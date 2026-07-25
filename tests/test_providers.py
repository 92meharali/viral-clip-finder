"""Tests for AI provider factory."""

import pytest

from app.core.config import Settings
from app.core.exceptions import UnknownProviderError
from app.providers.cursor_manual import CursorManualClipAnalyzer
from app.providers.factory import SUPPORTED_PROVIDERS, get_clip_analyzer
from app.providers.openai import OpenAIClipAnalyzer


class TestProviderFactory:
    def test_supported_providers(self) -> None:
        assert "cursor" in SUPPORTED_PROVIDERS
        assert "openai" in SUPPORTED_PROVIDERS

    def test_creates_openai_provider(self) -> None:
        settings = Settings(openai_api_key="test-key", ai_provider="openai")
        analyzer = get_clip_analyzer(settings)
        assert isinstance(analyzer, OpenAIClipAnalyzer)

    def test_creates_cursor_provider(self) -> None:
        settings = Settings(ai_provider="cursor")
        analyzer = get_clip_analyzer(settings)
        assert isinstance(analyzer, CursorManualClipAnalyzer)

    def test_unknown_provider_raises(self) -> None:
        settings = Settings(ai_provider="gemini")
        with pytest.raises(UnknownProviderError, match="gemini"):
            get_clip_analyzer(settings)
