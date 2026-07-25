"""Tests for LLM clip analysis."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.core.exceptions import LLMAnalysisError
from app.llm.analyzer import OpenAIClipAnalyzer, analyze_transcript
from app.llm.client import create_openai_client
from app.llm.json_utils import parse_llm_json
from app.models.clip import ClipAnalysisResponse
from app.models.transcript import TranscriptSegment

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        openai_api_key="test-key",
        openai_model="gpt-4o",
        openai_temperature=0.7,
        max_clips=10,
        min_clip_duration_seconds=20,
        max_clip_duration_seconds=90,
    )


@pytest.fixture
def sample_segments() -> list[TranscriptSegment]:
    return [
        TranscriptSegment(
            start="00:00:13",
            seconds=13.0,
            speaker="Player A",
            text="I didn't kill him.",
        ),
        TranscriptSegment(
            start="00:00:19",
            seconds=19.0,
            speaker="Player B",
            text="You're lying.",
        ),
    ]


@pytest.fixture
def llm_response_json() -> str:
    return (FIXTURES / "llm_clip_response.json").read_text(encoding="utf-8")


def _make_mock_client(response_content: str) -> MagicMock:
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = response_content
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


class TestParseLlmJson:
    def test_parses_valid_json(self, llm_response_json: str) -> None:
        result = parse_llm_json(llm_response_json, ClipAnalysisResponse)
        assert len(result.clips) == 2

    def test_strips_markdown_fences(self, llm_response_json: str) -> None:
        fenced = f"```json\n{llm_response_json}\n```"
        result = parse_llm_json(fenced, ClipAnalysisResponse)
        assert len(result.clips) == 2

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(LLMAnalysisError, match="invalid JSON"):
            parse_llm_json("not json", ClipAnalysisResponse)


class TestClipAnalyzer:
    def test_analyze_returns_sorted_clips(
        self,
        settings: Settings,
        sample_segments: list[TranscriptSegment],
        llm_response_json: str,
    ) -> None:
        analyzer = OpenAIClipAnalyzer(
            settings=settings,
            client=_make_mock_client(llm_response_json),
        )
        clips = analyzer.analyze_transcript(sample_segments)

        assert len(clips) == 2
        assert clips[0].viral_score >= clips[1].viral_score
        assert clips[0].emotion == "betrayal"
        assert clips[0].duration_seconds == 32.0

    def test_empty_transcript_raises(self, settings: Settings) -> None:
        analyzer = OpenAIClipAnalyzer(settings=settings, client=MagicMock())
        with pytest.raises(LLMAnalysisError, match="empty transcript"):
            analyzer.analyze_transcript([])

    def test_empty_llm_response_raises(
        self,
        settings: Settings,
        sample_segments: list[TranscriptSegment],
    ) -> None:
        analyzer = OpenAIClipAnalyzer(
            settings=settings,
            client=_make_mock_client(""),
        )
        with pytest.raises(LLMAnalysisError, match="empty response"):
            analyzer.analyze_transcript(sample_segments)

    def test_api_failure_raises(
        self,
        settings: Settings,
        sample_segments: list[TranscriptSegment],
    ) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("API down")
        analyzer = OpenAIClipAnalyzer(settings=settings, client=mock_client)

        with pytest.raises(LLMAnalysisError, match="API call failed"):
            analyzer.analyze_transcript(sample_segments)

    def test_skips_invalid_clips(
        self,
        settings: Settings,
        sample_segments: list[TranscriptSegment],
    ) -> None:
        payload = json.dumps(
            {
                "clips": [
                    {
                        "start": "00:01:00",
                        "end": "00:00:30",
                        "reason": "Invalid timestamps",
                        "viral_score": 5.0,
                        "emotion": "confusion",
                        "hook": "Bad clip",
                        "summary": "End before start",
                    },
                    {
                        "start": "00:00:13",
                        "end": "00:00:45",
                        "reason": "Valid clip",
                        "viral_score": 9.0,
                        "emotion": "betrayal",
                        "hook": "Good clip",
                        "summary": "This one is fine",
                    },
                ]
            }
        )
        analyzer = OpenAIClipAnalyzer(settings=settings, client=_make_mock_client(payload))
        clips = analyzer.analyze_transcript(sample_segments)

        assert len(clips) == 1
        assert clips[0].viral_score == 9.0

    def test_analyze_transcript_convenience_function(
        self,
        settings: Settings,
        sample_segments: list[TranscriptSegment],
        llm_response_json: str,
    ) -> None:
        clips = analyze_transcript(
            sample_segments,
            settings=settings,
            client=_make_mock_client(llm_response_json),
        )
        assert len(clips) == 2


class TestOpenAIClient:
    def test_missing_api_key_raises(self) -> None:
        with pytest.raises(LLMAnalysisError, match="API key"):
            create_openai_client(Settings(openai_api_key=""))

    def test_creates_client_with_key(self, settings: Settings) -> None:
        client = create_openai_client(settings)
        assert client is not None
