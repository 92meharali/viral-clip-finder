"""Active speaker estimator interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.models.transcript import TranscriptSegment
from app.reframe.models.speakers import SpeakerEstimationResult
from app.reframe.models.tracking import TrackingResult


class ActiveSpeakerEstimator(ABC):
    """Estimate who is speaking across a tracked face sequence."""

    @property
    @abstractmethod
    def estimator_name(self) -> str:
        """Return the estimator backend identifier."""

    @abstractmethod
    def estimate(
        self,
        tracking: TrackingResult,
        *,
        transcript_segments: list[TranscriptSegment] | None = None,
        video_path: Path | None = None,
        video_duration: float | None = None,
    ) -> SpeakerEstimationResult:
        """Return active speaker segments and per-frame confidence."""
