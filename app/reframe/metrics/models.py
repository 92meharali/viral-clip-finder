"""Reframe evaluation metric models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ReframeEvaluationMetrics(BaseModel):
    """Quality metrics for an intelligent reframe render."""

    average_face_visibility: float = Field(..., ge=0, le=1)
    clipped_face_percentage: float = Field(..., ge=0, le=100)
    average_empty_space_ratio: float = Field(..., ge=0, le=1)
    camera_movement_distance: float = Field(..., ge=0)
    camera_jitter_score: float = Field(..., ge=0)
    unnecessary_cut_count: int = Field(..., ge=0)
    frame_count: int = Field(..., ge=0)
    face_frame_count: int = Field(..., ge=0)

    model_config = {"frozen": True}
