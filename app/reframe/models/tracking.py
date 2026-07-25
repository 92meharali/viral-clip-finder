"""Face tracking data models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.reframe.models.faces import BoundingBox, FaceLandmarks


class TrackedFace(BaseModel):
    """A detected face with a persistent track identity."""

    track_id: str = Field(..., min_length=1, description="Persistent person track id")
    bounding_box: BoundingBox
    detection_confidence: float = Field(
        ...,
        ge=0,
        le=1,
        description="Face detector confidence",
    )
    association_score: float = Field(
        default=1.0,
        ge=0,
        le=1,
        description="Track-to-detection association confidence",
    )
    landmarks: FaceLandmarks | None = Field(
        default=None,
        description="Optional eye and mouth landmarks",
    )

    model_config = {"frozen": True}

    @property
    def center(self) -> tuple[float, float]:
        """Face center derived from the bounding box."""
        return self.bounding_box.center


class FrameTracks(BaseModel):
    """Tracked faces in a single video frame."""

    frame_number: int = Field(..., ge=0)
    timestamp: float = Field(..., ge=0)
    image_width: int = Field(..., ge=1)
    image_height: int = Field(..., ge=1)
    faces: list[TrackedFace] = Field(default_factory=list)
    active_track_ids: list[str] = Field(
        default_factory=list,
        description="Track ids visible in this frame",
    )

    model_config = {"frozen": True}

    @property
    def face_count(self) -> int:
        """Number of tracked faces visible in this frame."""
        return len(self.faces)


class TrackSummary(BaseModel):
    """Lifecycle summary for a single person track."""

    track_id: str
    first_frame: int = Field(..., ge=0)
    last_frame: int = Field(..., ge=0)
    first_timestamp: float = Field(..., ge=0)
    last_timestamp: float = Field(..., ge=0)
    total_detections: int = Field(..., ge=1)
    max_consecutive_misses: int = Field(default=0, ge=0)

    model_config = {"frozen": True}

    @property
    def duration_seconds(self) -> float:
        """Track span from first to last detection."""
        return max(0.0, self.last_timestamp - self.first_timestamp)


class TrackingResult(BaseModel):
    """Full tracking output for a video sequence."""

    frames: list[FrameTracks] = Field(default_factory=list)
    tracks: dict[str, TrackSummary] = Field(default_factory=dict)

    model_config = {"frozen": True}

    @property
    def track_count(self) -> int:
        """Number of unique person tracks."""
        return len(self.tracks)
