"""Temporal smoothing orchestration service."""

from __future__ import annotations

from loguru import logger

from app.core.config import Settings, get_settings
from app.reframe.models.camera import CameraPath
from app.reframe.models.scenes import SceneDetectionResult
from app.reframe.smoothing.base import TemporalSmoother
from app.reframe.smoothing.factory import get_temporal_smoother


class TemporalSmoothingService:
    """Smooth virtual camera paths for stable reframing."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        smoother: TemporalSmoother | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._smoother = smoother

    @property
    def smoother(self) -> TemporalSmoother:
        if self._smoother is None:
            self._smoother = get_temporal_smoother(self.settings)
        return self._smoother

    def smooth(
        self,
        camera_path: CameraPath,
        *,
        scene_result: SceneDetectionResult | None = None,
    ) -> CameraPath:
        """Smooth a camera path while respecting scene boundaries."""
        logger.info(
            "Smoothing camera path across {} frames with {}",
            len(camera_path.frames),
            self.smoother.smoother_name,
        )
        return self.smoother.smooth(camera_path, scene_result=scene_result)


def smooth_camera_path(
    camera_path: CameraPath,
    *,
    settings: Settings | None = None,
    scene_result: SceneDetectionResult | None = None,
) -> CameraPath:
    """Convenience function to smooth a camera path."""
    return TemporalSmoothingService(settings=settings).smooth(
        camera_path,
        scene_result=scene_result,
    )
