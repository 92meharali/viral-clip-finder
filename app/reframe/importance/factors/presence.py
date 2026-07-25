"""Screen presence importance factor."""

from __future__ import annotations

from app.reframe.importance.factors.base import ImportanceFactorProvider
from app.reframe.models.speakers import SpeakerEstimationResult
from app.reframe.models.tracking import TrackingResult


class ScreenPresenceFactor(ImportanceFactorProvider):
    """Prefer larger, more visually dominant faces."""

    factor_type = "screen_presence"

    def score_frames(
        self,
        tracking: TrackingResult,
        *,
        speaker_result: SpeakerEstimationResult | None = None,
    ) -> dict[int, dict[str, float]]:
        scores: dict[int, dict[str, float]] = {}

        for frame in tracking.frames:
            if not frame.faces:
                scores[frame.frame_number] = {}
                continue

            max_area = max(face.bounding_box.area for face in frame.faces)
            scores[frame.frame_number] = {
                face.track_id: (face.bounding_box.area / max_area if max_area > 0 else 0.0)
                for face in frame.faces
            }

        return scores
