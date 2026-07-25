"""FastAPI dependency injection helpers."""

from __future__ import annotations

from functools import lru_cache

from fastapi import HTTPException, Request, status

from app.core.config import Settings, get_settings
from app.database.session import Database
from app.services.analysis.service import AnalysisJobService
from app.services.analysis.store import AnalysisJobStore
from app.services.projects.repository import ProjectRepository


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


def get_database(request: Request) -> Database:
    """Return the application database."""
    database = getattr(request.app.state, "database", None)
    if database is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured",
        )
    return database


def get_project_repository(request: Request) -> ProjectRepository:
    """Build a project repository for the current request."""
    database = get_database(request)
    return ProjectRepository(database.session_factory)
