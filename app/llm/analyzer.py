"""LLM-powered viral clip detection."""

from __future__ import annotations

import json
import re

from loguru import logger
from openai import OpenAI
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.exceptions import LLMAnalysisError
from app.llm.client import create_openai_client
from app.llm.transcript_formatter import format_transcript_for_llm
from app.models.clip import ClipAnalysisResponse, ViralClip, ViralClipBase
from app.models.transcript import TranscriptSegment
from app.utils.prompt_loader import load_prompt

_JSON_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_json_fences(text: str) -> str:
    """Remove markdown code fences from an LLM response if present."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = _JSON_FENCE_PATTERN.sub("", cleaned).strip()
    return cleaned


def _parse_llm_json(content: str) -> ClipAnalysisResponse:
    """Parse and validate raw LLM JSON output.

    Args:
        content: Raw response text from the LLM.

    Returns:
        Validated :class:`ClipAnalysisResponse`.

    Raises:
        LLMAnalysisError: If JSON is invalid or fails schema validation.
    """
    try:
        payload = json.loads(_strip_json_fences(content))
        return ClipAnalysisResponse.model_validate(payload)
    except json.JSONDecodeError as exc:
        logger.error("LLM returned invalid JSON: {}", content[:200])
        raise LLMAnalysisError("LLM returned invalid JSON") from exc
    except ValidationError as exc:
        logger.error("LLM JSON failed validation: {}", exc)
        raise LLMAnalysisError(f"LLM response failed validation: {exc}") from exc


def _build_system_prompt(settings: Settings, transcript_text: str) -> str:
    """Render the clip selection prompt with runtime configuration."""
    return load_prompt(
        "clip_selection",
        transcript=transcript_text,
        max_clips=str(settings.max_clips),
        min_duration=str(settings.min_clip_duration_seconds),
        max_duration=str(settings.max_clip_duration_seconds),
    )


def _to_viral_clips(raw_clips: list[ViralClipBase]) -> list[ViralClip]:
    """Convert validated LLM clip objects into domain ViralClip models."""
    clips: list[ViralClip] = []
    for raw in raw_clips:
        try:
            clips.append(ViralClip.from_base(raw))
        except ValueError as exc:
            logger.warning("Skipping invalid clip {}-{}: {}", raw.start, raw.end, exc)
    return clips


class ClipAnalyzer:
    """Analyze transcripts with an LLM to detect viral clip moments."""

    def __init__(
        self,
        settings: Settings | None = None,
        client: OpenAI | None = None,
    ) -> None:
        """Initialize the analyzer.

        Args:
            settings: Optional settings override.
            client: Optional pre-configured OpenAI client (useful for testing).
        """
        self.settings = settings or get_settings()
        self._client = client

    @property
    def client(self) -> OpenAI:
        """Lazy-initialize the OpenAI client."""
        if self._client is None:
            self._client = create_openai_client(self.settings)
        return self._client

    def analyze(self, segments: list[TranscriptSegment]) -> list[ViralClip]:
        """Detect viral clip moments from parsed transcript segments.

        Args:
            segments: Chronologically ordered transcript segments.

        Returns:
            List of detected viral clips, ordered by viral score descending.

        Raises:
            LLMAnalysisError: If segments are empty or the LLM call fails.
        """
        if not segments:
            raise LLMAnalysisError("Cannot analyze an empty transcript")

        transcript_text = format_transcript_for_llm(segments)
        system_prompt = _build_system_prompt(self.settings, transcript_text)

        logger.info(
            "Analyzing {} segments with model {}",
            len(segments),
            self.settings.openai_model,
        )

        try:
            response = self.client.chat.completions.create(
                model=self.settings.openai_model,
                temperature=self.settings.openai_temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            "Analyze the transcript above and return the viral clips "
                            "as JSON only."
                        ),
                    },
                ],
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            logger.exception("OpenAI API call failed")
            raise LLMAnalysisError(
                f"OpenAI API call failed: {exc}",
                model=self.settings.openai_model,
            ) from exc

        content = response.choices[0].message.content
        if not content:
            raise LLMAnalysisError(
                "OpenAI returned an empty response",
                model=self.settings.openai_model,
            )

        parsed = _parse_llm_json(content)
        clips = _to_viral_clips(parsed.clips)
        clips.sort(key=lambda clip: clip.viral_score, reverse=True)

        logger.info("Detected {} viral clips", len(clips))
        return clips


def analyze_transcript(
    segments: list[TranscriptSegment],
    *,
    settings: Settings | None = None,
    client: OpenAI | None = None,
) -> list[ViralClip]:
    """Convenience function to analyze transcript segments for viral clips.

    Args:
        segments: Parsed transcript segments.
        settings: Optional settings override.
        client: Optional OpenAI client override.

    Returns:
        Detected viral clips sorted by score.
    """
    return ClipAnalyzer(settings=settings, client=client).analyze(segments)
