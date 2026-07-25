"""Project and clip query schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.analyze import ClipSummaryResponse


class ProjectSummaryResponse(BaseModel):
    """Summary row for a persisted project."""

    id: str
    video_id: str
    title: str
    channel: str | None
    duration_seconds: float
    webpage_url: str
    youtube_url: str
    clip_count: int = Field(..., ge=0)
    latest_job_status: str | None = None
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    """Paginated project list."""

    items: list[ProjectSummaryResponse]
    total: int = Field(..., ge=0)
    limit: int = Field(..., ge=1)
    offset: int = Field(..., ge=0)


class ProjectDetailResponse(ProjectSummaryResponse):
    """Full project detail including ranked clips."""

    transcript_language: str | None = None
    transcript_source: str | None = None
    clips: list[ClipSummaryResponse] = Field(default_factory=list)


class ClipListResponse(BaseModel):
    """Filtered clip list."""

    items: list[ClipSummaryResponse]
    total: int = Field(..., ge=0)
    limit: int = Field(..., ge=1)
    offset: int = Field(..., ge=0)
