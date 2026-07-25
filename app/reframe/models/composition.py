"""Shot composition data models."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ShotType(str, Enum):
    """Composition intent for a single frame."""

    SINGLE_SPEAKER = "single_speaker"
    CONVERSATION = "conversation"
    GROUP_REACTION = "group_reaction"
    VOTE_REVEAL = "vote_reveal"
    MULTI_REACTION = "multi_reaction"
    SILENT_REACTION = "silent_reaction"
    WIDE_TABLE = "wide_table"


class FramingTarget(BaseModel):
    """Desired virtual camera target in source pixel coordinates."""

    center_x: float = Field(..., ge=0)
    center_y: float = Field(..., ge=0)
    crop_width: float = Field(..., gt=0, description="Virtual crop width in source pixels")
    crop_height: float = Field(..., gt=0, description="Virtual crop height in source pixels")

    model_config = {"frozen": True}

    @property
    def zoom_scale(self) -> float:
        """Relative zoom where larger values mean a wider field of view."""
        return self.crop_width


class FrameComposition(BaseModel):
    """Composition decision for one analyzed frame."""

    frame_number: int = Field(..., ge=0)
    timestamp: float = Field(..., ge=0)
    shot_type: ShotType
    target_track_ids: list[str] = Field(default_factory=list)
    framing: FramingTarget
    zoom_multiplier: float = Field(default=1.0, ge=1.0)
    reasoning: str = Field(..., min_length=1)

    model_config = {"frozen": True}


class CompositionResult(BaseModel):
    """Full shot composition output for a tracked sequence."""

    source_width: int = Field(..., ge=1)
    source_height: int = Field(..., ge=1)
    target_aspect: float = Field(..., gt=0, description="Output width / height ratio")
    frames: list[FrameComposition] = Field(default_factory=list)

    model_config = {"frozen": True}
