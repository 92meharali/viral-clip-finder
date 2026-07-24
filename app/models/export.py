"""Exported clip metadata."""

from pydantic import BaseModel, Field


class ExtractedClip(BaseModel):
    """Metadata for a video clip extracted from a source file."""

    index: int = Field(..., ge=1, description="1-based clip number")
    source_path: str = Field(..., description="Path to the source video")
    output_path: str = Field(..., description="Path to the extracted clip file")
    start: str = Field(..., description="Clip start timestamp (HH:MM:SS)")
    end: str = Field(..., description="Clip end timestamp (HH:MM:SS)")
    start_seconds: float = Field(..., ge=0, description="Start time in seconds")
    end_seconds: float = Field(..., ge=0, description="End time in seconds")
    duration_seconds: float = Field(..., gt=0, description="Clip duration in seconds")
    reencoded: bool = Field(
        default=False,
        description="True if the clip was re-encoded instead of stream-copied",
    )

    model_config = {"frozen": True}


class VerticalClip(BaseModel):
    """Metadata for a vertically cropped clip ready for short-form platforms."""

    index: int = Field(..., ge=1, description="1-based clip number")
    source_path: str = Field(..., description="Path to the input clip video")
    output_path: str = Field(..., description="Path to the vertical output file")
    width: int = Field(..., ge=1, description="Output video width in pixels")
    height: int = Field(..., ge=1, description="Output video height in pixels")
    blurred_background: bool = Field(..., description="Whether a blurred background was applied")
    crop_mode: str = Field(..., description="Crop strategy used (center_crop or blur_background)")

    model_config = {"frozen": True}
