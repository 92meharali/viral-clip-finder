"""OpenAI client factory."""

from openai import OpenAI

from app.core.config import Settings, get_settings
from app.core.exceptions import LLMAnalysisError


def create_openai_client(settings: Settings | None = None) -> OpenAI:
    """Create an authenticated OpenAI client.

    Args:
        settings: Optional settings override. Uses cached settings by default.

    Returns:
        Configured OpenAI client instance.

    Raises:
        LLMAnalysisError: If the API key is not configured.
    """
    resolved = settings or get_settings()
    if not resolved.openai_api_key:
        raise LLMAnalysisError(
            "OpenAI API key is not configured. Set OPENAI_API_KEY in your .env file."
        )
    return OpenAI(api_key=resolved.openai_api_key)
