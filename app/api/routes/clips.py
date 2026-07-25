"""Clip API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_project_repository
from app.schemas.projects import ClipListResponse
from app.services.projects.repository import ProjectRepository

router = APIRouter(prefix="/clips", tags=["clips"])

ProjectRepoDep = Annotated[ProjectRepository, Depends(get_project_repository)]


@router.get("", response_model=ClipListResponse, summary="List ranked clips")
def list_clips(
    repository: ProjectRepoDep,
    project_id: str | None = Query(default=None, description="Filter by project ID"),
    job_id: str | None = Query(default=None, description="Filter by analysis job ID"),
    emotion: str | None = Query(default=None, description="Filter by emotion label"),
    min_score: float | None = Query(default=None, ge=0, le=10, description="Minimum viral score"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ClipListResponse:
    """Return ranked clips with optional filters."""
    items, total = repository.list_clips(
        project_id=project_id,
        job_id=job_id,
        emotion=emotion,
        min_score=min_score,
        limit=limit,
        offset=offset,
    )
    return ClipListResponse(items=items, total=total, limit=limit, offset=offset)
