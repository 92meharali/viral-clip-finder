"""FFmpeg video filter builders for vertical cropping."""

from __future__ import annotations

CROP_MODE_CENTER = "center_crop"
CROP_MODE_BLUR = "blur_background"


def build_center_crop_filter(
    source_width: int,
    source_height: int,
    target_width: int = 1080,
    target_height: int = 1920,
) -> str:
    """Build a center-crop filter chain for 9:16 vertical output.

    Landscape sources are center-cropped to 9:16 then scaled. Portrait sources
    are scaled up and center-cropped to the target dimensions.

    Args:
        source_width: Input video width in pixels.
        source_height: Input video height in pixels.
        target_width: Output width (default 1080).
        target_height: Output height (default 1920).

    Returns:
        FFmpeg ``-vf`` filter string.
    """
    target_aspect = target_width / target_height
    source_aspect = source_width / source_height

    if source_aspect > target_aspect:
        crop_width_expr = f"ih*{target_width}/{target_height}"
        return (
            f"crop={crop_width_expr}:ih:(iw-{crop_width_expr})/2:0,"
            f"scale={target_width}:{target_height}"
        )

    return (
        f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
        f"crop={target_width}:{target_height}"
    )


def build_blur_background_filter(
    target_width: int = 1080,
    target_height: int = 1920,
    blur_strength: int = 20,
) -> str:
    """Build a filter_complex chain with blurred background and centered foreground.

    The background is a scaled, cropped, and blurred version of the video.
    The foreground preserves aspect ratio and is centered on top.

    Args:
        target_width: Output width (default 1080).
        target_height: Output height (default 1920).
        blur_strength: Box blur radius (default 20).

    Returns:
        FFmpeg ``filter_complex`` string with ``[vout]`` output label.
    """
    return (
        f"[0:v]split=2[fg][bg];"
        f"[bg]scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
        f"crop={target_width}:{target_height},boxblur={blur_strength}:5[blurred];"
        f"[fg]scale={target_width}:-2:force_original_aspect_ratio=decrease[scaled];"
        f"[blurred][scaled]overlay=(W-w)/2:(H-h)/2[vout]"
    )
