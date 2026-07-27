"""Tests for AI provider factory."""

import pytest

from app.core.config import Settings
from app.core.exceptions import LLMAnalysisError, UnknownProviderError
from app.providers.cursor_manual import CursorManualClipAnalyzer
from app.providers.factory import SUPPORTED_PROVIDERS, ensure_provider_ready, get_clip_analyzer
from app.providers.gemini import GeminiClipAnalyzer
from app.providers.openai import OpenAIClipAnalyzer


class TestProviderFactory:
    def test_supported_providers(self) -> None:
        assert "cursor" in SUPPORTED_PROVIDERS
        assert "openai" in SUPPORTED_PROVIDERS
        assert "gemini" in SUPPORTED_PROVIDERS

    def test_creates_openai_provider(self) -> None:
        settings = Settings(openai_api_key="test-key", ai_provider="openai")
        analyzer = get_clip_analyzer(settings)
        assert isinstance(analyzer, OpenAIClipAnalyzer)

    def test_creates_cursor_provider(self) -> None:
        settings = Settings(ai_provider="cursor")
        analyzer = get_clip_analyzer(settings)
        assert isinstance(analyzer, CursorManualClipAnalyzer)

    def test_creates_gemini_provider(self) -> None:
        settings = Settings(gemini_api_key="test-key", ai_provider="gemini")
        analyzer = get_clip_analyzer(settings)
        assert isinstance(analyzer, GeminiClipAnalyzer)

    def test_unknown_provider_raises(self) -> None:
        settings = Settings(ai_provider="anthropic")
        with pytest.raises(UnknownProviderError, match="anthropic"):
            get_clip_analyzer(settings)

    def test_ensure_openai_ready_requires_api_key(self) -> None:
        settings = Settings(openai_api_key="")
        with pytest.raises(LLMAnalysisError, match="OpenAI API key"):
            ensure_provider_ready("openai", settings)

    def test_ensure_gemini_ready_requires_api_key(self) -> None:
        settings = Settings(gemini_api_key="")
        with pytest.raises(LLMAnalysisError, match="Gemini API key"):
            ensure_provider_ready("gemini", settings)

    def test_ensure_gemini_ready_accepts_configured_key(self) -> None:
        settings = Settings(gemini_api_key="test-key")
        ensure_provider_ready("gemini", settings)
