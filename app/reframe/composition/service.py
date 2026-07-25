"""Shot composition orchestration service."""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from app.core.config import Settings, get_settings
from app.models.transcript import TranscriptSegment
from app.reframe.composition.base import CompositionPlanner
from app.reframe.composition.factory import get_composition_planner
from app.reframe.importance.service import ImportanceScoringService
from app.reframe.models.composition import CompositionResult
from app.reframe.models.importance import ImportanceScoringResult
from app.reframe.models.scenes import SceneDetectionResult
from app.reframe.models.speakers import SpeakerEstimationResult
from app.reframe.models.tracking import TrackingResult
from app.reframe.scenes.service import SceneDetectionService
from app.reframe.speakers.service import ActiveSpeakerEstimationService
from app.reframe.tracking.service import FaceTrackingService


class CompositionService:
    """Plan shot composition from tracking and importance data."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        planner: CompositionPlanner | None = None,
        importance_service: ImportanceScoringService | None = None,
        speaker_service: ActiveSpeakerEstimationService | None = None,
        tracking_service: FaceTrackingService | None = None,
        scene_service: SceneDetectionService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._planner = planner
        self._importance_service = importance_service
        self._speaker_service = speaker_service
        self._tracking_service = tracking_service
        self._scene_service = scene_service

    @property
    def planner(self) -> CompositionPlanner:
        if self._planner is None:
            self._planner = get_composition_planner(self.settings)
        return self._planner

    @property
    def importance_service(self) -> ImportanceScoringService:
        if self._importance_service is None:
            self._importance_service = ImportanceScoringService(self.settings)
        return self._importance_service

    @property
    def speaker_service(self) -> ActiveSpeakerEstimationService:
        if self._speaker_service is None:
            self._speaker_service = ActiveSpeakerEstimationService(self.settings)
        return self._speaker_service

    @property
    def tracking_service(self) -> FaceTrackingService:
        if self._tracking_service is None:
            self._tracking_service = FaceTrackingService(self.settings)
        return self._tracking_service

    @property
    def scene_service(self) -> SceneDetectionService:
        if self._scene_service is None:
            self._scene_service = SceneDetectionService(self.settings)
        return self._scene_service

    def plan(
        self,
        tracking: TrackingResult,
        importance: ImportanceScoringResult,
        *,
        speaker_result: SpeakerEstimationResult | None = None,
        scene_result: SceneDetectionResult | None = None,
        transcript_segments: list[TranscriptSegment] | None = None,
        video_path: str | Path | None = None,
    ) -> CompositionResult:
        """Plan composition for existing tracking and importance results."""
        resolved_speaker = speaker_result
        if resolved_speaker is None and transcript_segments is not None:
            resolved_speaker = self.speaker_service.estimate(
                tracking,
                transcript_segments=transcript_segments,
                video_path=video_path,
            )

        logger.info(
            "Planning shot composition across {} frames with {}",
            len(tracking.frames),
            self.planner.planner_name,
        )
        return self.planner.plan(
            tracking,
            importance,
            speaker_result=resolved_speaker,
            scene_result=scene_result,
        )

    def plan_video(
        self,
        video_path: str | Path,
        *,
        transcript_segments: list[TranscriptSegment] | None = None,
        fps: float | None = None,
        frames_dir: str | Path | None = None,
    ) -> CompositionResult:
        """Track faces, score importance, and plan composition for a video."""
        source = Path(video_path).resolve()
        logger.info("Starting shot composition on {}", source.name)

        tracking = self.tracking_service.track_video(
            source,
            fps=fps,
            frames_dir=frames_dir,
        )
        importance = self.importance_service.score(
            tracking,
            transcript_segments=transcript_segments,
            video_path=source,
        )
        scene_result = self.scene_service.detect(source)
        return self.plan(
            tracking,
            importance,
            transcript_segments=transcript_segments,
            video_path=source,
            scene_result=scene_result,
        )

    def close(self) -> None:
        """Release dependent pipeline services."""
        self.importance_service.close()
        self.speaker_service.close()
        self.tracking_service.close()


def plan_composition(
    tracking: TrackingResult,
    importance: ImportanceScoringResult,
    *,
    settings: Settings | None = None,
    speaker_result: SpeakerEstimationResult | None = None,
    scene_result: SceneDetectionResult | None = None,
    transcript_segments: list[TranscriptSegment] | None = None,
    video_path: str | Path | None = None,
) -> CompositionResult:
    """Convenience function to plan shot composition."""
    service = CompositionService(settings=settings)
    try:
        return service.plan(
            tracking,
            importance,
            speaker_result=speaker_result,
            scene_result=scene_result,
            transcript_segments=transcript_segments,
            video_path=video_path,
        )
    finally:
        service.close()
