"""Tests for Gemini clip analyzer."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.core.exceptions import LLMAnalysisError, MetadataGenerationError
from app.models.clip import ViralClip
from app.models.transcript import TranscriptSegment
from app.providers.gemini import GeminiClipAnalyzer


def _sample_segments() -> list[TranscriptSegment]:
    return [
        TranscriptSegment(start="00:00:00", seconds=0.0, text="Hello world"),
        TranscriptSegment(start="00:00:05", seconds=5.0, text="This is viral content"),
    ]


def _clip_analysis_json() -> str:
    return """
    {
      "clips": [
        {
          "start": "00:00:00",
          "end": "00:00:10",
          "score": 8.5,
          "emotion": "excitement",
          "hook": "You need to hear this",
          "reason": "Strong opening hook"
        }
      ]
    }
    """


def _metadata_json() -> str:
    return """
    {
      "title": "Viral Moment",
      "title_variations": ["Alt title", "Second title"],
      "hook": "You need to hear this",
      "description": "A standout clip",
      "hashtags": ["#viral", "#clips", "#shorts"],
      "call_to_action": "Follow for more",
      "seo_keywords": ["viral", "clip", "shorts"]
    }
    """


class TestGeminiClipAnalyzer:
    def test_analyze_transcript_parses_json_response(self) -> None:
        client = MagicMock()
        client.models.generate_content.return_value = MagicMock(text=_clip_analysis_json())
        analyzer = GeminiClipAnalyzer(Settings(gemini_api_key="test-key"), client=client)

        clips = analyzer.analyze_transcript(_sample_segments())

        assert len(clips) == 1
        assert clips[0].viral_score == 8.5
        assert clips[0].emotion == "excitement"

    def test_analyze_empty_transcript_raises(self) -> None:
        analyzer = GeminiClipAnalyzer(Settings(gemini_api_key="test-key"), client=MagicMock())

        with pytest.raises(LLMAnalysisError, match="empty transcript"):
            analyzer.analyze_transcript([])

    def test_generate_metadata_parses_json_response(self) -> None:
        client = MagicMock()
        client.models.generate_content.return_value = MagicMock(text=_metadata_json())
        analyzer = GeminiClipAnalyzer(Settings(gemini_api_key="test-key"), client=client)
        clip = ViralClip(
            start="00:00:00",
            end="00:00:10",
            viral_score=8.5,
            emotion="excitement",
            hook="You need to hear this",
            reason="Strong opening hook",
            summary="Strong opening hook",
            start_seconds=0.0,
            end_seconds=10.0,
            duration_seconds=10.0,
        )

        metadata = analyzer.generate_metadata(clip, _sample_segments(), index=1)

        assert metadata.title == "Viral Moment"
        assert metadata.hashtags == ["#viral", "#clips", "#shorts"]

    def test_api_failure_raises_metadata_error(self) -> None:
        client = MagicMock()
        client.models.generate_content.side_effect = RuntimeError("quota exceeded")
        analyzer = GeminiClipAnalyzer(Settings(gemini_api_key="test-key"), client=client)
        clip = ViralClip(
            start="00:00:00",
            end="00:00:10",
            viral_score=8.5,
            emotion="excitement",
            hook="Hook",
            reason="Reason",
            summary="Summary",
            start_seconds=0.0,
            end_seconds=10.0,
            duration_seconds=10.0,
        )

        with pytest.raises(MetadataGenerationError, match="quota exceeded"):
            analyzer.generate_metadata(clip, _sample_segments(), index=1)
