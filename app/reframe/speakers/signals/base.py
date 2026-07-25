"""Base interfaces for active speaker signal providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.models.transcript import TranscriptSegment
from app.reframe.models.tracking import TrackingResult


class SpeakerSignalProvider(ABC):
    """Compute a normalized per-track score for every tracked frame."""

    @property
    @abstractmethod
    def signal_type(self) -> str:
        """Return the signal identifier."""

    @abstractmethod
    def score_frames(
        self,
        tracking: TrackingResult,
        *,
        transcript_segments: list[TranscriptSegment] | None = None,
        video_path: Path | None = None,
        video_duration: float | None = None,
    ) -> dict[int, dict[str, float]]:
        """Return frame_number -> track_id -> score in ``[0, 1]``."""
