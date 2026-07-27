"""Analysis job API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.api.dependencies import get_analysis_job_service
from app.core.config import get_settings
from app.core.exceptions import LLMAnalysisError
from app.providers.factory import ensure_provider_ready
from app.schemas.analyze import AnalysisJobResponse, AnalyzeRequest
from app.services.analysis.service import AnalysisJobService

router = APIRouter(prefix="/analyze", tags=["analysis"])

JobServiceDep = Annotated[AnalysisJobService, Depends(get_analysis_job_service)]


@router.post(
    "",
    response_model=AnalysisJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start YouTube analysis",
)
def start_analysis(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    service: JobServiceDep,
) -> AnalysisJobResponse:
    """Queue a background job to ingest and analyze a YouTube video."""
    settings = get_settings()
    resolved_provider = (request.provider or settings.api_ai_provider).strip().lower()
    try:
        ensure_provider_ready(resolved_provider, settings)
    except LLMAnalysisError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    job = service.create_job(
        request.url,
        provider=resolved_provider,
        top_n=request.top_n,
    )
    background_tasks.add_task(service.run_job, job.id)
    return AnalysisJobResponse.from_job(job)


@router.get(
    "/{job_id}",
    response_model=AnalysisJobResponse,
    summary="Get analysis job status",
)
def get_analysis_job(
    job_id: str,
    service: JobServiceDep,
) -> AnalysisJobResponse:
    """Return the current status and result for an analysis job."""
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job not found: {job_id}",
        )
    return AnalysisJobResponse.from_job(job)
