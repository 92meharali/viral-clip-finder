"""SRT subtitle file formatting utilities."""

from __future__ import annotations

from pathlib import Path

from app.models.subtitle import SubtitleCue

MIN_CUE_DURATION_SECONDS = 0.5
DEFAULT_CUE_DURATION_SECONDS = 2.5


def format_srt_timestamp(seconds: float) -> str:
    """Format seconds as an SRT timestamp (HH:MM:SS,mmm).

    Args:
        seconds: Elapsed time in seconds (non-negative).

    Returns:
        SRT-formatted timestamp such as ``00:01:23,500``.

    Example:
        >>> format_srt_timestamp(83.5)
        '00:01:23,500'
    """
    if seconds < 0:
        raise ValueError(f"Seconds must be non-negative, got {seconds}")

    total_millis = int(round(seconds * 1000))
    hours, remainder = divmod(total_millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def cues_to_srt(cues: list[SubtitleCue]) -> str:
    """Render subtitle cues as SRT file content.

    Args:
        cues: Ordered list of subtitle cues.

    Returns:
        Complete SRT file content string.
    """
    blocks: list[str] = []
    for cue in cues:
        start = format_srt_timestamp(cue.start_seconds)
        end = format_srt_timestamp(cue.end_seconds)
        blocks.append(f"{cue.index}\n{start} --> {end}\n{cue.text}")
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def write_srt_file(cues: list[SubtitleCue], path: str | Path) -> Path:
    """Write subtitle cues to an SRT file.

    Args:
        cues: Subtitle cues to write.
        path: Output file path.

    Returns:
        Resolved path to the written file.
    """
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(cues_to_srt(cues), encoding="utf-8")
    return output.resolve()
