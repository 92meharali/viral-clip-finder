"""Face tracker factory."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.core.exceptions import UnknownFaceTrackerError
from app.reframe.tracking.base import FaceTracker
from app.reframe.tracking.iou import IoUFaceTracker

SUPPORTED_FACE_TRACKERS = frozenset({"iou"})


def get_face_tracker(
    settings: Settings | None = None,
    *,
    provider: str | None = None,
) -> FaceTracker:
    """Create a :class:`FaceTracker` for the configured backend.

    Args:
        settings: Optional settings override.
        provider: Tracker name override (``iou``).

    Returns:
        Configured face tracker instance.

    Raises:
        UnknownFaceTrackerError: If the tracker name is not supported.
    """
    resolved = settings or get_settings()
    tracker_name = (provider or resolved.face_tracker).strip().lower()

    if tracker_name not in SUPPORTED_FACE_TRACKERS:
        supported = ", ".join(sorted(SUPPORTED_FACE_TRACKERS))
        raise UnknownFaceTrackerError(
            f"Unknown face tracker '{tracker_name}'. Supported trackers: {supported}"
        )

    if tracker_name == "iou":
        return IoUFaceTracker(settings=resolved)

    raise UnknownFaceTrackerError(f"Tracker '{tracker_name}' is not implemented")
