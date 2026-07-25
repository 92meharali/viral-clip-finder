"""Importance scorer interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.reframe.models.importance import ImportanceScoringResult
from app.reframe.models.speakers import SpeakerEstimationResult
from app.reframe.models.tracking import TrackingResult


class ImportanceScorer(ABC):
    """Score how much attention each tracked person deserves."""

    @property
    @abstractmethod
    def scorer_name(self) -> str:
        """Return the scorer backend identifier."""

    @abstractmethod
    def score(
        self,
        tracking: TrackingResult,
        *,
        speaker_result: SpeakerEstimationResult | None = None,
    ) -> ImportanceScoringResult:
        """Return per-frame importance scores for all visible tracks."""
