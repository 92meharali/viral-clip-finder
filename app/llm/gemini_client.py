"""Google Gemini client factory."""

from google import genai

from app.core.config import Settings, get_settings
from app.core.exceptions import LLMAnalysisError


def create_gemini_client(settings: Settings | None = None) -> genai.Client:
    """Create an authenticated Gemini client.

    Args:
        settings: Optional settings override. Uses cached settings by default.

    Returns:
        Configured Gemini client instance.

    Raises:
        LLMAnalysisError: If the API key is not configured.
    """
    resolved = settings or get_settings()
    if not resolved.gemini_api_key:
        raise LLMAnalysisError(
            "Gemini API key is not configured. Set GEMINI_API_KEY in your .env file."
        )
    return genai.Client(api_key=resolved.gemini_api_key)
