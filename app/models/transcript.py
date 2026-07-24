"""Transcript data models."""

from pydantic import BaseModel, Field, field_validator


class TranscriptSegment(BaseModel):
    """A single segment of parsed transcript dialogue.

    Attributes:
        start: Human-readable timestamp (HH:MM:SS).
        seconds: Start time converted to total seconds.
        speaker: Optional speaker label when available.
        text: Dialogue text for this segment.
    """

    start: str = Field(..., description="Timestamp in HH:MM:SS format")
    seconds: float = Field(..., ge=0, description="Start time in seconds")
    speaker: str | None = Field(default=None, description="Speaker label if detected")
    text: str = Field(..., min_length=1, description="Dialogue text")

    @field_validator("text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        """Normalize whitespace in dialogue text."""
        return " ".join(value.split())

    model_config = {"frozen": True}
