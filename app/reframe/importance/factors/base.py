"""Base interfaces for importance scoring factors."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.reframe.models.speakers import SpeakerEstimationResult
from app.reframe.models.tracking import TrackingResult


class ImportanceFactorProvider(ABC):
    """Compute a normalized per-track importance factor for every frame."""

    @property
    @abstractmethod
    def factor_type(self) -> str:
        """Return the factor identifier."""

    @abstractmethod
    def score_frames(
        self,
        tracking: TrackingResult,
        *,
        speaker_result: SpeakerEstimationResult | None = None,
    ) -> dict[int, dict[str, float]]:
        """Return frame_number -> track_id -> score in ``[0, 1]``."""
