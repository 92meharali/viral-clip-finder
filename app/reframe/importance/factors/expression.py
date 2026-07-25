"""Facial expression importance factor."""

from __future__ import annotations

import math

from app.reframe.importance.factors.base import ImportanceFactorProvider
from app.reframe.models.speakers import SpeakerEstimationResult
from app.reframe.models.tracking import TrackingResult, TrackedFace


def _mouth_point(track_face: TrackedFace) -> tuple[float, float] | None:
    if track_face.landmarks is not None and track_face.landmarks.mouth is not None:
        return track_face.landmarks.mouth

    bbox = track_face.bounding_box
    return (bbox.center_x, bbox.y + bbox.height * 0.75)


def _movement_delta(
    current: tuple[float, float] | None,
    previous: tuple[float, float] | None,
) -> float:
    if current is None or previous is None:
        return 0.0
    return math.hypot(current[0] - previous[0], current[1] - previous[1])


class FacialExpressionFactor(ImportanceFactorProvider):
    """Use mouth movement as a proxy for expressive faces."""

    factor_type = "facial_expression"

    def __init__(self, *, movement_scale: float = 12.0) -> None:
        self.movement_scale = movement_scale

    def score_frames(
        self,
        tracking: TrackingResult,
        *,
        speaker_result: SpeakerEstimationResult | None = None,
    ) -> dict[int, dict[str, float]]:
        previous_points: dict[str, tuple[float, float] | None] = {}
        raw_scores: dict[int, dict[str, float]] = {}

        for frame in tracking.frames:
            frame_scores: dict[str, float] = {}
            for face in frame.faces:
                point = _mouth_point(face)
                delta = _movement_delta(point, previous_points.get(face.track_id))
                previous_points[face.track_id] = point
                frame_scores[face.track_id] = delta
            raw_scores[frame.frame_number] = frame_scores

        normalized: dict[int, dict[str, float]] = {}
        for frame_number, track_scores in raw_scores.items():
            if not track_scores:
                normalized[frame_number] = {}
                continue

            normalized[frame_number] = {
                track_id: min(1.0, delta / self.movement_scale) if delta > 0 else 0.0
                for track_id, delta in track_scores.items()
            }

        return normalized
