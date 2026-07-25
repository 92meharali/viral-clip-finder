"""Tests for the FastAPI health endpoint."""

from fastapi.testclient import TestClient

from app.api.main import create_app


def test_health_check_returns_ok() -> None:
    """Health endpoint reports service identity and version."""
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "status": "ok",
        "service": "viral-clip-finder",
        "version": "0.1.0",
    }


def test_openapi_schema_available() -> None:
    """OpenAPI schema is exposed for documentation tooling."""
    client = TestClient(create_app())

    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Viral Clip Finder API"
    assert "/health" in schema["paths"]
