"""Abstract interface for swappable face detectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.reframe.models.faces import DetectedFace


class FaceDetector(ABC):
    """Provider-agnostic face detection interface.

  New detectors (YOLO, RetinaFace, etc.) implement this class and register
  in :mod:`app.reframe.detection.factory` without changing the pipeline.
    """

    @property
    @abstractmethod
    def detector_name(self) -> str:
        """Return the detector identifier (e.g. ``mediapipe``)."""

    @abstractmethod
    def detect(
        self,
        image_path: str,
        *,
        frame_number: int = 0,
        timestamp: float = 0.0,
    ) -> list[DetectedFace]:
        """Detect faces in a single frame image.

        Args:
            image_path: Path to a JPEG or PNG frame image.
            frame_number: Source frame index for id assignment.
            timestamp: Source timestamp in seconds.

        Returns:
            Detected faces sorted by confidence descending.
        """

    def close(self) -> None:
        """Release detector resources. Override if needed."""
