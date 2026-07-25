"""Face tracking backends and service."""

from app.reframe.tracking.base import FaceTracker
from app.reframe.tracking.factory import SUPPORTED_FACE_TRACKERS, get_face_tracker
from app.reframe.tracking.iou import IoUFaceTracker
from app.reframe.tracking.service import (
    FaceTrackingService,
    track_faces_in_frames,
    track_faces_in_video,
)

__all__ = [
    "FaceTracker",
    "FaceTrackingService",
    "IoUFaceTracker",
    "SUPPORTED_FACE_TRACKERS",
    "get_face_tracker",
    "track_faces_in_frames",
    "track_faces_in_video",
]
