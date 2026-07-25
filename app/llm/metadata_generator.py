"""LLM-powered clip metadata generation (OpenAI provider wrapper)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from openai import OpenAI

from app.core.config import Settings
from app.core.exceptions import MetadataGenerationError
from app.models.clip import ViralClip
from app.models.metadata import ClipMetadata
from app.models.transcript import TranscriptSegment
from app.providers.openai import OpenAIClipAnalyzer


class MetadataGenerator(OpenAIClipAnalyzer):
    """Backward-compatible metadata generator alias."""

    def generate_for_clip(
        self,
        clip: ViralClip,
        segments: list[TranscriptSegment],
        *,
        index: int = 1,
    ) -> ClipMetadata:
        """Generate publishing metadata for a single clip."""
        return self.generate_metadata(clip, segments, index=index)

    def generate_batch(
        self,
        clips: Sequence[ViralClip],
        segments: list[TranscriptSegment],
        *,
        output_dir: str | Path | None = None,
    ) -> list[ClipMetadata]:
        """Generate metadata for multiple clips."""
        return self.generate_metadata_batch(clips, segments, output_dir=output_dir)


def generate_metadata(
    clips: Sequence[ViralClip],
    segments: list[TranscriptSegment],
    *,
    output_dir: str | Path | None = None,
    settings: Settings | None = None,
    client: OpenAI | None = None,
) -> list[ClipMetadata]:
    """Convenience function to generate clip publishing metadata."""
    if not clips:
        raise MetadataGenerationError("Cannot generate metadata for empty clip list")
    if not segments:
        raise MetadataGenerationError("Cannot generate metadata from empty transcript")

    analyzer = MetadataGenerator(settings=settings, client=client)
    return analyzer.generate_metadata_batch(clips, segments, output_dir=output_dir)
