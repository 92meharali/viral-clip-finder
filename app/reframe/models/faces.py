"""Face detection data models for the reframing pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field, computed_field, field_validator


class BoundingBox(BaseModel):
    """Axis-aligned bounding box in pixel coordinates."""

    x: float = Field(..., ge=0, description="Left edge in pixels")
    y: float = Field(..., ge=0, description="Top edge in pixels")
    width: float = Field(..., gt=0, description="Box width in pixels")
    height: float = Field(..., gt=0, description="Box height in pixels")

    model_config = {"frozen": True}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def center_x(self) -> float:
        """Horizontal center of the box."""
        return self.x + self.width / 2

    @computed_field  # type: ignore[prop-decorator]
    @property
    def center_y(self) -> float:
        """Vertical center of the box."""
        return self.y + self.height / 2

    @property
    def center(self) -> tuple[float, float]:
        """Center point as ``(x, y)``."""
        return (self.center_x, self.center_y)

    @property
    def area(self) -> float:
        """Bounding box area in square pixels."""
        return self.width * self.height

    def contains_point(self, x: float, y: float) -> bool:
        """Return whether a point lies inside the box."""
        return self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height

    def expand(self, padding: float) -> BoundingBox:
        """Return a copy expanded by padding on all sides."""
        return BoundingBox(
            x=max(0.0, self.x - padding),
            y=max(0.0, self.y - padding),
            width=self.width + padding * 2,
            height=self.height + padding * 2,
        )


class FaceLandmarks(BaseModel):
    """Optional facial landmark positions in pixel coordinates."""

    left_eye: tuple[float, float] | None = Field(
        default=None,
        description="Left eye center (subject's left)",
    )
    right_eye: tuple[float, float] | None = Field(
        default=None,
        description="Right eye center (subject's right)",
    )
    nose: tuple[float, float] | None = Field(default=None, description="Nose tip")
    mouth: tuple[float, float] | None = Field(default=None, description="Mouth center")

    model_config = {"frozen": True}

    @field_validator("left_eye", "right_eye", "nose", "mouth")
    @classmethod
    def validate_point(cls, value: tuple[float, float] | None) -> tuple[float, float] | None:
        """Ensure landmark tuples have exactly two coordinates."""
        if value is None:
            return None
        if len(value) != 2:
            raise ValueError("Landmark must be a (x, y) tuple")
        return value


class DetectedFace(BaseModel):
    """A single face detected in one video frame."""

    id: str | None = Field(
        default=None,
        description="Temporary face id until persistent tracking is assigned",
    )
    bounding_box: BoundingBox
    confidence: float = Field(..., ge=0, le=1, description="Detector confidence score")
    landmarks: FaceLandmarks | None = Field(
        default=None,
        description="Optional eye and mouth landmarks",
    )

    model_config = {"frozen": True}

    @property
    def center(self) -> tuple[float, float]:
        """Face center derived from the bounding box."""
        return self.bounding_box.center


class FrameFaces(BaseModel):
    """All faces detected in a single video frame."""

    frame_number: int = Field(..., ge=0, description="Zero-based frame index")
    timestamp: float = Field(..., ge=0, description="Frame timestamp in seconds")
    image_width: int = Field(..., ge=1, description="Source frame width in pixels")
    image_height: int = Field(..., ge=1, description="Source frame height in pixels")
    faces: list[DetectedFace] = Field(default_factory=list)

    model_config = {"frozen": True}

    @property
    def face_count(self) -> int:
        """Number of detected faces in this frame."""
        return len(self.faces)


class VideoFrame(BaseModel):
    """A single extracted video frame ready for analysis."""

    frame_number: int = Field(..., ge=0, description="Zero-based frame index")
    timestamp: float = Field(..., ge=0, description="Frame timestamp in seconds")
    image_path: str = Field(..., description="Path to the extracted frame image")
    width: int = Field(..., ge=1, description="Frame width in pixels")
    height: int = Field(..., ge=1, description="Frame height in pixels")

    model_config = {"frozen": True}
