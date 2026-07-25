"""Intelligent reframe export for extracted clips."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from loguru import logger

from app.core.config import Settings, get_settings
from app.core.exceptions import VerticalCropError
from app.models.export import ExtractedClip, VerticalClip
from app.models.transcript import TranscriptSegment
from app.reframe.metrics.evaluation import evaluate_reframe
from app.reframe.pipeline.service import ReframePipelineService
from app.utils.clip_segments import segments_for_clip_window
from app.video.cropper import _build_vertical_output_path, _resolve_input
from app.video.filters import CROP_MODE_BLUR, CROP_MODE_CENTER
from app.video.ffmpeg import validate_source_video

REFRAME_CROP_MODE = "intelligent_reframe"


def _write_metrics(path: Path, metrics: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(metrics, "model_dump"):
        payload = metrics.model_dump()
    else:
        payload = metrics
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class ClipReframer:
    """Apply the intelligent reframe pipeline to extracted horizontal clips."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def reframe(
        self,
        clips: Sequence[str | Path | ExtractedClip],
        output_dir: str | Path | None = None,
        *,
        transcript_segments: list[TranscriptSegment] | None = None,
        metrics_dir: str | Path | None = None,
        blurred_background: bool = False,
    ) -> list[VerticalClip]:
        """Reframe extracted clips to vertical 9:16 output."""
        if not clips:
            raise VerticalCropError("Cannot reframe an empty clip list")

        out_dir = Path(output_dir or self.settings.output_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        metrics_root = Path(metrics_dir).resolve() if metrics_dir is not None else out_dir / "reframe"

        results: list[VerticalClip] = []
        output_index = 0
        pipeline = ReframePipelineService(self.settings)

        try:
            for clip in clips:
                source, clip_index = _resolve_input(clip)
                try:
                    validate_source_video(source)
                except Exception as exc:
                    raise VerticalCropError(str(exc), source_path=str(source)) from exc

                output_index += 1
                output_path = _build_vertical_output_path(out_dir, output_index)
                clip_segments = transcript_segments or []
                if isinstance(clip, ExtractedClip):
                    clip_segments = segments_for_clip_window(
                        clip_segments,
                        clip_start_seconds=clip.start_seconds,
                        clip_end_seconds=clip.end_seconds,
                        relative_to_clip=True,
                    )
                    duration_seconds = clip.duration_seconds
                else:
                    duration_seconds = None

                logger.info("Reframing clip {} with intelligent pipeline → {}", clip_index, output_path.name)
                pipeline_result = pipeline.process_video(
                    source,
                    transcript_segments=clip_segments or None,
                )
                pipeline.render_service.render(
                    source,
                    pipeline_result.crop_plan,
                    output_path,
                    duration_seconds=duration_seconds,
                    blurred_background=blurred_background,
                )
                metrics = evaluate_reframe(
                    tracking=pipeline_result.tracking,
                    crop_plan=pipeline_result.crop_plan,
                    camera_path=pipeline_result.smoothed_path,
                )
                _write_metrics(metrics_root / f"clip{output_index}_metrics.json", metrics)

                results.append(
                    VerticalClip(
                        index=output_index,
                        source_path=str(source),
                        output_path=str(output_path),
                        width=self.settings.vertical_width,
                        height=self.settings.vertical_height,
                        blurred_background=blurred_background,
                        crop_mode=REFRAME_CROP_MODE,
                    )
                )
        finally:
            pipeline.close()

        logger.info("Reframed {} clips with intelligent pipeline", len(results))
        return results


def reframe_to_vertical(
    clips: Sequence[str | Path | ExtractedClip],
    output_dir: str | Path | None = None,
    *,
    transcript_segments: list[TranscriptSegment] | None = None,
    metrics_dir: str | Path | None = None,
    blurred_background: bool = False,
    settings: Settings | None = None,
) -> list[VerticalClip]:
    """Convenience function to reframe clips to vertical using the AI pipeline."""
    return ClipReframer(settings=settings).reframe(
        clips,
        output_dir,
        transcript_segments=transcript_segments,
        metrics_dir=metrics_dir,
        blurred_background=blurred_background,
    )
