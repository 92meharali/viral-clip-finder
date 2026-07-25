"""Abstract interface for AI clip analysis providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path

from app.core.config import Settings, get_settings
from app.models.clip import RankedClip, ViralClip
from app.models.metadata import ClipMetadata
from app.models.transcript import TranscriptSegment
from app.services.clip_ranker import rank_clips


class ClipAnalyzer(ABC):
    """Provider-agnostic interface for all AI-assisted clip operations.

    The rest of the application interacts only with this interface.
    Individual providers encapsulate how each model is invoked.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the provider with optional settings override."""
        self.settings = settings or get_settings()

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider identifier (e.g. ``cursor``, ``openai``)."""

    @abstractmethod
    def analyze_transcript(self, segments: list[TranscriptSegment]) -> list[ViralClip]:
        """Detect viral clip candidates from parsed transcript segments.

        Args:
            segments: Chronologically ordered transcript segments.

        Returns:
            Detected viral clips sorted by score descending.
        """

    def rank_candidates(
        self,
        clips: list[ViralClip],
        segments: list[TranscriptSegment],
        *,
        top_n: int | None = None,
    ) -> list[RankedClip]:
        """Rank and select top clip candidates.

        Default implementation uses deterministic composite scoring.
        Providers may override for model-assisted ranking.
        """
        return rank_clips(clips, segments, top_n=top_n, settings=self.settings)

    @abstractmethod
    def generate_metadata(
        self,
        clip: ViralClip,
        segments: list[TranscriptSegment],
        *,
        index: int = 1,
    ) -> ClipMetadata:
        """Generate publishing metadata for a single clip."""

    def generate_metadata_batch(
        self,
        clips: Sequence[ViralClip],
        segments: list[TranscriptSegment],
        *,
        output_dir: str | Path | None = None,
    ) -> list[ClipMetadata]:
        """Generate metadata for multiple clips."""
        from app.providers.metadata_io import save_metadata

        results: list[ClipMetadata] = []
        for index, clip in enumerate(clips, start=1):
            metadata = self.generate_metadata(clip, segments, index=index)
            if output_dir is not None:
                metadata = save_metadata(metadata, output_dir)
            results.append(metadata)
        return results
