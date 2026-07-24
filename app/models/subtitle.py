"""Subtitle data models and styling."""

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class SubtitlePosition(str, Enum):
    """Vertical placement of burned-in subtitles."""

    TOP = "top"
    CENTER = "center"
    BOTTOM = "bottom"


class SubtitleStyle(BaseModel):
    """Styling options for burned-in subtitles."""

    font: str = Field(default="Arial", min_length=1, description="Font family name")
    size: int = Field(default=24, ge=8, le=96, description="Font size in pixels")
    outline: int = Field(default=2, ge=0, le=10, description="Outline thickness")
    color: str = Field(default="white", description="Text color name or #RRGGBB hex")
    position: SubtitlePosition = Field(
        default=SubtitlePosition.BOTTOM,
        description="Vertical subtitle position",
    )

    model_config = {"frozen": True}

    @field_validator("color")
    @classmethod
    def normalize_color(cls, value: str) -> str:
        """Normalize color to lowercase."""
        return value.strip().lower()


class SubtitleCue(BaseModel):
    """A single subtitle cue with clip-relative timing."""

    index: int = Field(..., ge=1, description="Cue sequence number")
    start_seconds: float = Field(..., ge=0, description="Start time relative to clip")
    end_seconds: float = Field(..., gt=0, description="End time relative to clip")
    text: str = Field(..., min_length=1, description="Subtitle text")

    model_config = {"frozen": True}


class SubtitleFile(BaseModel):
    """Metadata for a generated SRT subtitle file."""

    index: int = Field(..., ge=1, description="Clip index")
    clip_start: str = Field(..., description="Clip start in source video (HH:MM:SS)")
    clip_end: str = Field(..., description="Clip end in source video (HH:MM:SS)")
    srt_path: str = Field(..., description="Path to the .srt file")
    cue_count: int = Field(..., ge=0, description="Number of subtitle cues")
    burned_output_path: str | None = Field(
        default=None,
        description="Path to video with burned-in subtitles, if rendered",
    )

    model_config = {"frozen": True}
