"""Future enrichment modules for candidate window generation.

These interfaces define extension points for scene detection, audio analysis,
emotion detection, frame sampling, and face tracking. Implementations will plug
into the candidate window generator without changing the core pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models.transcript import TranscriptSegment


@dataclass(frozen=True)
class EnrichmentSignal:
    """A scored signal from an enrichment module."""

    start_seconds: float
    end_seconds: float
    signal_type: str
    score: float
    label: str
    details: str = ""


class EnrichmentModule(ABC):
    """Base class for transcript/video enrichment modules."""

    @property
    @abstractmethod
    def module_name(self) -> str:
        """Return the module identifier."""

    @abstractmethod
    def analyze(
        self,
        segments: list[TranscriptSegment],
        *,
        video_path: str | None = None,
    ) -> list[EnrichmentSignal]:
        """Produce enrichment signals for candidate window generation."""


class SceneDetector(EnrichmentModule):
    """Detect scene changes to anchor candidate windows."""

    @property
    def module_name(self) -> str:
        return "scene_detection"

    @abstractmethod
    def analyze(
        self,
        segments: list[TranscriptSegment],
        *,
        video_path: str | None = None,
    ) -> list[EnrichmentSignal]:
        """Return scene-boundary signals."""


class AudioAnalyzer(EnrichmentModule):
    """Detect volume spikes, silence, and laughter from audio."""

    @property
    def module_name(self) -> str:
        return "audio_analysis"

    @abstractmethod
    def analyze(
        self,
        segments: list[TranscriptSegment],
        *,
        video_path: str | None = None,
    ) -> list[EnrichmentSignal]:
        """Return audio-based signals."""


class EmotionDetector(EnrichmentModule):
    """Detect emotional peaks from transcript and optional video."""

    @property
    def module_name(self) -> str:
        return "emotion_detection"

    @abstractmethod
    def analyze(
        self,
        segments: list[TranscriptSegment],
        *,
        video_path: str | None = None,
    ) -> list[EnrichmentSignal]:
        """Return emotion-based signals."""


class FrameSampler(EnrichmentModule):
    """Sample video frames for visual interest scoring."""

    @property
    def module_name(self) -> str:
        return "frame_sampling"

    @abstractmethod
    def analyze(
        self,
        segments: list[TranscriptSegment],
        *,
        video_path: str | None = None,
    ) -> list[EnrichmentSignal]:
        """Return frame-sampling signals."""


class FaceTracker(EnrichmentModule):
    """Track faces to prioritize speaker-focused moments."""

    @property
    def module_name(self) -> str:
        return "face_tracking"

    @abstractmethod
    def analyze(
        self,
        segments: list[TranscriptSegment],
        *,
        video_path: str | None = None,
    ) -> list[EnrichmentSignal]:
        """Return face-tracking signals."""
