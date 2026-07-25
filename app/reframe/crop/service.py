"""Safe crop generation orchestration service."""

from __future__ import annotations

from loguru import logger

from app.core.config import Settings, get_settings
from app.reframe.crop.base import CropGenerator
from app.reframe.crop.factory import get_crop_generator
from app.reframe.models.camera import CameraPath
from app.reframe.models.crop import CropPlan
from app.reframe.models.importance import ImportanceScoringResult
from app.reframe.models.speakers import SpeakerEstimationResult
from app.reframe.models.tracking import TrackingResult


class SafeCropService:
    """Generate safe crop plans from smoothed camera paths."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        generator: CropGenerator | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._generator = generator

    @property
    def generator(self) -> CropGenerator:
        if self._generator is None:
            self._generator = get_crop_generator(self.settings)
        return self._generator

    def generate(
        self,
        camera_path: CameraPath,
        tracking: TrackingResult,
        *,
        speaker_result: SpeakerEstimationResult | None = None,
        importance: ImportanceScoringResult | None = None,
    ) -> CropPlan:
        """Generate a crop plan from a camera path and tracking data."""
        logger.info(
            "Generating safe crop plan across {} frames with {}",
            len(camera_path.frames),
            self.generator.generator_name,
        )
        return self.generator.generate(
            camera_path,
            tracking,
            speaker_result=speaker_result,
            importance=importance,
        )


def generate_crop_plan(
    camera_path: CameraPath,
    tracking: TrackingResult,
    *,
    settings: Settings | None = None,
) -> CropPlan:
    """Convenience function to generate a safe crop plan."""
    return SafeCropService(settings=settings).generate(camera_path, tracking)
