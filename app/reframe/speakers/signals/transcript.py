"""Transcript timing signal for active speaker estimation."""

from __future__ import annotations

from pathlib import Path

from app.models.transcript import TranscriptSegment
from app.reframe.models.tracking import TrackingResult
from app.reframe.speakers.signals.mouth import MouthMovementSignal


def _build_speech_windows(
    segments: list[TranscriptSegment],
    *,
    video_duration: float | None,
) -> list[tuple[float, float, str | None]]:
    """Convert transcript segments into ``(start, end, speaker)`` windows."""
    if not segments:
        return []

    sorted_segments = sorted(segments, key=lambda segment: segment.seconds)
    windows: list[tuple[float, float, str | None]] = []

    for index, segment in enumerate(sorted_segments):
        start = segment.seconds
        if index + 1 < len(sorted_segments):
            end = sorted_segments[index + 1].seconds
        elif video_duration is not None:
            end = max(start + 1.0, video_duration)
        else:
            end = start + max(2.0, len(segment.text.split()) * 0.35)

        if end <= start:
            end = start + 0.5

        windows.append((start, end, segment.speaker))

    return windows


def _speech_activity(timestamp: float, windows: list[tuple[float, float, str | None]]) -> float:
    """Return 1.0 when dialogue is active at ``timestamp``, else 0.0."""
    for start, end, _speaker in windows:
        if start <= timestamp < end:
            return 1.0
    return 0.0


class TranscriptTimingSignal:
    """Boost visible tracks while transcript dialogue is active."""

    signal_type = "transcript_timing"

    def score_frames(
        self,
        tracking: TrackingResult,
        *,
        transcript_segments: list[TranscriptSegment] | None = None,
        video_path: Path | None = None,
        video_duration: float | None = None,
    ) -> dict[int, dict[str, float]]:
        windows = _build_speech_windows(transcript_segments or [], video_duration=video_duration)
        mouth_by_frame = MouthMovementSignal().score_frames(tracking)
        scores: dict[int, dict[str, float]] = {}

        for frame in tracking.frames:
            activity = _speech_activity(frame.timestamp, windows)
            if activity <= 0 or not frame.faces:
                scores[frame.frame_number] = {}
                continue

            visible_tracks = [face.track_id for face in frame.faces]
            if len(visible_tracks) == 1:
                scores[frame.frame_number] = {visible_tracks[0]: 1.0}
                continue

            # During dialogue, prefer the track with the most mouth movement.
            mouth_scores = mouth_by_frame.get(frame.frame_number, {})
            if mouth_scores:
                leader = max(mouth_scores.items(), key=lambda item: item[1])[0]
                scores[frame.frame_number] = {
                    track_id: (1.0 if track_id == leader else 0.2)
                    for track_id in visible_tracks
                }
            else:
                neutral = 0.35
                scores[frame.frame_number] = {
                    track_id: neutral for track_id in visible_tracks
                }

        return scores
