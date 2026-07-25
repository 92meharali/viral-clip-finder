"""Detection confidence importance factor."""

from __future__ import annotations

from app.reframe.importance.factors.base import ImportanceFactorProvider
from app.reframe.models.speakers import SpeakerEstimationResult
from app.reframe.models.tracking import TrackingResult


class DetectionConfidenceFactor(ImportanceFactorProvider):
    """Prefer faces the detector is confident about."""

    factor_type = "detection_confidence"

    def score_frames(
        self,
        tracking: TrackingResult,
        *,
        speaker_result: SpeakerEstimationResult | None = None,
    ) -> dict[int, dict[str, float]]:
        scores: dict[int, dict[str, float]] = {}

        for frame in tracking.frames:
            scores[frame.frame_number] = {
                face.track_id: face.detection_confidence for face in frame.faces
            }

        return scores
