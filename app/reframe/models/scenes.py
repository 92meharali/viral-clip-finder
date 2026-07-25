"""Scene detection data models."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SceneBoundaryType(str, Enum):
    """Type of visual transition between scenes."""

    CUT = "cut"
    DISSOLVE = "dissolve"
    ZOOM = "zoom"
    UNKNOWN = "unknown"


class SceneBoundary(BaseModel):
    """A detected transition between shots."""

    timestamp: float = Field(..., ge=0, description="Boundary time in seconds")
    confidence: float = Field(..., ge=0, le=1, description="Detector confidence score")
    boundary_type: SceneBoundaryType = Field(
        default=SceneBoundaryType.CUT,
        description="Transition type",
    )
    frame_number: int | None = Field(
        default=None,
        ge=0,
        description="Optional source frame index",
    )

    model_config = {"frozen": True}


class SceneSegment(BaseModel):
    """A continuous shot between scene boundaries."""

    index: int = Field(..., ge=0, description="Zero-based scene index")
    start_seconds: float = Field(..., ge=0)
    end_seconds: float = Field(..., gt=0)
    duration_seconds: float = Field(..., gt=0)

    model_config = {"frozen": True}


class SceneDetectionResult(BaseModel):
    """Full scene analysis for a video or clip."""

    source_path: str
    duration_seconds: float = Field(..., gt=0)
    boundaries: list[SceneBoundary] = Field(default_factory=list)
    segments: list[SceneSegment] = Field(default_factory=list)

    model_config = {"frozen": True}

    @property
    def scene_count(self) -> int:
        """Number of detected scenes."""
        return len(self.segments)

    def segment_at(self, timestamp: float) -> SceneSegment | None:
        """Return the scene segment containing a timestamp."""
        for segment in self.segments:
            if segment.start_seconds <= timestamp < segment.end_seconds:
                return segment
        if self.segments and timestamp >= self.segments[-1].end_seconds:
            return self.segments[-1]
        return None

    def is_near_boundary(self, timestamp: float, *, tolerance: float) -> bool:
        """Return whether a timestamp is close to any scene boundary."""
        return any(abs(timestamp - boundary.timestamp) <= tolerance for boundary in self.boundaries)
