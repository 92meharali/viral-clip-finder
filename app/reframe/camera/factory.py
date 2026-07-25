"""Virtual camera planner factory."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.core.exceptions import UnknownCameraPlannerError
from app.reframe.camera.base import VirtualCameraPlanner
from app.reframe.camera.pursuit import PursuitCameraPlanner

SUPPORTED_CAMERA_PLANNERS = frozenset({"pursuit"})


def get_camera_planner(settings: Settings | None = None) -> VirtualCameraPlanner:
    """Return the configured virtual camera planner backend."""
    resolved = settings or get_settings()
    planner_name = resolved.camera_planner.strip().lower()

    if planner_name not in SUPPORTED_CAMERA_PLANNERS:
        supported = ", ".join(sorted(SUPPORTED_CAMERA_PLANNERS))
        raise UnknownCameraPlannerError(
            f"Unsupported camera planner '{resolved.camera_planner}'. Supported: {supported}"
        )

    if planner_name == "pursuit":
        return PursuitCameraPlanner(resolved)

    raise UnknownCameraPlannerError(f"No implementation for camera planner '{planner_name}'")
