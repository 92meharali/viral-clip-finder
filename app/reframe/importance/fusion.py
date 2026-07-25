"""Multi-factor importance fusion scorer."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.reframe.importance.base import ImportanceScorer
from app.reframe.importance.factors.center import FrameCenterFactor
from app.reframe.importance.factors.detection import DetectionConfidenceFactor
from app.reframe.importance.factors.expression import FacialExpressionFactor
from app.reframe.importance.factors.presence import ScreenPresenceFactor
from app.reframe.importance.factors.reaction import ReactionTargetFactor
from app.reframe.importance.factors.recent_speaker import RecentSpeakerFactor
from app.reframe.importance.factors.speaking import CurrentlySpeakingFactor
from app.reframe.models.importance import (
    FrameImportance,
    ImportanceFactor,
    ImportanceScore,
    ImportanceScoringResult,
)
from app.reframe.models.speakers import SpeakerEstimationResult
from app.reframe.models.tracking import TrackingResult

_FACTOR_LABELS = {
    "currently_speaking": "currently speaking",
    "facial_expression": "expressive face",
    "detection_confidence": "high detection confidence",
    "frame_center": "center of frame",
    "screen_presence": "large screen presence",
    "recent_speaker": "recent speaker",
    "reaction_target": "reaction focus",
}


class FusionImportanceScorer(ImportanceScorer):
    """Fuse speaking, expression, presence, and reaction factors."""

    scorer_name = "fusion"

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        speaking_factor: CurrentlySpeakingFactor | None = None,
        expression_factor: FacialExpressionFactor | None = None,
        detection_factor: DetectionConfidenceFactor | None = None,
        center_factor: FrameCenterFactor | None = None,
        presence_factor: ScreenPresenceFactor | None = None,
        recent_speaker_factor: RecentSpeakerFactor | None = None,
        reaction_factor: ReactionTargetFactor | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._speaking_factor = speaking_factor or CurrentlySpeakingFactor()
        self._expression_factor = expression_factor or FacialExpressionFactor()
        self._detection_factor = detection_factor or DetectionConfidenceFactor()
        self._center_factor = center_factor or FrameCenterFactor()
        self._presence_factor = presence_factor or ScreenPresenceFactor()
        self._recent_speaker_factor = recent_speaker_factor or RecentSpeakerFactor(
            self.settings
        )
        self._reaction_factor = reaction_factor or ReactionTargetFactor()

    def score(
        self,
        tracking: TrackingResult,
        *,
        speaker_result: SpeakerEstimationResult | None = None,
    ) -> ImportanceScoringResult:
        if not tracking.frames:
            return ImportanceScoringResult()

        providers = [
            self._speaking_factor,
            self._expression_factor,
            self._detection_factor,
            self._center_factor,
            self._presence_factor,
            self._recent_speaker_factor,
            self._reaction_factor,
        ]
        factor_maps = {
            provider.factor_type: provider.score_frames(
                tracking,
                speaker_result=speaker_result,
            )
            for provider in providers
        }
        weights = _factor_weights(self.settings)

        frame_results: list[FrameImportance] = []
        for frame in tracking.frames:
            track_ids = {face.track_id for face in frame.faces}
            frame_scores: list[ImportanceScore] = []

            for track_id in track_ids:
                factors: list[ImportanceFactor] = []
                weighted_total = 0.0
                weight_sum = 0.0

                for factor_type, frame_map in factor_maps.items():
                    factor_score = frame_map.get(frame.frame_number, {}).get(track_id, 0.0)
                    weight = weights.get(factor_type, 0.0)
                    factors.append(ImportanceFactor(factor_type=factor_type, score=factor_score))
                    weighted_total += weight * factor_score
                    weight_sum += weight

                final_score = weighted_total / weight_sum if weight_sum > 0 else 0.0
                frame_scores.append(
                    ImportanceScore(
                        track_id=track_id,
                        score=final_score,
                        reasoning=_build_reasoning(factors),
                        factors=factors,
                    )
                )

            frame_scores.sort(key=lambda item: item.score, reverse=True)
            frame_results.append(
                FrameImportance(
                    frame_number=frame.frame_number,
                    timestamp=frame.timestamp,
                    scores=frame_scores,
                )
            )

        return ImportanceScoringResult(frames=frame_results)


def _factor_weights(settings: Settings) -> dict[str, float]:
    return {
        "currently_speaking": settings.importance_weight_speaking,
        "facial_expression": settings.importance_weight_expression,
        "detection_confidence": settings.importance_weight_detection,
        "frame_center": settings.importance_weight_center,
        "screen_presence": settings.importance_weight_presence,
        "recent_speaker": settings.importance_weight_recent_speaker,
        "reaction_target": settings.importance_weight_reaction,
    }


def _build_reasoning(
    factors: list[ImportanceFactor],
    *,
    threshold: float = 0.55,
) -> str:
    ranked = sorted(factors, key=lambda factor: factor.score, reverse=True)
    reasons = [
        _FACTOR_LABELS.get(factor.factor_type, factor.factor_type.replace("_", " "))
        for factor in ranked
        if factor.score >= threshold
    ]

    if not reasons and ranked:
        top = ranked[0]
        reasons = [
            _FACTOR_LABELS.get(top.factor_type, top.factor_type.replace("_", " "))
        ]

    return "; ".join(reasons) if reasons else "visible participant"
