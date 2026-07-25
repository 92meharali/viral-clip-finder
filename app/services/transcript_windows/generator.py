"""Overlapping transcript window generation for LLM analysis."""

from __future__ import annotations

from loguru import logger

from app.core.config import Settings, get_settings
from app.core.exceptions import LLMAnalysisError
from app.models.transcript import TranscriptSegment
from app.models.transcript_window import TranscriptWindow, TranscriptWindowResult


def estimate_transcript_duration(
    segments: list[TranscriptSegment],
    *,
    total_duration_seconds: float | None = None,
    tail_seconds: float = 5.0,
) -> float:
    """Estimate transcript coverage in seconds."""
    if total_duration_seconds is not None and total_duration_seconds > 0:
        return total_duration_seconds
    if not segments:
        return 0.0
    return segments[-1].seconds + tail_seconds


def segment_end_seconds(
    segments: list[TranscriptSegment],
    index: int,
    *,
    total_duration_seconds: float | None = None,
    tail_seconds: float = 5.0,
) -> float:
    """Estimate when a transcript segment ends."""
    if index + 1 < len(segments):
        return segments[index + 1].seconds
    if total_duration_seconds is not None and total_duration_seconds > segments[index].seconds:
        return total_duration_seconds
    return segments[index].seconds + tail_seconds


def segments_in_window(
    segments: list[TranscriptSegment],
    *,
    window_start: float,
    window_end: float,
    total_duration_seconds: float | None = None,
) -> list[TranscriptSegment]:
    """Return segments that overlap a time window without splitting segments."""
    selected: list[TranscriptSegment] = []
    for index, segment in enumerate(segments):
        segment_end = segment_end_seconds(
            segments,
            index,
            total_duration_seconds=total_duration_seconds,
        )
        if segment_end <= window_start:
            continue
        if segment.seconds >= window_end:
            break
        selected.append(segment)
    return selected


def generate_transcript_windows(
    segments: list[TranscriptSegment],
    *,
    settings: Settings | None = None,
    total_duration_seconds: float | None = None,
) -> TranscriptWindowResult:
    """Split a transcript into overlapping analysis windows.

    Segment boundaries are preserved — segments are never truncated mid-line.
    When the transcript fits within a single window, one window is returned.
    """
    resolved = settings or get_settings()
    if not segments:
        raise LLMAnalysisError("Cannot generate transcript windows from an empty transcript")

    window_size = resolved.llm_window_size_seconds
    overlap = resolved.llm_window_overlap_seconds
    if overlap >= window_size:
        raise LLMAnalysisError(
            "LLM window overlap must be smaller than the window size "
            f"({overlap} >= {window_size})"
        )

    duration = estimate_transcript_duration(
        segments,
        total_duration_seconds=total_duration_seconds,
    )
    if not resolved.llm_window_enabled or duration <= window_size:
        return TranscriptWindowResult(
            windows=[
                TranscriptWindow(
                    index=0,
                    start_seconds=segments[0].seconds,
                    end_seconds=duration,
                    segments=list(segments),
                )
            ],
            total_duration_seconds=duration,
            window_size_seconds=window_size,
            overlap_seconds=overlap,
        )

    stride = window_size - overlap
    window_starts: list[float] = []
    cursor = segments[0].seconds
    while cursor < duration:
        window_starts.append(cursor)
        window_end = min(cursor + window_size, duration)
        if window_end >= duration:
            break
        cursor += stride

    final_start = max(segments[0].seconds, duration - window_size)
    if not window_starts or window_starts[-1] < final_start - 0.5:
        window_starts.append(final_start)

    windows: list[TranscriptWindow] = []
    for index, window_start in enumerate(window_starts):
        window_end = min(window_start + window_size, duration)
        window_segments = segments_in_window(
            segments,
            window_start=window_start,
            window_end=window_end,
            total_duration_seconds=duration,
        )
        if not window_segments:
            continue
        windows.append(
            TranscriptWindow(
                index=index,
                start_seconds=window_start,
                end_seconds=window_end,
                segments=window_segments,
            )
        )

    if not windows:
        raise LLMAnalysisError("Transcript window generation produced no segments")

    logger.info(
        "Generated {} LLM transcript windows (size={}s overlap={}s duration={}s)",
        len(windows),
        window_size,
        overlap,
        duration,
    )
    return TranscriptWindowResult(
        windows=windows,
        total_duration_seconds=duration,
        window_size_seconds=window_size,
        overlap_seconds=overlap,
    )
