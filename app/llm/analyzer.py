"""LLM-powered viral clip detection (OpenAI provider wrapper)."""

from __future__ import annotations

from openai import OpenAI

from app.core.config import Settings
from app.models.clip import ViralClip
from app.models.transcript import TranscriptSegment
from app.providers.openai import OpenAIClipAnalyzer

__all__ = ["OpenAIClipAnalyzer", "analyze_transcript"]


def analyze_transcript(
    segments: list[TranscriptSegment],
    *,
    settings: Settings | None = None,
    client: OpenAI | None = None,
) -> list[ViralClip]:
    """Convenience function to analyze transcript segments for viral clips."""
    return OpenAIClipAnalyzer(settings=settings, client=client).analyze_transcript(segments)
