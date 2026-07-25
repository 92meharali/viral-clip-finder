"""Health check endpoint."""

from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])

SERVICE_NAME = "viral-clip-finder"
API_VERSION = "0.1.0"


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Return service health for load balancers and orchestrators."""
    return HealthResponse(
        status="ok",
        service=SERVICE_NAME,
        version=API_VERSION,
    )
