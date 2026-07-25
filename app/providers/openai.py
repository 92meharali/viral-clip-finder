"""OpenAI-backed clip analysis provider."""

from __future__ import annotations

from loguru import logger
from openai import OpenAI

from app.core.config import Settings
from app.core.exceptions import LLMAnalysisError, MetadataGenerationError
from app.llm.client import create_openai_client
from app.llm.json_utils import parse_llm_json
from app.llm.transcript_formatter import format_clip_transcript, format_transcript_for_llm
from app.models.clip import ViralClip
from app.models.metadata import ClipMetadata, ClipMetadataBase
from app.models.transcript import TranscriptSegment
from app.providers.base import ClipAnalyzer
from app.providers.response_parser import parse_clip_analysis_response
from app.utils.prompt_loader import load_prompt, load_prompt_schema


def _to_clip_metadata(
    response: ClipMetadataBase,
    *,
    index: int,
    clip: ViralClip,
) -> ClipMetadata:
    """Convert validated LLM metadata to a domain object."""
    return ClipMetadata(
        index=index,
        clip_start=clip.start,
        clip_end=clip.end,
        title=response.title.strip(),
        title_variations=response.title_variations,
        hook=response.hook.strip(),
        description=response.description.strip(),
        hashtags=response.hashtags,
        call_to_action=response.call_to_action.strip(),
        seo_keywords=response.seo_keywords,
    )


class OpenAIClipAnalyzer(ClipAnalyzer):
    """Analyze transcripts and generate metadata via the OpenAI API."""

    def __init__(
        self,
        settings: Settings | None = None,
        client: OpenAI | None = None,
    ) -> None:
        """Initialize the OpenAI provider.

        Args:
            settings: Optional settings override.
            client: Optional pre-configured OpenAI client (for testing).
        """
        super().__init__(settings)
        self._client = client

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def client(self) -> OpenAI:
        """Lazy-initialize the OpenAI client."""
        if self._client is None:
            self._client = create_openai_client(self.settings)
        return self._client

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
            "Analyzing {} segments with OpenAI model {}",
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

        clips = parse_clip_analysis_response(content)
        logger.info("OpenAI detected {} viral clips", len(clips))
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
            "Generating metadata for clip {}-{} with OpenAI model {}",
            clip.start,
            clip.end,
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
                        "content": "Generate publishing metadata for this clip as JSON only.",
                    },
                ],
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            logger.exception("OpenAI metadata API call failed")
            raise MetadataGenerationError(
                f"OpenAI API call failed: {exc}",
                model=self.settings.openai_model,
            ) from exc

        content = response.choices[0].message.content
        if not content:
            raise MetadataGenerationError(
                "OpenAI returned an empty response",
                model=self.settings.openai_model,
            )

        try:
            parsed = parse_llm_json(content, ClipMetadataBase)
        except LLMAnalysisError as exc:
            raise MetadataGenerationError(str(exc), model=self.settings.openai_model) from exc

        return _to_clip_metadata(parsed, index=index, clip=clip)
