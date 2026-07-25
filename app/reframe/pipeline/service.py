"""End-to-end reframe render pipeline."""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from app.core.config import Settings, get_settings
from app.models.transcript import TranscriptSegment
from app.reframe.camera.service import VirtualCameraService
from app.reframe.composition.service import CompositionService
from app.reframe.crop.service import SafeCropService
from app.reframe.importance.service import ImportanceScoringService
from app.reframe.models.camera import CameraPath
from app.reframe.models.composition import CompositionResult
from app.reframe.models.crop import CropPlan
from app.reframe.models.importance import ImportanceScoringResult
from app.reframe.models.render import ReframeRenderResult
from app.reframe.models.scenes import SceneDetectionResult
from app.reframe.models.speakers import SpeakerEstimationResult
from app.reframe.models.tracking import TrackingResult
from app.reframe.render.service import ReframeRenderService
from app.reframe.scenes.service import SceneDetectionService
from app.reframe.smoothing.service import TemporalSmoothingService
from app.reframe.speakers.service import ActiveSpeakerEstimationService
from app.reframe.tracking.service import FaceTrackingService


class ReframePipelineResult:
    """Artifacts produced by the full reframe pipeline."""

    def __init__(
        self,
        *,
        tracking: TrackingResult,
        importance: ImportanceScoringResult,
        composition: CompositionResult,
        camera_path: CameraPath,
        smoothed_path: CameraPath,
        crop_plan: CropPlan,
        render_result: ReframeRenderResult | None = None,
    ) -> None:
        self.tracking = tracking
        self.importance = importance
        self.composition = composition
        self.camera_path = camera_path
        self.smoothed_path = smoothed_path
        self.crop_plan = crop_plan
        self.render_result = render_result


class ReframePipelineService:
    """Run modules 1-10 from tracking through final render."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.tracking_service = FaceTrackingService(self.settings)
        self.importance_service = ImportanceScoringService(self.settings)
        self.composition_service = CompositionService(self.settings)
        self.camera_service = VirtualCameraService(self.settings)
        self.smoothing_service = TemporalSmoothingService(self.settings)
        self.crop_service = SafeCropService(self.settings)
        self.render_service = ReframeRenderService(self.settings)
        self.scene_service = SceneDetectionService(self.settings)
        self.speaker_service = ActiveSpeakerEstimationService(self.settings)

    def process_tracking(
        self,
        tracking: TrackingResult,
        importance: ImportanceScoringResult,
        *,
        scene_result: SceneDetectionResult | None = None,
        transcript_segments: list[TranscriptSegment] | None = None,
        video_path: str | Path | None = None,
        speaker_result: SpeakerEstimationResult | None = None,
    ) -> ReframePipelineResult:
        """Run modules 6-9 on existing tracking and importance results."""
        composition = self.composition_service.plan(
            tracking,
            importance,
            scene_result=scene_result,
            transcript_segments=transcript_segments,
            video_path=video_path,
            speaker_result=speaker_result,
        )
        camera_path = self.camera_service.plan(composition, scene_result=scene_result)
        smoothed_path = self.smoothing_service.smooth(camera_path, scene_result=scene_result)
        crop_plan = self.crop_service.generate(
            smoothed_path,
            tracking,
            speaker_result=speaker_result,
            importance=importance,
        )
        return ReframePipelineResult(
            tracking=tracking,
            importance=importance,
            composition=composition,
            camera_path=camera_path,
            smoothed_path=smoothed_path,
            crop_plan=crop_plan,
        )

    def process_video(
        self,
        video_path: str | Path,
        *,
        transcript_segments: list[TranscriptSegment] | None = None,
        fps: float | None = None,
        frames_dir: str | Path | None = None,
    ) -> ReframePipelineResult:
        """Run the analysis pipeline on a source video."""
        source = Path(video_path).resolve()
        logger.info("Running reframe analysis pipeline on {}", source.name)

        tracking = self.tracking_service.track_video(
            source,
            fps=fps,
            frames_dir=frames_dir,
        )
        speaker_result: SpeakerEstimationResult | None = None
        if transcript_segments:
            speaker_result = self.speaker_service.estimate(
                tracking,
                transcript_segments=transcript_segments,
                video_path=source,
            )
        importance = self.importance_service.score(
            tracking,
            speaker_result=speaker_result,
            transcript_segments=transcript_segments,
            video_path=source,
        )
        scene_result = self.scene_service.detect(source)
        return self.process_tracking(
            tracking,
            importance,
            scene_result=scene_result,
            transcript_segments=transcript_segments,
            video_path=source,
            speaker_result=speaker_result,
        )

    def render_video(
        self,
        video_path: str | Path,
        output_path: str | Path,
        *,
        transcript_segments: list[TranscriptSegment] | None = None,
        fps: float | None = None,
        frames_dir: str | Path | None = None,
        blurred_background: bool | None = None,
        duration_seconds: float | None = None,
    ) -> ReframePipelineResult:
        """Run the full pipeline and render the final vertical video."""
        pipeline = self.process_video(
            video_path,
            transcript_segments=transcript_segments,
            fps=fps,
            frames_dir=frames_dir,
        )
        render_result = self.render_service.render(
            video_path,
            pipeline.crop_plan,
            output_path,
            duration_seconds=duration_seconds,
            blurred_background=blurred_background,
        )
        pipeline.render_result = render_result
        return pipeline

    def close(self) -> None:
        """Release all dependent services."""
        self.tracking_service.close()
        self.importance_service.close()
        self.composition_service.close()
        self.camera_service.close()
        self.speaker_service.close()
