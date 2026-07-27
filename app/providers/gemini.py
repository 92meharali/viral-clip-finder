"""Google Gemini-backed clip analysis provider."""

from __future__ import annotations

import time

from google import genai
from google.genai import types
from loguru import logger

from app.core.config import Settings
from app.core.exceptions import LLMAnalysisError, MetadataGenerationError
from app.llm.gemini_client import create_gemini_client
from app.llm.gemini_errors import (
    format_gemini_error,
    parse_retry_delay_seconds,
    should_retry_gemini_error,
)
from app.llm.json_utils import parse_llm_json
from app.llm.transcript_formatter import format_clip_transcript, format_transcript_for_llm
from app.models.clip import ViralClip
from app.models.metadata import ClipMetadata, ClipMetadataBase
from app.models.transcript import TranscriptSegment
from app.providers.base import ClipAnalyzer
from app.providers.openai import _to_clip_metadata
from app.providers.response_parser import parse_clip_analysis_response
from app.utils.prompt_loader import load_prompt, load_prompt_schema


class GeminiClipAnalyzer(ClipAnalyzer):
    """Analyze transcripts and generate metadata via the Google Gemini API."""

    def __init__(
        self,
        settings: Settings | None = None,
        client: genai.Client | None = None,
    ) -> None:
        super().__init__(settings)
        self._client = client

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def client(self) -> genai.Client:
        """Lazy-initialize the Gemini client."""
        if self._client is None:
            self._client = create_gemini_client(self.settings)
        return self._client

    def _generate_json(self, *, system_prompt: str, user_prompt: str) -> str:
        max_attempts = self.settings.gemini_max_retries + 1
        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.settings.gemini_model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=self.settings.gemini_temperature,
                        response_mime_type="application/json",
                    ),
                )
            except Exception as exc:
                last_error = exc
                if should_retry_gemini_error(
                    exc,
                    attempt=attempt,
                    max_attempts=max_attempts,
                ):
                    wait_seconds = max(
                        5,
                        int(parse_retry_delay_seconds(exc) or 30) + 1,
                    )
                    logger.warning(
                        "Gemini rate limited on attempt {}/{}; retrying in {}s",
                        attempt,
                        max_attempts,
                        wait_seconds,
                    )
                    time.sleep(wait_seconds)
                    continue

                logger.exception("Gemini API call failed")
                raise LLMAnalysisError(
                    format_gemini_error(exc, model=self.settings.gemini_model),
                    model=self.settings.gemini_model,
                ) from exc

            content = response.text
            if not content:
                raise LLMAnalysisError(
                    "Gemini returned an empty response",
                    model=self.settings.gemini_model,
                )
            return content

        assert last_error is not None
        raise LLMAnalysisError(
            format_gemini_error(last_error, model=self.settings.gemini_model),
            model=self.settings.gemini_model,
        ) from last_error

    def analyze_transcript(self, segments: list[TranscriptSegment]) -> list[ViralClip]:
        if not segments:
            raise LLMAnalysisError("Cannot analyze an empty transcript")

        transcript_text = format_transcript_for_llm(segments)
        system_prompt = load_prompt(
            "clip_analysis",
            transcript=transcript_text,
            max_clips=str(self.settings.max_clips),
            min_duration=str(self.settings.min_clip_duration_seconds),
            max_duration=str(self.settings.max_clip_duration_seconds),
            json_schema=load_prompt_schema("clip_analysis"),
        )

        logger.info(
            "Analyzing {} segments with Gemini model {}",
            len(segments),
            self.settings.gemini_model,
        )

        content = self._generate_json(
            system_prompt=system_prompt,
            user_prompt=(
                "Analyze the transcript above and return the viral clips as JSON only."
            ),
        )

        clips = parse_clip_analysis_response(content)
        logger.info("Gemini detected {} viral clips", len(clips))
        return clips

    def generate_metadata(
        self,
        clip: ViralClip,
        segments: list[TranscriptSegment],
        *,
        index: int = 1,
    ) -> ClipMetadata:
        clip_transcript = format_clip_transcript(
            segments,
            clip_start_seconds=clip.start_seconds,
            clip_end_seconds=clip.end_seconds,
        )
        system_prompt = load_prompt(
            "metadata",
            start=clip.start,
            end=clip.end,
            emotion=clip.emotion,
            viral_score=str(clip.viral_score),
            reason=clip.reason,
            summary=clip.summary,
            hook=clip.hook,
            clip_transcript=clip_transcript or "(no dialogue in clip window)",
            json_schema=load_prompt_schema("metadata"),
        )

        logger.info(
            "Generating metadata for clip {}-{} with Gemini model {}",
            clip.start,
            clip.end,
            self.settings.gemini_model,
        )

        try:
            content = self._generate_json(
                system_prompt=system_prompt,
                user_prompt="Generate publishing metadata for this clip as JSON only.",
            )
        except LLMAnalysisError as exc:
            raise MetadataGenerationError(str(exc), model=self.settings.gemini_model) from exc

        try:
            parsed = parse_llm_json(content, ClipMetadataBase)
        except LLMAnalysisError as exc:
            raise MetadataGenerationError(str(exc), model=self.settings.gemini_model) from exc

        return _to_clip_metadata(parsed, index=index, clip=clip)
