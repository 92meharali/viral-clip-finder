"""FastAPI dependency injection helpers."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Request

from app.core.config import Settings, get_settings
from app.services.analysis.service import AnalysisJobService
from app.services.analysis.store import AnalysisJobStore


@lru_cache
def get_settings_dep() -> Settings:
    """Cached settings dependency for FastAPI routes."""
    return get_settings()


def get_job_store(request: Request) -> AnalysisJobStore:
    """Return the application-scoped job store."""
    store = getattr(request.app.state, "job_store", None)
    if store is None:
        raise RuntimeError("Application job store is not configured")
    return store


def get_analysis_job_service(request: Request) -> AnalysisJobService:
    """Build an analysis job service for the current request."""
    settings = get_settings_dep()
    store = get_job_store(request)
    return AnalysisJobService(store, settings)
