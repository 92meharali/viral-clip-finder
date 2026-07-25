"""Reaction-target importance factor."""

from __future__ import annotations

from app.reframe.importance.factors.base import ImportanceFactorProvider
from app.reframe.importance.factors.expression import FacialExpressionFactor
from app.reframe.importance.factors.presence import ScreenPresenceFactor
from app.reframe.models.speakers import SpeakerEstimationResult
from app.reframe.models.tracking import TrackingResult


class ReactionTargetFactor(ImportanceFactorProvider):
    """Boost central listeners while others around them are animated."""

    factor_type = "reaction_target"

    def __init__(self) -> None:
        self._expression_factor = FacialExpressionFactor()
        self._presence_factor = ScreenPresenceFactor()

    def score_frames(
        self,
        tracking: TrackingResult,
        *,
        speaker_result: SpeakerEstimationResult | None = None,
    ) -> dict[int, dict[str, float]]:
        expression_scores = self._expression_factor.score_frames(
            tracking,
            speaker_result=speaker_result,
        )
        presence_scores = self._presence_factor.score_frames(
            tracking,
            speaker_result=speaker_result,
        )
        scores: dict[int, dict[str, float]] = {}

        for frame in tracking.frames:
            frame_expression = expression_scores.get(frame.frame_number, {})
            frame_presence = presence_scores.get(frame.frame_number, {})
            if len(frame.faces) < 2:
                scores[frame.frame_number] = {}
                continue

            animated_others = [
                face.track_id
                for face in frame.faces
                if frame_expression.get(face.track_id, 0.0) >= 0.5
            ]
            if not animated_others:
                scores[frame.frame_number] = {}
                continue

            frame_scores: dict[str, float] = {}
            for face in frame.faces:
                expression = frame_expression.get(face.track_id, 0.0)
                presence = frame_presence.get(face.track_id, 0.0)
                if expression >= 0.4:
                    frame_scores[face.track_id] = 0.0
                    continue

                others_animated = any(
                    track_id != face.track_id for track_id in animated_others
                )
                if others_animated and presence >= 0.5:
                    frame_scores[face.track_id] = min(1.0, presence * 0.7 + 0.3)
                else:
                    frame_scores[face.track_id] = 0.0

            scores[frame.frame_number] = frame_scores

        return scores
