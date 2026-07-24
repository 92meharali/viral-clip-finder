"""End-to-end batch export pipeline."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from loguru import logger
from openai import OpenAI
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.core.exceptions import BatchExportError
from app.llm.analyzer import analyze_transcript
from app.llm.metadata_generator import generate_metadata
from app.models.batch import BatchExportManifest, BatchExportResult, ExportedClipBundle
from app.models.clip import RankedClip, ViralClip
from app.models.export import ExtractedClip, VerticalClip
from app.models.metadata import ClipMetadata
from app.models.quality import QualityFilterResult
from app.models.subtitle import SubtitleFile
from app.models.transcript import TranscriptSegment
from app.services.clip_ranker import rank_clips
from app.services.quality_checker import filter_quality_clips
from app.services.transcript_parser import parse_transcript, parse_transcript_file
from app.video.cropper import crop_to_vertical
from app.video.cutter import cut_clips
from app.video.subtitle_burner import SubtitleBurner
from app.video.subtitles import generate_subtitles


class BatchExportOptions(BaseModel):
    """Configuration options for a batch export run."""

    top_n: int | None = Field(default=None, description="Max clips to rank and export")
    blurred_background: bool = Field(default=False, description="Use blurred background cropping")
    burn_subtitles: bool = Field(default=False, description="Burn subtitles into vertical videos")
    include_speaker_in_subtitles: bool = Field(default=True, description="Include speaker in SRT")
    skip_video_processing: bool = Field(
        default=False,
        description="Skip FFmpeg steps (for testing)",
    )


@dataclass(frozen=True)
class _VideoArtifacts:
    """Intermediate video processing results."""

    extracted: list[ExtractedClip]
    vertical: list[VerticalClip]
    subtitles: list[SubtitleFile]


def _rank_score(clip: ViralClip) -> float | None:
    """Extract rank score when the clip is a :class:`RankedClip`."""
    if isinstance(clip, RankedClip):
        return clip.rank_score
    return None


def _metadata_by_index(metadata_list: list[ClipMetadata]) -> dict[int, ClipMetadata]:
    """Index metadata objects by clip number."""
    return {item.index: item for item in metadata_list}


def _build_clip_bundle(
    *,
    index: int,
    clip: ViralClip,
    extracted: ExtractedClip | None,
    vertical: VerticalClip | None,
    subtitle: SubtitleFile | None,
    metadata: ClipMetadata | None,
) -> ExportedClipBundle:
    """Assemble a single exported clip bundle."""
    return ExportedClipBundle(
        index=index,
        clip_start=clip.start,
        clip_end=clip.end,
        viral_score=clip.viral_score,
        emotion=clip.emotion,
        rank_score=_rank_score(clip),
        video_path=extracted.output_path if extracted else None,
        vertical_path=vertical.output_path if vertical else None,
        subtitled_path=subtitle.burned_output_path if subtitle else None,
        srt_path=subtitle.srt_path if subtitle else None,
        metadata_path=metadata.json_path if metadata else None,
        title=metadata.title if metadata else None,
        hook=metadata.hook if metadata else None,
        hashtags=list(metadata.hashtags) if metadata else [],
    )


def save_manifest(manifest: BatchExportManifest, output_dir: str | Path) -> BatchExportManifest:
    """Write the batch manifest to ``manifest.json`` in the output directory."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "manifest.json"
    payload = manifest.model_dump()
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info("Wrote batch manifest to {}", path)
    return manifest.model_copy(update={"manifest_path": str(path.resolve())})


