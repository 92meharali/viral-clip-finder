"""FastAPI application factory and ASGI entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from loguru import logger

from app.api.routes import analyze, health
from app.core.config import Settings, get_settings
from app.database.session import Database
from app.services.analysis.sqlalchemy_store import SqlAlchemyAnalysisJobStore
from app.services.analysis.store import AnalysisJobStore, InMemoryAnalysisJobStore

API_TITLE = "Viral Clip Finder API"
API_DESCRIPTION = (
    "AI Video Intelligence Platform — find viral moments in long-form video transcripts."
)
API_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Configure logging and emit startup/shutdown events."""
    settings = get_settings()
    database = getattr(app.state, "database", None)
    if database is not None and settings.database_auto_create:
        database.create_tables()
    logger.info(
        "Starting {service} API (log_level={level})",
        service=health.SERVICE_NAME,
        level=settings.log_level,
    )
    yield
    logger.info("Shutting down {service} API", service=health.SERVICE_NAME)


def _build_job_store(
    settings: Settings,
    job_store: AnalysisJobStore | None = None,
) -> tuple[AnalysisJobStore, Database | None]:
    """Create the configured analysis job store."""
    if job_store is not None:
        return job_store, None

    database = Database(settings)
    store = SqlAlchemyAnalysisJobStore(database.session_factory)
    return store, database


def create_app(
    settings: Settings | None = None,
    job_store: AnalysisJobStore | None = None,
) -> FastAPI:
    """Build and return the FastAPI application.

    Args:
        settings: Optional settings override (useful for tests).
        job_store: Optional job store override for tests.

    Returns:
        Configured FastAPI instance with all routers mounted.
    """
    if settings is not None:
        get_settings.cache_clear()

    resolved_settings = settings or get_settings()
    store, database = _build_job_store(resolved_settings, job_store)

    app = FastAPI(
        title=API_TITLE,
        description=API_DESCRIPTION,
        version=API_VERSION,
        lifespan=lifespan,
    )
    app.state.job_store = store
    if database is not None:
        app.state.database = database
    app.include_router(health.router)
    app.include_router(analyze.router)
    return app


app = create_app()


def run() -> None:
    """Run the API server with uvicorn (CLI entrypoint)."""
    settings = get_settings()
    uvicorn.run(
        "app.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run()
