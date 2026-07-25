"""Safe crop generator interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.reframe.models.camera import CameraPath
from app.reframe.models.crop import CropPlan
from app.reframe.models.importance import ImportanceScoringResult
from app.reframe.models.speakers import SpeakerEstimationResult
from app.reframe.models.tracking import TrackingResult


class CropGenerator(ABC):
    """Generate safe crop rectangles from a camera path."""

    @property
    @abstractmethod
    def generator_name(self) -> str:
        """Return the generator backend identifier."""

    @abstractmethod
    def generate(
        self,
        camera_path: CameraPath,
        tracking: TrackingResult,
        *,
        speaker_result: SpeakerEstimationResult | None = None,
        importance: ImportanceScoringResult | None = None,
    ) -> CropPlan:
        """Return per-frame crop rectangles with render segments."""
