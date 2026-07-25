"""Virtual camera planning orchestration service."""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from app.core.config import Settings, get_settings
from app.models.transcript import TranscriptSegment
from app.reframe.camera.base import VirtualCameraPlanner
from app.reframe.camera.factory import get_camera_planner
from app.reframe.composition.service import CompositionService
from app.reframe.models.camera import CameraPath
from app.reframe.models.composition import CompositionResult
from app.reframe.models.importance import ImportanceScoringResult
from app.reframe.models.scenes import SceneDetectionResult
from app.reframe.models.tracking import TrackingResult


class VirtualCameraService:
    """Plan a smooth virtual camera path from shot composition."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        planner: VirtualCameraPlanner | None = None,
        composition_service: CompositionService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._planner = planner
        self._composition_service = composition_service

    @property
    def planner(self) -> VirtualCameraPlanner:
        if self._planner is None:
            self._planner = get_camera_planner(self.settings)
        return self._planner

    @property
    def composition_service(self) -> CompositionService:
        if self._composition_service is None:
            self._composition_service = CompositionService(self.settings)
        return self._composition_service

    def plan(
        self,
        composition: CompositionResult,
        *,
        scene_result: SceneDetectionResult | None = None,
    ) -> CameraPath:
        """Plan a camera path from an existing composition result."""
        logger.info(
            "Planning virtual camera path across {} frames with {}",
            len(composition.frames),
            self.planner.planner_name,
        )
        return self.planner.plan(composition, scene_result=scene_result)

    def plan_from_pipeline(
        self,
        tracking: TrackingResult,
        importance: ImportanceScoringResult,
        *,
        scene_result: SceneDetectionResult | None = None,
        transcript_segments: list[TranscriptSegment] | None = None,
        video_path: str | Path | None = None,
    ) -> CameraPath:
        """Plan composition and camera path from upstream reframe results."""
        composition = self.composition_service.plan(
            tracking,
            importance,
            scene_result=scene_result,
            transcript_segments=transcript_segments,
            video_path=video_path,
        )
        return self.plan(composition, scene_result=scene_result)

    def plan_video(
        self,
        video_path: str | Path,
        *,
        transcript_segments: list[TranscriptSegment] | None = None,
        fps: float | None = None,
        frames_dir: str | Path | None = None,
    ) -> CameraPath:
        """Run the upstream pipeline and plan a camera path for a video."""
        composition = self.composition_service.plan_video(
            video_path,
            transcript_segments=transcript_segments,
            fps=fps,
            frames_dir=frames_dir,
        )
        source = Path(video_path).resolve()
        scene_result = self.composition_service.scene_service.detect(source)
        return self.plan(composition, scene_result=scene_result)

    def close(self) -> None:
        """Release dependent pipeline services."""
        self.composition_service.close()


def plan_camera_path(
    composition: CompositionResult,
    *,
    settings: Settings | None = None,
    scene_result: SceneDetectionResult | None = None,
) -> CameraPath:
    """Convenience function to plan a virtual camera path."""
    service = VirtualCameraService(settings=settings)
    try:
        return service.plan(composition, scene_result=scene_result)
    finally:
        service.close()
