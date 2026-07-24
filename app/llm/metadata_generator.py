"""LLM-powered clip metadata generation for social publishing."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from loguru import logger
from openai import OpenAI

from app.core.config import Settings, get_settings
from app.core.exceptions import LLMAnalysisError, MetadataGenerationError
from app.llm.client import create_openai_client
from app.llm.json_utils import parse_llm_json
from app.llm.transcript_formatter import format_clip_transcript
from app.models.clip import ViralClip
from app.models.metadata import ClipMetadata, ClipMetadataBase
from app.models.transcript import TranscriptSegment
from app.utils.prompt_loader import load_prompt


def _build_metadata_prompt(clip: ViralClip, clip_transcript: str) -> str:
    """Render the metadata generation prompt for a single clip."""
    return load_prompt(
        "metadata_generation",
        start=clip.start,
        end=clip.end,
        emotion=clip.emotion,
        viral_score=str(clip.viral_score),
        reason=clip.reason,
        summary=clip.summary,
        hook=clip.hook,
        clip_transcript=clip_transcript or "(no dialogue in clip window)",
    )


def _to_clip_metadata(
    response: ClipMetadataBase,
    *,
    index: int,
    clip: ViralClip,
) -> ClipMetadata:
    """Convert LLM response to a :class:`ClipMetadata` domain object."""
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


def save_metadata(metadata: ClipMetadata, output_dir: str | Path) -> ClipMetadata:
    """Export clip metadata to a JSON file.

    Args:
        metadata: Metadata to export.
        output_dir: Directory for ``clip{N}_metadata.json``.

    Returns:
        Updated metadata with ``json_path`` set.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"clip{metadata.index}_metadata.json"
    path.write_text(
        json.dumps(metadata.model_dump(exclude={"json_path"}), indent=2),
        encoding="utf-8",
    )
    logger.debug("Exported metadata to {}", path.name)
    return metadata.model_copy(update={"json_path": str(path.resolve())})


class MetadataGenerator:
    """Generate social media publishing metadata for viral clips."""

    def __init__(
        self,
        settings: Settings | None = None,
        client: OpenAI | None = None,
    ) -> None:
        """Initialize the metadata generator.

        Args:
            settings: Optional settings override.
            client: Optional pre-configured OpenAI client (for testing).
        """
        self.settings = settings or get_settings()
        self._client = client

    @property
    def client(self) -> OpenAI:
        """Lazy-initialize the OpenAI client."""
        if self._client is None:
            self._client = create_openai_client(self.settings)
        return self._client

    def generate_for_clip(
        self,
        clip: ViralClip,
        segments: list[TranscriptSegment],
        *,
        index: int = 1,
    ) -> ClipMetadata:
        """Generate publishing metadata for a single clip.

        Args:
            clip: Viral clip with timing and analysis fields.
            segments: Full parsed transcript segments.
            index: Clip number for export naming.

        Returns:
            Generated clip metadata.

        Raises:
            MetadataGenerationError: If generation fails.
        """
        clip_transcript = format_clip_transcript(
            segments,
            clip_start_seconds=clip.start_seconds,
            clip_end_seconds=clip.end_seconds,
        )
        system_prompt = _build_metadata_prompt(clip, clip_transcript)

        logger.info(
            "Generating metadata for clip {}-{} with model {}",
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

    def generate_batch(
        self,
        clips: Sequence[ViralClip],
        segments: list[TranscriptSegment],
        *,
        output_dir: str | Path | None = None,
    ) -> list[ClipMetadata]:
        """Generate metadata for multiple clips.

        Args:
            clips: Clips to generate metadata for.
            segments: Full parsed transcript.
            output_dir: If provided, export each clip's metadata as JSON.

        Returns:
            List of generated metadata objects.

        Raises:
            MetadataGenerationError: If clips are empty or generation fails.
        """
        if not clips:
            raise MetadataGenerationError("Cannot generate metadata for empty clip list")
        if not segments:
            raise MetadataGenerationError("Cannot generate metadata from empty transcript")

        results: list[ClipMetadata] = []
        for index, clip in enumerate(clips, start=1):
            metadata = self.generate_for_clip(clip, segments, index=index)
            if output_dir is not None:
                metadata = save_metadata(metadata, output_dir)
            results.append(metadata)

        logger.info("Generated metadata for {} clips", len(results))
        return results


def generate_metadata(
    clips: Sequence[ViralClip],
    segments: list[TranscriptSegment],
    *,
    output_dir: str | Path | None = None,
    settings: Settings | None = None,
    client: OpenAI | None = None,
) -> list[ClipMetadata]:
    """Convenience function to generate clip publishing metadata.

    Args:
        clips: Clips to generate metadata for.
        segments: Parsed transcript segments.
        output_dir: Optional directory to export JSON files.
        settings: Optional settings override.
        client: Optional OpenAI client override.

    Returns:
        Generated metadata for each clip.
    """
    return MetadataGenerator(settings=settings, client=client).generate_batch(
        clips,
        segments,
        output_dir=output_dir,
    )
