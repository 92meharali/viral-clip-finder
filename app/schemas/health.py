"""Health check API schemas."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response payload for the service health endpoint."""

    status: str = Field(description="Service health status", examples=["ok"])
    service: str = Field(description="Service identifier", examples=["viral-clip-finder"])
    version: str = Field(description="API version", examples=["0.1.0"])
