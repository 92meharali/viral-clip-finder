"""Virtual camera planner interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.reframe.models.camera import CameraPath
from app.reframe.models.composition import CompositionResult
from app.reframe.models.scenes import SceneDetectionResult


class VirtualCameraPlanner(ABC):
    """Plan a smooth virtual camera path from composition targets."""

    @property
    @abstractmethod
    def planner_name(self) -> str:
        """Return the planner backend identifier."""

    @abstractmethod
    def plan(
        self,
        composition: CompositionResult,
        *,
        scene_result: SceneDetectionResult | None = None,
    ) -> CameraPath:
        """Return a continuous camera path across the composition."""
