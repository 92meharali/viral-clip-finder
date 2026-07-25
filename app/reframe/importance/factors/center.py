"""Frame-center importance factor."""

from __future__ import annotations

from app.reframe.importance.factors.base import ImportanceFactorProvider
from app.reframe.models.speakers import SpeakerEstimationResult
from app.reframe.models.tracking import TrackingResult


class FrameCenterFactor(ImportanceFactorProvider):
    """Prefer faces near the horizontal center of the frame."""

    factor_type = "frame_center"

    def score_frames(
        self,
        tracking: TrackingResult,
        *,
        speaker_result: SpeakerEstimationResult | None = None,
    ) -> dict[int, dict[str, float]]:
        scores: dict[int, dict[str, float]] = {}

        for frame in tracking.frames:
            frame_center_x = frame.image_width / 2
            max_distance = frame.image_width / 2
            frame_scores: dict[str, float] = {}

            for face in frame.faces:
                distance = abs(face.bounding_box.center_x - frame_center_x)
                frame_scores[face.track_id] = max(
                    0.0,
                    1.0 - (distance / max_distance if max_distance > 0 else 1.0),
                )

            scores[frame.frame_number] = frame_scores

        return scores
