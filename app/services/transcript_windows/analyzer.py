"""Windowed transcript analysis orchestration."""

from __future__ import annotations

from collections.abc import Callable

from loguru import logger

from app.core.config import Settings, get_settings
from app.core.exceptions import LLMAnalysisError
from app.models.clip import ViralClip
from app.models.transcript import TranscriptSegment
from app.providers.base import ClipAnalyzer
from app.services.transcript_windows.generator import generate_transcript_windows


def merge_window_clips(window_results: list[list[ViralClip]]) -> list[ViralClip]:
    """Merge clip candidates from multiple windows, removing exact duplicates."""
    merged: list[ViralClip] = []
    seen: set[tuple[float, float]] = set()

    for clips in window_results:
        for clip in clips:
            key = (clip.start_seconds, clip.end_seconds)
            if key in seen:
                continue
            seen.add(key)
            merged.append(clip)

    return merged


def analyze_transcript_with_windows(
    analyzer: ClipAnalyzer,
    segments: list[TranscriptSegment],
    *,
    settings: Settings | None = None,
    total_duration_seconds: float | None = None,
    on_window_analyzed: Callable[[int, int], None] | None = None,
) -> tuple[list[ViralClip], int]:
    """Analyze a transcript in overlapping windows when needed.

    Args:
        analyzer: Provider implementing :class:`ClipAnalyzer`.
        segments: Full transcript segments with absolute timestamps.
        settings: Optional settings override.
        total_duration_seconds: Known video duration for better windowing.
        on_window_analyzed: Optional callback ``(index, total)`` after each window.

    Returns:
        Tuple of merged viral clips and the number of windows analyzed.
    """
    resolved = settings or get_settings()
    window_result = generate_transcript_windows(
        segments,
        settings=resolved,
        total_duration_seconds=total_duration_seconds,
    )

    if window_result.window_count == 1:
        clips = analyzer.analyze_transcript(segments)
        return clips, 1

    logger.info(
        "Running windowed analysis across {} transcript windows with provider={}",
        window_result.window_count,
        analyzer.provider_name,
    )

    per_window: list[list[ViralClip]] = []
    for offset, window in enumerate(window_result.windows, start=1):
        logger.info(
            "Analyzing transcript window {}/{} ({:.1f}s → {:.1f}s, {} segments)",
            offset,
            window_result.window_count,
            window.start_seconds,
            window.end_seconds,
            window.segment_count,
        )
        clips = analyzer.analyze_transcript(window.segments)
        per_window.append(clips)
        if on_window_analyzed is not None:
            on_window_analyzed(offset, window_result.window_count)

    merged = merge_window_clips(per_window)
    if not merged:
        raise LLMAnalysisError("Windowed analysis returned no clips")

    logger.info(
        "Windowed analysis produced {} unique clips from {} windows",
        len(merged),
        window_result.window_count,
    )
    return merged, window_result.window_count
