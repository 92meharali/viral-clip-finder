"""Manual Cursor provider — zero external API calls."""

from __future__ import annotations

import json
from pathlib import Path

from loguru import logger

from app.core.config import Settings
from app.core.exceptions import LLMAnalysisError, ManualAnalysisRequiredError, MetadataGenerationError
from app.llm.json_utils import parse_llm_json
from app.llm.transcript_formatter import format_clip_transcript, format_transcript_for_llm
from app.models.clip import ViralClip
from app.models.metadata import ClipMetadata, ClipMetadataBase
from app.models.transcript import TranscriptSegment
from app.providers.base import ClipAnalyzer
from app.providers.openai import _to_clip_metadata
from app.providers.response_parser import parse_clip_analysis_response
from app.utils.prompt_loader import load_prompt, load_prompt_schema


class CursorManualClipAnalyzer(ClipAnalyzer):
    """Provider that exports prompts for manual use in Cursor and imports JSON responses.

    Workflow:
    1. Call :meth:`export_analysis_prompt` to generate a formatted prompt.
    2. Paste the prompt into Cursor and run the analysis.
    3. Paste the JSON response back via :meth:`import_analysis_response` or a response file.
    4. Call :meth:`analyze_transcript` to validate and continue the pipeline.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        analysis_response_path: str | Path | None = None,
        metadata_response_path: str | Path | None = None,
        analysis_response_json: str | None = None,
    ) -> None:
        """Initialize the Cursor manual provider.

        Args:
            settings: Optional settings override.
            analysis_response_path: File containing clip analysis JSON.
            metadata_response_path: File containing metadata JSON (object or array).
            analysis_response_json: Inline analysis JSON (overrides file when set).
        """
        super().__init__(settings)
        self.analysis_response_path = (
            Path(analysis_response_path) if analysis_response_path is not None else None
        )
        self.metadata_response_path = (
            Path(metadata_response_path) if metadata_response_path is not None else None
        )
        self._analysis_response_json = analysis_response_json
        self._metadata_cache: dict[int, ClipMetadataBase] | None = None

    @property
    def provider_name(self) -> str:
        return "cursor"

    def export_analysis_prompt(self, segments: list[TranscriptSegment]) -> str:
        """Build a complete prompt for manual analysis in Cursor.

        Args:
            segments: Parsed transcript segments.

        Returns:
            Rendered prompt including transcript, instructions, and JSON schema.
        """
        if not segments:
            raise LLMAnalysisError("Cannot export prompt for an empty transcript")

        transcript_text = format_transcript_for_llm(segments)
        schema = load_prompt_schema("clip_analysis")
        return load_prompt(
            "clip_analysis",
            transcript=transcript_text,
            max_clips=str(self.settings.max_clips),
            min_duration=str(self.settings.min_clip_duration_seconds),
            max_duration=str(self.settings.max_clip_duration_seconds),
            json_schema=schema,
        )

    def write_analysis_prompt(
        self,
        segments: list[TranscriptSegment],
        output_path: str | Path,
    ) -> Path:
        """Export the analysis prompt to a file for use in Cursor."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        prompt = self.export_analysis_prompt(segments)
        path.write_text(prompt, encoding="utf-8")
        logger.info("Wrote analysis prompt to {}", path)
        return path

    def import_analysis_response(self, content: str) -> list[ViralClip]:
        """Validate and parse a manual clip analysis JSON response.

        Args:
            content: Raw JSON from Cursor.

        Returns:
            Validated viral clips.

        Raises:
            LLMAnalysisError: If validation fails.
        """
        clips = parse_clip_analysis_response(content)
        logger.info("Imported {} clips from manual Cursor response", len(clips))
        return clips

    def _load_analysis_response_text(self) -> str | None:
        """Load analysis JSON from inline value or configured file."""
        if self._analysis_response_json is not None:
            return self._analysis_response_json

        path = self.analysis_response_path
        if path is not None and path.exists():
            return path.read_text(encoding="utf-8")

        return None

    def analyze_transcript(self, segments: list[TranscriptSegment]) -> list[ViralClip]:
        if not segments:
            raise LLMAnalysisError("Cannot analyze an empty transcript")

        response_text = self._load_analysis_response_text()
        if response_text is None:
            default_prompt_path = Path(self.settings.output_dir) / "analysis_prompt.md"
            self.write_analysis_prompt(segments, default_prompt_path)
            raise ManualAnalysisRequiredError(
                "No clip analysis response found. A prompt was written to "
                f"{default_prompt_path.resolve()}. Paste it into Cursor, then save the "
                "JSON response and re-run with --analysis-response or set "
                "AI_ANALYSIS_RESPONSE_PATH.",
                prompt_path=str(default_prompt_path.resolve()),
            )

        clips = self.import_analysis_response(response_text)
        if not clips:
            raise LLMAnalysisError("Manual analysis response contained no valid clips")
        return clips

    def export_metadata_prompt(
        self,
        clip: ViralClip,
        segments: list[TranscriptSegment],
    ) -> str:
        """Build a metadata prompt for a single clip."""
        clip_transcript = format_clip_transcript(
            segments,
            clip_start_seconds=clip.start_seconds,
            clip_end_seconds=clip.end_seconds,
        )
        schema = load_prompt_schema("metadata")
        return load_prompt(
            "metadata",
            start=clip.start,
            end=clip.end,
            emotion=clip.emotion,
            viral_score=str(clip.viral_score),
            reason=clip.reason,
            summary=clip.summary,
            hook=clip.hook,
            clip_transcript=clip_transcript or "(no dialogue in clip window)",
            json_schema=schema,
        )

    def import_metadata_response(self, content: str) -> dict[int, ClipMetadataBase]:
        """Parse metadata JSON keyed by clip index.

        Accepts:
        - A single metadata object (index 1)
        - An array of metadata objects (1-based order)
        - An object mapping index strings to metadata objects
        """
        try:
            payload = json.loads(content.strip())
        except json.JSONDecodeError as exc:
            raise MetadataGenerationError(
                f"Invalid metadata JSON: {exc.msg} at line {exc.lineno}, column {exc.colno}"
            ) from exc

        results: dict[int, ClipMetadataBase] = {}

        if isinstance(payload, dict) and "title" in payload:
            results[1] = ClipMetadataBase.model_validate(payload)
            return results

        if isinstance(payload, list):
            for index, item in enumerate(payload, start=1):
                results[index] = ClipMetadataBase.model_validate(item)
            return results

        if isinstance(payload, dict):
            for key, item in payload.items():
                results[int(key)] = ClipMetadataBase.model_validate(item)
            return results

        raise MetadataGenerationError(
            "Expected metadata JSON as an object, array, or index-keyed object"
        )

    def _load_metadata_cache(self) -> dict[int, ClipMetadataBase]:
        if self._metadata_cache is not None:
            return self._metadata_cache

        path = self.metadata_response_path
        if path is None or not path.exists():
            return {}

        self._metadata_cache = self.import_metadata_response(path.read_text(encoding="utf-8"))
        return self._metadata_cache

    def generate_metadata(
        self,
        clip: ViralClip,
        segments: list[TranscriptSegment],
        *,
        index: int = 1,
    ) -> ClipMetadata:
        metadata_map = self._load_metadata_cache()
        if index not in metadata_map:
            default_prompt_path = Path(self.settings.output_dir) / f"metadata_prompt_clip{index}.md"
            default_prompt_path.parent.mkdir(parents=True, exist_ok=True)
            default_prompt_path.write_text(
                self.export_metadata_prompt(clip, segments),
                encoding="utf-8",
            )
            raise MetadataGenerationError(
                f"No metadata found for clip {index}. A prompt was written to "
                f"{default_prompt_path.resolve()}. Paste the JSON response into "
                f"{self.metadata_response_path or 'metadata_response.json'} and re-run.",
                model=self.provider_name,
            )

        return _to_clip_metadata(metadata_map[index], index=index, clip=clip)
