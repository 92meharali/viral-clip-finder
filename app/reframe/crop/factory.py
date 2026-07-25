"""Safe crop generator factory."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.core.exceptions import UnknownCropGeneratorError
from app.reframe.crop.base import CropGenerator
from app.reframe.crop.generator import SafeCropGenerator

SUPPORTED_CROP_GENERATORS = frozenset({"safe"})


def get_crop_generator(settings: Settings | None = None) -> CropGenerator:
    """Return the configured crop generator backend."""
    resolved = settings or get_settings()
    generator_name = resolved.crop_generator.strip().lower()

    if generator_name not in SUPPORTED_CROP_GENERATORS:
        supported = ", ".join(sorted(SUPPORTED_CROP_GENERATORS))
        raise UnknownCropGeneratorError(
            f"Unsupported crop generator '{resolved.crop_generator}'. Supported: {supported}"
        )

    if generator_name == "safe":
        return SafeCropGenerator(resolved)

    raise UnknownCropGeneratorError(f"No implementation for crop generator '{generator_name}'")
