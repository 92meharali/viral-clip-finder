"""Reframe render result models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ReframeRenderResult(BaseModel):
    """Metadata for a reframed vertical render."""

    source_path: str
    output_path: str
    width: int = Field(..., ge=1)
    height: int = Field(..., ge=1)
    segment_count: int = Field(..., ge=1)
    crop_keyframe_count: int = Field(..., ge=0)
    blurred_background: bool = Field(default=False)
    render_fps: float = Field(..., gt=0)

    model_config = {"frozen": True}
