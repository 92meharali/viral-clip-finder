"""Generate SRT subtitles from transcript segments for clip windows."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from loguru import logger

from app.core.config import Settings, get_settings
from app.core.exceptions import SubtitleError
from app.models.export import ExtractedClip
from app.models.subtitle import SubtitleCue, SubtitleFile
from app.models.transcript import TranscriptSegment
from app.utils.srt_utils import (
    DEFAULT_CUE_DURATION_SECONDS,
    MIN_CUE_DURATION_SECONDS,
    write_srt_file,
)


class TimedClip(Protocol):
    """Protocol for clip objects with timing metadata."""

    index: int
    start: str
    end: str
    start_seconds: float
    end_seconds: float


def _format_cue_text(segment: TranscriptSegment, *, include_speaker: bool) -> str:
    """Format segment dialogue for display, optionally with speaker label."""
    if include_speaker and segment.speaker:
        return f"{segment.speaker}: {segment.text}"
    return segment.text


def build_cues_for_clip(
    segments: list[TranscriptSegment],
    *,
    clip_start_seconds: float,
    clip_end_seconds: float,
    include_speaker: bool = True,
) -> list[SubtitleCue]:
    """Build clip-relative subtitle cues from transcript segments.

    Segments are filtered to the clip window and timed relative to clip start.
    Each cue ends when the next segment begins, or at the clip end.

    Args:
        segments: Full transcript segments in chronological order.
        clip_start_seconds: Clip start time in the source video.
        clip_end_seconds: Clip end time in the source video.
        include_speaker: Prefix cues with speaker labels when available.

    Returns:
        Ordered list of :class:`SubtitleCue` objects.
    """
    clip_duration = clip_end_seconds - clip_start_seconds
    matching = [
        segment for segment in segments if clip_start_seconds <= segment.seconds < clip_end_seconds
    ]

    cues: list[SubtitleCue] = []
    for index, segment in enumerate(matching, start=1):
        rel_start = max(0.0, segment.seconds - clip_start_seconds)

        if index < len(matching):
            rel_end = matching[index].seconds - clip_start_seconds
        else:
            rel_end = clip_duration

        if rel_end - rel_start < MIN_CUE_DURATION_SECONDS:
            rel_end = min(rel_start + DEFAULT_CUE_DURATION_SECONDS, clip_duration)

        if rel_end <= rel_start:
            rel_end = min(rel_start + MIN_CUE_DURATION_SECONDS, clip_duration)

        cues.append(
            SubtitleCue(
                index=index,
                start_seconds=round(rel_start, 3),
                end_seconds=round(rel_end, 3),
                text=_format_cue_text(segment, include_speaker=include_speaker),
            )
        )

    return cues


def _build_srt_path(output_dir: Path, index: int) -> Path:
    """Generate SRT path such as ``clip1.srt``."""
    return output_dir / f"clip{index}.srt"


class SubtitleGenerator:
    """Generate SRT subtitle files for video clips from transcript data."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the subtitle generator."""
        self.settings = settings or get_settings()

    def generate(
        self,
        segments: list[TranscriptSegment],
        clips: Sequence[TimedClip | ExtractedClip],
        output_dir: str | Path | None = None,
        *,
        include_speaker: bool = True,
    ) -> list[SubtitleFile]:
        """Generate SRT files for each clip.

        Args:
            segments: Parsed transcript segments from the full video.
            clips: Clips with start/end timing (e.g. ``ExtractedClip`` or ``ViralClip``).
            output_dir: Directory for ``.srt`` files. Defaults to ``settings.output_dir``.
            include_speaker: Include speaker names in subtitle text.

        Returns:
            Metadata for each generated subtitle file.

        Raises:
            SubtitleError: If inputs are invalid.
        """
        if not segments:
            raise SubtitleError("Cannot generate subtitles from empty transcript")
        if not clips:
            raise SubtitleError("Cannot generate subtitles for empty clip list")

        out_dir = Path(output_dir or self.settings.output_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Generating subtitles for {} clips → {}", len(clips), out_dir)

        results: list[SubtitleFile] = []
        output_index = 0

        for clip in clips:
            cues = build_cues_for_clip(
                segments,
                clip_start_seconds=clip.start_seconds,
                clip_end_seconds=clip.end_seconds,
                include_speaker=include_speaker,
            )

            output_index += 1
            srt_path = write_srt_file(cues, _build_srt_path(out_dir, output_index))

            results.append(
                SubtitleFile(
                    index=output_index,
                    clip_start=clip.start,
                    clip_end=clip.end,
                    srt_path=str(srt_path),
                    cue_count=len(cues),
                )
            )
            logger.debug("Wrote {} cues to {}", len(cues), srt_path.name)

        logger.info("Generated {} subtitle files", len(results))
        return results


def generate_subtitles(
    segments: list[TranscriptSegment],
    clips: Sequence[TimedClip | ExtractedClip],
    output_dir: str | Path | None = None,
    *,
    settings: Settings | None = None,
    include_speaker: bool = True,
) -> list[SubtitleFile]:
    """Convenience function to generate SRT subtitles for clips.

    Args:
        segments: Full transcript segments.
        clips: Timed clip objects.
        output_dir: Output directory for SRT files.
        settings: Optional settings override.
        include_speaker: Include speaker labels in cues.

    Returns:
        List of subtitle file metadata.
    """
    return SubtitleGenerator(settings=settings).generate(
        segments,
        clips,
        output_dir,
        include_speaker=include_speaker,
    )
