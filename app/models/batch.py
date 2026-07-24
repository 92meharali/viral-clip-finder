"""Batch export result models."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.models.metadata import ClipMetadata
from app.models.quality import ClipQualityResult


class ExportedClipBundle(BaseModel):
    """All export artifacts for a single clip."""

    index: int = Field(..., ge=1, description="1-based exported clip number")
    clip_start: str = Field(..., description="Clip start timestamp")
    clip_end: str = Field(..., description="Clip end timestamp")
    viral_score: float = Field(..., ge=0, description="LLM viral score")
    emotion: str = Field(..., description="Primary emotion")
    rank_score: float | None = Field(default=None, description="Composite rank score if available")
    video_path: str | None = Field(default=None, description="Horizontal cut video path")
    vertical_path: str | None = Field(default=None, description="Vertical video path")
    subtitled_path: str | None = Field(default=None, description="Video with burned subtitles")
    srt_path: str | None = Field(default=None, description="SRT subtitle file path")
    metadata_path: str | None = Field(default=None, description="Metadata JSON path")
    title: str | None = Field(default=None, description="Primary title")
    hook: str | None = Field(default=None, description="Social media hook")
    hashtags: list[str] = Field(default_factory=list, description="Suggested hashtags")

    model_config = {"frozen": True}


class BatchExportManifest(BaseModel):
    """Full batch export manifest written to ``manifest.json``."""

    source_video: str = Field(..., description="Path to the source video")
    transcript_source: str = Field(..., description="Path or label for the transcript input")
    output_dir: str = Field(..., description="Export output directory")
    clips_analyzed: int = Field(..., ge=0, description="Clips detected by LLM")
    clips_ranked: int = Field(..., ge=0, description="Clips after ranking")
    clips_exported: int = Field(..., ge=0, description="Clips successfully exported")
    clips_rejected_quality: int = Field(..., ge=0, description="Clips rejected by quality checks")
    quality_rejections: list[ClipQualityResult] = Field(default_factory=list)
    clips: list[ExportedClipBundle] = Field(default_factory=list)
    manifest_path: str | None = Field(default=None, description="Path to this manifest file")
    created_at: str = Field(
        default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        description="UTC export timestamp",
    )

    model_config = {"frozen": True}


class BatchExportResult(BaseModel):
    """Result returned by the batch exporter."""

    manifest: BatchExportManifest
    metadata: list[ClipMetadata]

    model_config = {"frozen": True}
