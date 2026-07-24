"""Shared utilities for parsing LLM JSON responses."""

from __future__ import annotations

import json
import re
from typing import TypeVar

from loguru import logger
from pydantic import BaseModel, ValidationError

from app.core.exceptions import LLMAnalysisError

_JSON_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

T = TypeVar("T", bound=BaseModel)


def strip_json_fences(text: str) -> str:
    """Remove markdown code fences from an LLM response if present."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = _JSON_FENCE_PATTERN.sub("", cleaned).strip()
    return cleaned


def parse_llm_json(content: str, model: type[T]) -> T:
    """Parse and validate raw LLM JSON output against a Pydantic model.

    Args:
        content: Raw response text from the LLM.
        model: Pydantic model class to validate against.

    Returns:
        Validated model instance.

    Raises:
        LLMAnalysisError: If JSON is invalid or fails schema validation.
    """
    try:
        payload = json.loads(strip_json_fences(content))
        return model.model_validate(payload)
    except json.JSONDecodeError as exc:
        logger.error("LLM returned invalid JSON: {}", content[:200])
        raise LLMAnalysisError("LLM returned invalid JSON") from exc
    except ValidationError as exc:
        logger.error("LLM JSON failed validation: {}", exc)
        raise LLMAnalysisError(f"LLM response failed validation: {exc}") from exc
