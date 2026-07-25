"""Abstract interface for swappable scene detectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.reframe.models.scenes import SceneDetectionResult


class SceneDetector(ABC):
    """Provider-agnostic scene boundary detection interface.

    Future detectors (PySceneDetect, neural shot detectors) implement this
    class and register in :mod:`app.reframe.scenes.factory`.
    """

    @property
    @abstractmethod
    def detector_name(self) -> str:
        """Return the detector identifier (e.g. ``ffmpeg``)."""

    @abstractmethod
    def detect(self, video_path: str | Path) -> SceneDetectionResult:
        """Detect scene boundaries in a video file.

        Args:
            video_path: Source video path.

        Returns:
            Scene boundaries and derived segments.
        """
