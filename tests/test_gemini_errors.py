"""Tests for Gemini API error helpers."""

from __future__ import annotations

from app.llm.gemini_errors import (
    format_gemini_error,
    has_zero_free_tier_quota,
    is_gemini_rate_limit_error,
    parse_retry_delay_seconds,
    should_retry_gemini_error,
)

_SAMPLE_429 = (
    "429 RESOURCE_EXHAUSTED. {'error': {'message': "
    "'Quota exceeded ... limit: 0, model: gemini-2.0-flash Please retry in 36.3s.'}}"
)
_SAMPLE_TEMPORARY_429 = (
    "429 RESOURCE_EXHAUSTED. {'error': {'message': "
    "'Rate limit exceeded. Please retry in 12.5s.'}}"
)


class TestGeminiErrors:
    def test_detects_rate_limit(self) -> None:
        assert is_gemini_rate_limit_error(RuntimeError(_SAMPLE_429))

    def test_detects_zero_quota(self) -> None:
        assert has_zero_free_tier_quota(RuntimeError(_SAMPLE_429))
        assert not has_zero_free_tier_quota(RuntimeError(_SAMPLE_TEMPORARY_429))

    def test_parses_retry_delay(self) -> None:
        assert parse_retry_delay_seconds(RuntimeError(_SAMPLE_429)) == 36.3

    def test_zero_quota_message_is_actionable(self) -> None:
        message = format_gemini_error(RuntimeError(_SAMPLE_429), model="gemini-2.0-flash")
        assert "free-tier quota is not available" in message
        assert "aistudio.google.com/apikey" in message

    def test_should_not_retry_zero_quota(self) -> None:
        assert not should_retry_gemini_error(RuntimeError(_SAMPLE_429), attempt=1, max_attempts=3)

    def test_should_retry_temporary_rate_limit(self) -> None:
        assert should_retry_gemini_error(
            RuntimeError(_SAMPLE_TEMPORARY_429),
            attempt=1,
            max_attempts=3,
        )
