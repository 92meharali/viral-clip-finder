"""Virtual camera path data models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class VirtualCameraFrame(BaseModel):
    """Virtual camera state for one output frame."""

    frame_number: int = Field(..., ge=0)
    timestamp: float = Field(..., ge=0)
    center_x: float = Field(..., ge=0)
    center_y: float = Field(..., ge=0)
    zoom: float = Field(..., gt=0, description="Crop width in source pixels")
    crop_height: float = Field(..., gt=0, description="Crop height in source pixels")
    velocity_x: float = Field(default=0.0)
    velocity_y: float = Field(default=0.0)
    zoom_velocity: float = Field(default=0.0)
    acceleration_x: float = Field(default=0.0)
    acceleration_y: float = Field(default=0.0)
    zoom_acceleration: float = Field(default=0.0)

    model_config = {"frozen": True}


class CameraPath(BaseModel):
    """Continuous virtual camera path across a clip."""

    source_width: int = Field(..., ge=1)
    source_height: int = Field(..., ge=1)
    target_aspect: float = Field(..., gt=0)
    frames: list[VirtualCameraFrame] = Field(default_factory=list)

    model_config = {"frozen": True}

    @property
    def frame_count(self) -> int:
        """Number of planned camera frames."""
        return len(self.frames)
