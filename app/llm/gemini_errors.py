"""User-facing Gemini API error helpers."""

from __future__ import annotations

import re


_RETRY_DELAY_PATTERN = re.compile(r"retry in (\d+(?:\.\d+)?)s", re.IGNORECASE)
_ZERO_QUOTA_PATTERN = re.compile(r"limit:\s*0", re.IGNORECASE)


def is_gemini_rate_limit_error(exc: BaseException) -> bool:
    """Return True when the exception looks like a Gemini 429 rate-limit error."""
    message = str(exc)
    return "429" in message or "RESOURCE_EXHAUSTED" in message


def has_zero_free_tier_quota(exc: BaseException) -> bool:
    """Return True when Gemini reports free-tier quota limit is zero."""
    return _ZERO_QUOTA_PATTERN.search(str(exc)) is not None


def parse_retry_delay_seconds(exc: BaseException) -> float | None:
    """Extract Gemini's suggested retry delay from an error message."""
    match = _RETRY_DELAY_PATTERN.search(str(exc))
    if match is None:
        return None
    return float(match.group(1))


def format_gemini_error(exc: BaseException, *, model: str) -> str:
    """Convert a Gemini API exception into a concise, actionable message."""
    if not is_gemini_rate_limit_error(exc):
        return f"Gemini API call failed: {exc}"

    if has_zero_free_tier_quota(exc):
        return (
            f"Gemini free-tier quota is not available for model '{model}'. "
            "This usually means your API key has no free quota for that model. "
            "Create a key at https://aistudio.google.com/apikey (it should start with "
            "'AIza'), set GEMINI_MODEL=gemini-2.5-flash-lite in .env, restart the API, "
            "and try again. If it still fails, enable billing in Google AI Studio — "
            "free-tier usage still applies, but Google may require a billing account."
        )

    retry_delay = parse_retry_delay_seconds(exc)
    if retry_delay is not None:
        wait_seconds = max(5, int(retry_delay) + 1)
        return (
            f"Gemini rate limit reached for model '{model}'. "
            f"Wait about {wait_seconds} seconds and try again."
        )

    return (
        f"Gemini rate limit reached for model '{model}'. "
        "Wait a minute and try again, or switch to a lighter model in .env."
    )


def should_retry_gemini_error(exc: BaseException, *, attempt: int, max_attempts: int) -> bool:
    """Decide whether a failed Gemini call should be retried."""
    if attempt >= max_attempts:
        return False
    if not is_gemini_rate_limit_error(exc):
        return False
    if has_zero_free_tier_quota(exc):
        return False
    return parse_retry_delay_seconds(exc) is not None