class BatchExporter:
    """Orchestrate the full viral reel export pipeline."""

    def __init__(
        self,
        settings: Settings | None = None,
        client: OpenAI | None = None,
    ) -> None:
        """Initialize the batch exporter.

        Args:
            settings: Optional settings override.
            client: Optional OpenAI client for LLM steps.
        """
        self.settings = settings or get_settings()
        self._client = client

    def export(
        self,
        video_path: str | Path,
        transcript_path: str | Path,
        output_dir: str | Path | None = None,
        *,
        options: BatchExportOptions | None = None,
        segments: list[TranscriptSegment] | None = None,
    ) -> BatchExportResult:
        """Run the full batch export pipeline.

        Pipeline: parse → analyze → rank → quality filter → cut → crop →
        subtitles → metadata → manifest JSON.

        Args:
            video_path: Source video file (MP4, MOV, or MKV).
            transcript_path: Transcript text file.
            output_dir: Export directory. Defaults to ``settings.output_dir``.
            options: Batch export configuration.
            segments: Pre-parsed segments (skips transcript file parsing).

        Returns:
            :class:`BatchExportResult` with manifest and metadata.

        Raises:
            BatchExportError: If a pipeline step fails or nothing is exported.
        """
        opts = options or BatchExportOptions()
        out_dir = Path(output_dir or self.settings.output_dir).resolve()
        video = Path(video_path).resolve()
        transcript = Path(transcript_path).resolve()
        top_n = opts.top_n if opts.top_n is not None else self.settings.max_clips

        if not video.exists():
            raise BatchExportError(f"Source video not found: {video}")
        if segments is None and not transcript.exists():
            raise BatchExportError(f"Transcript file not found: {transcript}")

        out_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Starting batch export: {} + {} → {}", video.name, transcript.name, out_dir)

        parsed_segments = segments or parse_transcript_file(str(transcript))
        analyzed = analyze_transcript(
            parsed_segments,
            settings=self.settings,
            client=self._client,
        )
        if not analyzed:
            raise BatchExportError("LLM analysis returned no clips")

        ranked = rank_clips(analyzed, parsed_segments, top_n=top_n, settings=self.settings)
        passed, quality_report = filter_quality_clips(
            ranked, parsed_segments, settings=self.settings
        )

        if not passed:
            raise BatchExportError(
                f"No clips passed quality checks ({len(quality_report.rejected)} rejected)",
            )

        artifacts = self._process_videos(
            video,
            passed,
            out_dir,
            parsed_segments,
            opts=opts,
        )
        metadata_list = generate_metadata(
            passed,
            parsed_segments,
            output_dir=out_dir,
            settings=self.settings,
            client=self._client,
        )

        bundles = self._assemble_bundles(passed, artifacts, metadata_list)
        manifest = save_manifest(
            BatchExportManifest(
                source_video=str(video),
                transcript_source=str(transcript),
                output_dir=str(out_dir),
                clips_analyzed=len(analyzed),
                clips_ranked=len(ranked),
                clips_exported=len(bundles),
                clips_rejected_quality=len(quality_report.rejected),
                quality_rejections=quality_report.rejected,
                clips=bundles,
            ),
            out_dir,
        )

        logger.info("Batch export complete: {} clips → {}", len(bundles), out_dir)
        return BatchExportResult(manifest=manifest, metadata=metadata_list)

    def export_from_text(
        self,
        video_path: str | Path,
        transcript_text: str,
        output_dir: str | Path | None = None,
        *,
        options: BatchExportOptions | None = None,
    ) -> BatchExportResult:
        """Run batch export from raw transcript text instead of a file."""
        segments = parse_transcript(transcript_text)
        return self.export(
            video_path,
            transcript_path="<inline>",
            output_dir=output_dir,
            options=options,
            segments=segments,
        )

    def _process_videos(
        self,
        video: Path,
        clips: Sequence[ViralClip],
        out_dir: Path,
        segments: list[TranscriptSegment],
        *,
        opts: BatchExportOptions,
    ) -> _VideoArtifacts:
        """Cut, crop, and subtitle videos unless skipped for testing."""
        if opts.skip_video_processing:
            logger.info("Skipping video processing (test mode)")
            return _VideoArtifacts(extracted=[], vertical=[], subtitles=[])

        extracted = cut_clips(video, clips, output_dir=out_dir, settings=self.settings)
        vertical = crop_to_vertical(
            extracted,
            output_dir=out_dir,
            blurred_background=opts.blurred_background,
            settings=self.settings,
        )
        subtitles = generate_subtitles(
            segments,
            extracted,
            output_dir=out_dir,
            settings=self.settings,
            include_speaker=opts.include_speaker_in_subtitles,
        )

        if opts.burn_subtitles:
            video_map: dict[int, str | Path] = {
                item.index: Path(item.output_path) for item in vertical
            }
            subtitles = SubtitleBurner(settings=self.settings).burn_for_subtitle_files(
                video_map,
                subtitles,
            )

        return _VideoArtifacts(extracted=extracted, vertical=vertical, subtitles=subtitles)

    def _assemble_bundles(
        self,
        clips: Sequence[ViralClip],
        artifacts: _VideoArtifacts,
        metadata_list: list[ClipMetadata],
    ) -> list[ExportedClipBundle]:
        """Combine clip, video, and metadata artifacts into export bundles."""
        extracted_map = {item.index: item for item in artifacts.extracted}
        vertical_map = {item.index: item for item in artifacts.vertical}
        subtitle_map = {item.index: item for item in artifacts.subtitles}
        metadata_map = _metadata_by_index(metadata_list)

        bundles: list[ExportedClipBundle] = []
        for index, clip in enumerate(clips, start=1):
            bundles.append(
                _build_clip_bundle(
                    index=index,
                    clip=clip,
                    extracted=extracted_map.get(index),
                    vertical=vertical_map.get(index),
                    subtitle=subtitle_map.get(index),
                    metadata=metadata_map.get(index),
                )
            )
        return bundles


def run_batch_export(
    video_path: str | Path,
    transcript_path: str | Path,
    output_dir: str | Path | None = None,
    *,
    settings: Settings | None = None,
    client: OpenAI | None = None,
    options: BatchExportOptions | None = None,
) -> BatchExportResult:
    """Convenience function to run a full batch export."""
    return BatchExporter(settings=settings, client=client).export(
        video_path,
        transcript_path,
        output_dir,
        options=options,
    )
