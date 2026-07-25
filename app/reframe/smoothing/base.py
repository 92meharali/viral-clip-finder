"""Temporal smoothing interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.reframe.models.camera import CameraPath
from app.reframe.models.scenes import SceneDetectionResult


class TemporalSmoother(ABC):
    """Smooth a virtual camera path while respecting scene boundaries."""

    @property
    @abstractmethod
    def smoother_name(self) -> str:
        """Return the smoother backend identifier."""

    @abstractmethod
    def smooth(
        self,
        camera_path: CameraPath,
        *,
        scene_result: SceneDetectionResult | None = None,
    ) -> CameraPath:
        """Return a smoothed camera path."""
