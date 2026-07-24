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
