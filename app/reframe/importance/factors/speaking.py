"""Currently-speaking importance factor."""

from __future__ import annotations

from app.reframe.importance.factors.base import ImportanceFactorProvider
from app.reframe.models.speakers import SpeakerEstimationResult
from app.reframe.models.tracking import TrackingResult


class CurrentlySpeakingFactor(ImportanceFactorProvider):
    """Boost the track estimated to be actively speaking."""

    factor_type = "currently_speaking"

    def score_frames(
        self,
        tracking: TrackingResult,
        *,
        speaker_result: SpeakerEstimationResult | None = None,
    ) -> dict[int, dict[str, float]]:
        if speaker_result is None:
            return {}

        speaker_by_frame = {
            frame.frame_number: frame for frame in speaker_result.frames
        }
        scores: dict[int, dict[str, float]] = {}

        for frame in tracking.frames:
            speaker_frame = speaker_by_frame.get(frame.frame_number)
            if speaker_frame is None:
                scores[frame.frame_number] = {}
                continue

            frame_scores: dict[str, float] = {}
            for track_id, confidence in speaker_frame.track_scores.items():
                frame_scores[track_id] = confidence

            if speaker_frame.active_track_id is not None:
                frame_scores[speaker_frame.active_track_id] = max(
                    frame_scores.get(speaker_frame.active_track_id, 0.0),
                    1.0,
                )

            scores[frame.frame_number] = frame_scores

        return scores
