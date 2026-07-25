"""Recent-speaker importance factor."""

from __future__ import annotations

import math

from app.core.config import Settings, get_settings
from app.reframe.importance.factors.base import ImportanceFactorProvider
from app.reframe.models.speakers import SpeakerEstimationResult
from app.reframe.models.tracking import TrackingResult


class RecentSpeakerFactor(ImportanceFactorProvider):
    """Give residual attention to people who spoke recently."""

    factor_type = "recent_speaker"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def score_frames(
        self,
        tracking: TrackingResult,
        *,
        speaker_result: SpeakerEstimationResult | None = None,
    ) -> dict[int, dict[str, float]]:
        if speaker_result is None or not speaker_result.segments:
            return {}

        decay_seconds = self.settings.importance_recent_speaker_decay_seconds
        scores: dict[int, dict[str, float]] = {}

        for frame in tracking.frames:
            frame_scores: dict[str, float] = {}
            for face in frame.faces:
                frame_scores[face.track_id] = _recent_speaker_score(
                    face.track_id,
                    frame.timestamp,
                    speaker_result,
                    decay_seconds=decay_seconds,
                )
            scores[frame.frame_number] = frame_scores

        return scores


def _recent_speaker_score(
    track_id: str,
    timestamp: float,
    speaker_result: SpeakerEstimationResult,
    *,
    decay_seconds: float,
) -> float:
    best_score = 0.0

    for segment in speaker_result.segments:
        if segment.track_id != track_id:
            continue

        if segment.start_time <= timestamp <= segment.end_time:
            return 1.0

        if timestamp > segment.end_time:
            elapsed = timestamp - segment.end_time
            if decay_seconds <= 0:
                continue
            score = math.exp(-elapsed / decay_seconds)
            best_score = max(best_score, score)

    return min(1.0, best_score)
