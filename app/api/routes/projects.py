"""Project API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_project_repository
from app.schemas.projects import (
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectSummaryResponse,
)
from app.services.projects.repository import ProjectRepository, ProjectSummary

router = APIRouter(prefix="/projects", tags=["projects"])

ProjectRepoDep = Annotated[ProjectRepository, Depends(get_project_repository)]


def _summary_response(summary: ProjectSummary) -> ProjectSummaryResponse:
    return ProjectSummaryResponse(
        id=summary.id,
        video_id=summary.video_id,
        title=summary.title,
        channel=summary.channel,
        duration_seconds=summary.duration_seconds,
        webpage_url=summary.webpage_url,
        youtube_url=summary.youtube_url,
        clip_count=summary.clip_count,
        latest_job_status=summary.latest_job_status,
        created_at=summary.created_at,
        updated_at=summary.updated_at,
    )


@router.get("", response_model=ProjectListResponse, summary="List analysis projects")
def list_projects(
    repository: ProjectRepoDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ProjectListResponse:
    """Return recent persisted projects."""
    items, total = repository.list_projects(limit=limit, offset=offset)
    return ProjectListResponse(
        items=[_summary_response(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{project_id}", response_model=ProjectDetailResponse, summary="Get project detail")
def get_project(
    project_id: str,
    repository: ProjectRepoDep,
) -> ProjectDetailResponse:
    """Return project metadata and ranked clips."""
    summary = repository.get_project(project_id)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )

    clips = repository.get_project_clips(project_id)
    base = _summary_response(summary)
    return ProjectDetailResponse(
        **base.model_dump(),
        transcript_language=summary.transcript_language,
        transcript_source=summary.transcript_source,
        clips=clips,
    )
