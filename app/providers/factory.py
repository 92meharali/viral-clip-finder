"""Provider factory for the AI abstraction layer."""

from __future__ import annotations

from openai import OpenAI

from app.core.config import Settings, get_settings
from app.core.exceptions import LLMAnalysisError, UnknownProviderError
from app.providers.base import ClipAnalyzer
from app.providers.cursor_manual import CursorManualClipAnalyzer
from app.providers.gemini import GeminiClipAnalyzer
from app.providers.openai import OpenAIClipAnalyzer

SUPPORTED_PROVIDERS = frozenset({"cursor", "openai", "gemini"})


def ensure_provider_ready(provider: str, settings: Settings | None = None) -> None:
    """Validate that the requested provider can run with the current configuration.

    Raises:
        LLMAnalysisError: If required credentials or manual response files are missing.
    """
    resolved = settings or get_settings()
    provider_name = provider.strip().lower()

    if provider_name == "openai" and not resolved.openai_api_key:
        raise LLMAnalysisError(
            "OpenAI API key is not configured. Add OPENAI_API_KEY to your .env file and "
            "restart the API server."
        )

    if provider_name == "gemini" and not resolved.gemini_api_key:
        raise LLMAnalysisError(
            "Gemini API key is not configured. Add GEMINI_API_KEY to your .env file and "
            "restart the API server."
        )


def get_clip_analyzer(
    settings: Settings | None = None,
    *,
    provider: str | None = None,
    client: OpenAI | None = None,
    analysis_response_path: str | None = None,
    metadata_response_path: str | None = None,
    analysis_response_json: str | None = None,
) -> ClipAnalyzer:
    """Create a :class:`ClipAnalyzer` for the configured provider.

    Args:
        settings: Optional settings override.
        provider: Provider name override (``cursor``, ``openai``, or ``gemini``).
        client: Optional OpenAI client (``openai`` provider only).
        analysis_response_path: Path to manual analysis JSON (``cursor`` provider).
        metadata_response_path: Path to manual metadata JSON (``cursor`` provider).
        analysis_response_json: Inline analysis JSON (``cursor`` provider).

    Returns:
        Configured clip analyzer instance.

    Raises:
        UnknownProviderError: If the provider name is not supported.
    """
    resolved = settings or get_settings()
    provider_name = (provider or resolved.ai_provider).strip().lower()

    if provider_name not in SUPPORTED_PROVIDERS:
        supported = ", ".join(sorted(SUPPORTED_PROVIDERS))
        raise UnknownProviderError(
            f"Unknown AI provider '{provider_name}'. Supported providers: {supported}"
        )

    if provider_name == "cursor":
        return CursorManualClipAnalyzer(
            resolved,
            analysis_response_path=analysis_response_path or resolved.ai_analysis_response_path,
            metadata_response_path=metadata_response_path or resolved.ai_metadata_response_path,
            analysis_response_json=analysis_response_json,
        )

    if provider_name == "gemini":
        return GeminiClipAnalyzer(resolved)

    return OpenAIClipAnalyzer(resolved, client=client)
