"""Transcript segment helpers for clip-local processing."""

from __future__ import annotations

from app.models.transcript import TranscriptSegment


def segments_for_clip_window(
    segments: list[TranscriptSegment],
    *,
    clip_start_seconds: float,
    clip_end_seconds: float,
    relative_to_clip: bool = True,
) -> list[TranscriptSegment]:
    """Return transcript segments inside a clip window.

    When ``relative_to_clip`` is true, segment timestamps are shifted so the clip
  starts at zero. This is required when running analysis on an extracted clip file.
    """
    matching = [
        segment
        for segment in segments
        if clip_start_seconds <= segment.seconds < clip_end_seconds
    ]
    if not relative_to_clip:
        return matching

    adjusted: list[TranscriptSegment] = []
    for segment in matching:
        relative_seconds = max(0.0, segment.seconds - clip_start_seconds)
        adjusted.append(
            TranscriptSegment(
                start=format_timestamp(relative_seconds),
                seconds=relative_seconds,
                speaker=segment.speaker,
                text=segment.text,
            )
        )
    return adjusted


def format_timestamp(total_seconds: float) -> str:
    total = int(total_seconds)
    hours = total // 3600
    minutes = (total % 3600) // 60
    seconds = total % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
