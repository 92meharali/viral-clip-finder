"""Tests for AI response parsing."""

from pathlib import Path

import pytest

from app.core.exceptions import LLMAnalysisError
from app.providers.response_parser import parse_clip_analysis_response

FIXTURES = Path(__file__).parent / "fixtures"


class TestParseClipAnalysisResponse:
    def test_parses_wrapped_clips_format(self) -> None:
        content = (FIXTURES / "llm_clip_response.json").read_text(encoding="utf-8")
        clips = parse_clip_analysis_response(content)
        assert len(clips) == 2
        assert clips[0].viral_score >= clips[1].viral_score

    def test_parses_array_format_with_score_alias(self) -> None:
        content = """[
          {
            "start": "00:01:00",
            "end": "00:01:30",
            "score": 9.8,
            "emotion": "betrayal",
            "hook": "He trusted the wrong player.",
            "reason": "Major alliance collapse."
          }
        ]"""
        clips = parse_clip_analysis_response(content)
        assert len(clips) == 1
        assert clips[0].viral_score == 9.8
        assert clips[0].summary == "Major alliance collapse."

    def test_invalid_json_raises_with_details(self) -> None:
        with pytest.raises(LLMAnalysisError, match="Invalid JSON"):
            parse_clip_analysis_response("{not json")

    def test_missing_required_fields_raises(self) -> None:
        with pytest.raises(LLMAnalysisError, match="failed validation"):
            parse_clip_analysis_response('[{"start": "00:00:01"}]')

    def test_strips_markdown_fences(self) -> None:
        content = """```json
        [{"start":"00:00:10","end":"00:00:40","score":8.0,"emotion":"shock","hook":"Wow","reason":"Reveal"}]
        ```"""
        clips = parse_clip_analysis_response(content)
        assert len(clips) == 1
