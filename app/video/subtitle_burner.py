"""Burn SRT subtitles into video files using FFmpeg."""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from app.core.config import Settings, get_settings
from app.core.exceptions import SubtitleError, VideoCutError
from app.models.subtitle import SubtitleFile, SubtitlePosition, SubtitleStyle
from app.video.ffmpeg import run_ffmpeg, validate_source_video

# ASS/SSA alignment values (numpad layout).
_ASS_ALIGNMENT = {
    SubtitlePosition.TOP: 8,
    SubtitlePosition.CENTER: 5,
    SubtitlePosition.BOTTOM: 2,
}

_NAMED_COLORS = {
    "white": "&H00FFFFFF",
    "yellow": "&H0000FFFF",
    "black": "&H00000000",
    "red": "&H000000FF",
    "green": "&H0000FF00",
    "blue": "&H00FF0000",
    "cyan": "&H00FFFF00",
    "magenta": "&H00FF00FF",
}


def color_to_ass(color: str) -> str:
    """Convert a color name or hex string to ASS ``PrimaryColour`` format.

    ASS uses ``&H00BBGGRR`` byte order.

    Args:
        color: Color name (e.g. ``white``) or hex ``#RRGGBB``.

    Returns:
        ASS color string.
    """
    normalized = color.strip().lower()
    if normalized in _NAMED_COLORS:
        return _NAMED_COLORS[normalized]

    hex_color = normalized.lstrip("#")
    if len(hex_color) == 6:
        red = int(hex_color[0:2], 16)
        green = int(hex_color[2:4], 16)
        blue = int(hex_color[4:6], 16)
        return f"&H00{blue:02X}{green:02X}{red:02X}"

    raise SubtitleError(f"Unsupported subtitle color: {color}")


def build_force_style(style: SubtitleStyle) -> str:
    """Build FFmpeg ``force_style`` string from a :class:`SubtitleStyle`."""
    alignment = _ASS_ALIGNMENT[style.position]
    ass_color = color_to_ass(style.color)
    return (
        f"FontName={style.font},"
        f"FontSize={style.size},"
        f"Outline={style.outline},"
        f"PrimaryColour={ass_color},"
        f"Alignment={alignment}"
    )


def escape_subtitles_path(path: Path) -> str:
    """Escape a file path for use in FFmpeg's subtitles filter."""
    return str(path.resolve()).replace("\\", "/").replace(":", "\\:")


def _build_burn_filter(srt_path: Path, style: SubtitleStyle) -> str:
    """Build FFmpeg video filter for burning subtitles."""
    escaped = escape_subtitles_path(srt_path)
    force_style = build_force_style(style)
    return f"subtitles={escaped}:force_style='{force_style}'"


def _build_burned_output_path(video_path: Path) -> Path:
    """Generate output path such as ``clip1_vertical_subtitled.mp4``."""
    return video_path.with_name(f"{video_path.stem}_subtitled{video_path.suffix}")


def default_style_from_settings(settings: Settings | None = None) -> SubtitleStyle:
    """Create a :class:`SubtitleStyle` from application settings."""
    resolved = settings or get_settings()
    return SubtitleStyle(
        font=resolved.subtitle_font,
        size=resolved.subtitle_size,
        outline=resolved.subtitle_outline,
        color=resolved.subtitle_color,
        position=SubtitlePosition(resolved.subtitle_position),
    )


class SubtitleBurner:
    """Burn SRT subtitles into video files."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the subtitle burner."""
        self.settings = settings or get_settings()

    def burn(
        self,
        video_path: str | Path,
        srt_path: str | Path,
        output_path: str | Path | None = None,
        *,
        style: SubtitleStyle | None = None,
    ) -> str:
        """Burn subtitles into a video file.

        Args:
            video_path: Input video file.
            srt_path: SRT subtitle file.
            output_path: Output video path. Defaults to ``{stem}_subtitled.mp4``.
            style: Subtitle styling. Defaults to settings-based style.

        Returns:
            Path to the output video.

        Raises:
            SubtitleError: If inputs are invalid or burning fails.
        """
        video = Path(video_path).resolve()
        srt = Path(srt_path).resolve()
        resolved_style = style or default_style_from_settings(self.settings)

        if not srt.exists():
            raise SubtitleError(f"Subtitle file not found: {srt}")

        try:
            validate_source_video(video)
        except VideoCutError as exc:
            raise SubtitleError(str(exc)) from exc

        output = Path(output_path).resolve() if output_path else _build_burned_output_path(video)
        output.parent.mkdir(parents=True, exist_ok=True)

        video_filter = _build_burn_filter(srt, resolved_style)
        logger.info("Burning subtitles into {} → {}", video.name, output.name)

        try:
            run_ffmpeg(
                [
                    "-y",
                    "-i",
                    str(video),
                    "-vf",
                    video_filter,
                    "-c:a",
                    "copy",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "23",
                    str(output),
                ],
                settings=self.settings,
            )
        except VideoCutError as exc:
            raise SubtitleError(f"Failed to burn subtitles: {exc}") from exc

        return str(output)

    def burn_for_subtitle_files(
        self,
        video_paths: dict[int, str | Path],
        subtitle_files: list[SubtitleFile],
        *,
        style: SubtitleStyle | None = None,
    ) -> list[SubtitleFile]:
        """Burn subtitles for multiple clips matched by index.

        Args:
            video_paths: Mapping of clip index to video file path.
            subtitle_files: Generated subtitle metadata from :class:`SubtitleGenerator`.
            style: Optional subtitle style override.

        Returns:
            Updated subtitle file metadata with ``burned_output_path`` set.
        """
        updated: list[SubtitleFile] = []

        for subtitle in subtitle_files:
            video = video_paths.get(subtitle.index)
            if video is None:
                logger.warning(
                    "No video found for subtitle index {}, skipping burn", subtitle.index
                )
                updated.append(subtitle)
                continue

            burned_path = self.burn(video, subtitle.srt_path, style=style)
            updated.append(subtitle.model_copy(update={"burned_output_path": burned_path}))

        return updated


def burn_subtitles(
    video_path: str | Path,
    srt_path: str | Path,
    output_path: str | Path | None = None,
    *,
    settings: Settings | None = None,
    style: SubtitleStyle | None = None,
) -> str:
    """Convenience function to burn subtitles into a video."""
    return SubtitleBurner(settings=settings).burn(
        video_path,
        srt_path,
        output_path,
        style=style,
    )
