"""Importance scoring package."""

from app.reframe.importance.factory import SUPPORTED_IMPORTANCE_SCORERS, get_importance_scorer
from app.reframe.importance.service import (
    ImportanceScoringService,
    score_importance,
    score_importance_in_video,
)

__all__ = [
    "ImportanceScoringService",
    "SUPPORTED_IMPORTANCE_SCORERS",
    "get_importance_scorer",
    "score_importance",
    "score_importance_in_video",
]
