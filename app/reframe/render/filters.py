"""FFmpeg filter builders for reframed renders."""

from __future__ import annotations

from app.reframe.models.crop import CropSegment


def _even_dimension(value: int) -> int:
    return max(2, value - value % 2)


def even_crop_dimensions(width: int, height: int) -> tuple[int, int]:
    """Return encoder-friendly even crop dimensions."""
    return (_even_dimension(width), _even_dimension(height))


def build_segment_crop_filter(
    segment: CropSegment,
    *,
    target_width: int,
    target_height: int,
) -> str:
    """Build a crop+scale filter for one render segment."""
    crop = segment.crop
    x = int(round(crop.x))
    y = int(round(crop.y))
    width = _even_dimension(int(round(crop.width)))
    height = _even_dimension(int(round(crop.height)))
    return (
        f"crop={width}:{height}:{x}:{y},"
        f"scale={target_width}:{target_height}:flags=lanczos"
    )


def build_segment_blur_filter(
    segment: CropSegment,
    *,
    target_width: int,
    target_height: int,
    blur_strength: int,
) -> str:
    """Build a blurred-background filter_complex for one segment."""
    crop = segment.crop
    x = int(round(crop.x))
    y = int(round(crop.y))
    width = int(round(crop.width))
    height = int(round(crop.height))
    return (
        f"[0:v]split=2[fg][bg];"
        f"[bg]scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
        f"crop={target_width}:{target_height},boxblur={blur_strength}:5[blurred];"
        f"[fg]crop={width}:{height}:{x}:{y},scale={target_width}:-2:force_original_aspect_ratio=decrease[scaled];"
        f"[blurred][scaled]overlay=(W-w)/2:(H-h)/2[vout]"
    )
