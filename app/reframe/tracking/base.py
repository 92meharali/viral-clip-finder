"""Abstract interface for swappable face trackers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.reframe.models.faces import FrameFaces
from app.reframe.models.tracking import TrackingResult


class FaceTracker(ABC):
    """Provider-agnostic face tracking interface.

    New trackers (DeepSORT, ByteTrack, optical flow) implement this class
    and register in :mod:`app.reframe.tracking.factory`.
    """

    @property
    @abstractmethod
    def tracker_name(self) -> str:
        """Return the tracker identifier (e.g. ``iou``)."""

    @abstractmethod
    def track(self, frames: list[FrameFaces]) -> TrackingResult:
        """Assign persistent track ids across a frame sequence.

        Args:
            frames: Chronologically ordered per-frame detections.

        Returns:
            Tracking result with per-frame tracks and track summaries.
        """

    def reset(self) -> None:
        """Clear internal tracker state. Override if needed."""
