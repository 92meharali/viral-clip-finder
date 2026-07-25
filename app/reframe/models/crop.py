"""Safe crop plan data models."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class CropFrame(BaseModel):
    """Final crop rectangle in source pixel coordinates."""

    frame_number: int = Field(..., ge=0)
    timestamp: float = Field(..., ge=0)
    x: float = Field(..., description="Top-left X in source pixels")
    y: float = Field(..., description="Top-left Y in source pixels")
    width: float = Field(..., gt=0, description="Crop width in source pixels")
    height: float = Field(..., gt=0, description="Crop height in source pixels")

    model_config = {"frozen": True}

    @property
    def center_x(self) -> float:
        """Horizontal center of the crop."""
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        """Vertical center of the crop."""
        return self.y + self.height / 2

    @model_validator(mode="after")
    def validate_dimensions(self) -> CropFrame:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Crop width and height must be positive")
        return self


class CropSegment(BaseModel):
    """A time span with a constant crop rectangle for rendering."""

    start_time: float = Field(..., ge=0)
    end_time: float = Field(..., gt=0)
    crop: CropFrame

    model_config = {"frozen": True}

    @property
    def duration_seconds(self) -> float:
        """Segment duration."""
        return max(0.0, self.end_time - self.start_time)


class CropPlan(BaseModel):
    """Full crop plan for a clip."""

    source_width: int = Field(..., ge=1)
    source_height: int = Field(..., ge=1)
    target_width: int = Field(..., ge=1)
    target_height: int = Field(..., ge=1)
    frames: list[CropFrame] = Field(default_factory=list)
    segments: list[CropSegment] = Field(default_factory=list)

    model_config = {"frozen": True}

    @property
    def frame_count(self) -> int:
        """Number of crop keyframes."""
        return len(self.frames)
