"""Tests for CORS configuration."""

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.core.config import Settings
from app.services.analysis.store import InMemoryAnalysisJobStore


def test_cors_allows_frontend_origin() -> None:
    """Preflight from the Next.js dev server should succeed."""
    settings = Settings(cors_origins="http://localhost:3000")
    app = create_app(settings=settings, job_store=InMemoryAnalysisJobStore())
    client = TestClient(app)

    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
