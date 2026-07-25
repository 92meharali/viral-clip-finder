"""Parse and validate AI clip analysis JSON responses."""

from __future__ import annotations

import json
from typing import Any

from loguru import logger
from pydantic import TypeAdapter, ValidationError

from app.core.exceptions import LLMAnalysisError
from app.llm.json_utils import strip_json_fences
from app.models.clip import ClipAnalysisResponse, ViralClip, ViralClipBase

_CLIP_LIST_ADAPTER = TypeAdapter(list[ViralClipBase])


def _normalize_payload(payload: Any) -> list[dict[str, Any]]:
    """Normalize supported JSON shapes into a list of clip dicts."""
    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        if "clips" in payload:
            clips = payload["clips"]
            if not isinstance(clips, list):
                raise LLMAnalysisError("Expected 'clips' to be a JSON array")
            return clips

        if {"start", "end"} <= payload.keys():
            return [payload]

    raise LLMAnalysisError(
        "Expected clip analysis JSON as an array or an object with a 'clips' array"
    )


def parse_clip_analysis_response(content: str) -> list[ViralClip]:
    """Parse and validate clip analysis JSON from any supported provider format.

    Supported formats:
    - ``[{"start": "...", "end": "...", "score": 9.8, ...}]``
    - ``{"clips": [{...}]}``

    Field aliases:
    - ``score`` is accepted as an alias for ``viral_score``
    - ``summary`` defaults to ``reason`` when omitted

    Args:
        content: Raw JSON text (markdown fences are stripped automatically).

    Returns:
        Validated :class:`ViralClip` objects sorted by viral score descending.

    Raises:
        LLMAnalysisError: If JSON is malformed or fails schema validation.
    """
    try:
        payload = json.loads(strip_json_fences(content))
    except json.JSONDecodeError as exc:
        logger.error("Invalid clip analysis JSON: {}", content[:200])
        raise LLMAnalysisError(
            f"Invalid JSON: {exc.msg} at line {exc.lineno}, column {exc.colno}"
        ) from exc

    try:
        clip_dicts = _normalize_payload(payload)
        if not clip_dicts:
            return []

        if isinstance(payload, dict) and "clips" in payload:
            validated = ClipAnalysisResponse.model_validate(payload).clips
        else:
            validated = _CLIP_LIST_ADAPTER.validate_python(clip_dicts)
    except ValidationError as exc:
        logger.error("Clip analysis JSON failed validation: {}", exc)
        raise LLMAnalysisError(f"Clip analysis response failed validation:\n{exc}") from exc
    except LLMAnalysisError:
        raise
    except Exception as exc:
        raise LLMAnalysisError(f"Could not parse clip analysis response: {exc}") from exc

    clips: list[ViralClip] = []
    for raw in validated:
        try:
            clips.append(ViralClip.from_base(raw))
        except ValueError as exc:
            logger.warning("Skipping invalid clip {}-{}: {}", raw.start, raw.end, exc)

    clips.sort(key=lambda clip: clip.viral_score, reverse=True)
    return clips
