"""Vertical video cropping for short-form platforms."""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum
from pathlib import Path

from loguru import logger

from app.core.config import Settings, get_settings
from app.core.exceptions import VerticalCropError, VideoCutError
from app.models.export import ExtractedClip, VerticalClip
from app.video.ffmpeg import probe_dimensions, run_ffmpeg, validate_source_video
from app.video.filters import (
    CROP_MODE_BLUR,
    CROP_MODE_CENTER,
    build_blur_background_filter,
    build_center_crop_filter,
)


class CropMode(str, Enum):
    """Vertical crop strategy."""

    CENTER_CROP = CROP_MODE_CENTER
    BLUR_BACKGROUND = CROP_MODE_BLUR


def _resolve_input(clip: str | Path | ExtractedClip) -> tuple[Path, int]:
    """Resolve input path and clip index from various input types."""
    if isinstance(clip, ExtractedClip):
        return Path(clip.output_path), clip.index
    path = Path(clip)
    stem = path.stem
    if stem.startswith("clip") and stem[4:].isdigit():
        return path, int(stem[4:])
    return path, 1


def _build_vertical_output_path(output_dir: Path, index: int) -> Path:
    """Generate output path such as ``clip1_vertical.mp4``."""
    return output_dir / f"clip{index}_vertical.mp4"


def _simple_crop_args(source: Path, output: Path, video_filter: str) -> list[str]:
    """Build ffmpeg args for a simple ``-vf`` center crop."""
    return [
        "-y",
        "-i",
        str(source),
        "-vf",
        video_filter,
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-c:a",
        "copy",
        str(output),
    ]


def _blur_crop_args(source: Path, output: Path, filter_complex: str) -> list[str]:
    """Build ffmpeg args for blurred-background filter_complex."""
    return [
        "-y",
        "-i",
        str(source),
        "-filter_complex",
        filter_complex,
        "-map",
        "[vout]",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-c:a",
        "copy",
        str(output),
    ]


def _crop_single_video(
    source: Path,
    output: Path,
    *,
    mode: CropMode,
    settings: Settings,
    width: int,
    height: int,
    blur_strength: int,
) -> str:
    """Crop a single video file to vertical format.

    Returns:
        The crop mode string used.
    """
    source_width, source_height = probe_dimensions(source, settings)

    if mode == CropMode.BLUR_BACKGROUND:
        filter_complex = build_blur_background_filter(width, height, blur_strength)
        run_ffmpeg(_blur_crop_args(source, output, filter_complex), settings=settings)
        return CROP_MODE_BLUR

    video_filter = build_center_crop_filter(source_width, source_height, width, height)
    run_ffmpeg(_simple_crop_args(source, output, video_filter), settings=settings)
    return CROP_MODE_CENTER


class VerticalCropper:
    """Crop horizontal clips to 9:16 vertical format for TikTok, Reels, and Shorts."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the vertical cropper.

        Args:
            settings: Optional settings override.
        """
        self.settings = settings or get_settings()

    def crop(
        self,
        clips: Sequence[str | Path | ExtractedClip],
        output_dir: str | Path | None = None,
        *,
        blurred_background: bool = False,
        width: int | None = None,
        height: int | None = None,
        blur_strength: int | None = None,
        mode: CropMode | None = None,
    ) -> list[VerticalClip]:
        """Crop clips to vertical 1080x1920 format.

        Args:
            clips: Input video paths or :class:`ExtractedClip` objects from Phase 4.
            output_dir: Directory for vertical outputs. Defaults to ``settings.output_dir``.
            blurred_background: Use blurred background instead of center crop.
            width: Output width (default from settings, 1080).
            height: Output height (default from settings, 1920).
            blur_strength: Blur radius for background mode.
            mode: Explicit crop mode override.

        Returns:
            Metadata for each vertically cropped clip.

        Raises:
            VerticalCropError: If inputs are empty or cropping fails.
        """
        if not clips:
            raise VerticalCropError("Cannot crop an empty clip list")

        target_width = width or self.settings.vertical_width
        target_height = height or self.settings.vertical_height
        blur = blur_strength or self.settings.vertical_blur_strength
        crop_mode = mode or (
            CropMode.BLUR_BACKGROUND if blurred_background else CropMode.CENTER_CROP
        )

        out_dir = Path(output_dir or self.settings.output_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "Cropping {} clips to {}x{} (mode={}) → {}",
            len(clips),
            target_width,
            target_height,
            crop_mode.value,
            out_dir,
        )

        results: list[VerticalClip] = []
        output_index = 0

        for clip in clips:
            source, _ = _resolve_input(clip)
            try:
                validate_source_video(source)
            except VideoCutError as exc:
                raise VerticalCropError(str(exc), source_path=str(source)) from exc

            output_index += 1
            output_path = _build_vertical_output_path(out_dir, output_index)

            used_mode = _crop_single_video(
                source,
                output_path,
                mode=crop_mode,
                settings=self.settings,
                width=target_width,
                height=target_height,
                blur_strength=blur,
            )

            results.append(
                VerticalClip(
                    index=output_index,
                    source_path=str(source),
                    output_path=str(output_path),
                    width=target_width,
                    height=target_height,
                    blurred_background=used_mode == CROP_MODE_BLUR,
                    crop_mode=used_mode,
                )
            )

        logger.info("Cropped {} clips to vertical format", len(results))
        return results


def crop_to_vertical(
    clips: Sequence[str | Path | ExtractedClip],
    output_dir: str | Path | None = None,
    *,
    blurred_background: bool = False,
    settings: Settings | None = None,
    width: int | None = None,
    height: int | None = None,
    blur_strength: int | None = None,
    mode: CropMode | None = None,
) -> list[VerticalClip]:
    """Convenience function to crop clips to vertical short-form format.

    Args:
        clips: Input video paths or extracted clip metadata.
        output_dir: Output directory for vertical clips.
        blurred_background: Enable blurred background mode.
        settings: Optional settings override.
        width: Output width in pixels.
        height: Output height in pixels.
        blur_strength: Blur radius for background mode.
        mode: Explicit crop mode override.

    Returns:
        List of vertical clip metadata.
    """
    return VerticalCropper(settings=settings).crop(
        clips,
        output_dir,
        blurred_background=blurred_background,
        width=width,
        height=height,
        blur_strength=blur_strength,
        mode=mode,
    )
