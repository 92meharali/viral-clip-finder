"""Velocity-limited pursuit virtual camera planner."""

from __future__ import annotations

import math

from app.core.config import Settings, get_settings
from app.reframe.camera.base import VirtualCameraPlanner
from app.reframe.models.camera import CameraPath, VirtualCameraFrame
from app.reframe.models.composition import CompositionResult, FrameComposition
from app.reframe.models.scenes import SceneDetectionResult


class PursuitCameraPlanner(VirtualCameraPlanner):
    """Follow composition targets with bounded pan and zoom speeds."""

    planner_name = "pursuit"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def plan(
        self,
        composition: CompositionResult,
        *,
        scene_result: SceneDetectionResult | None = None,
    ) -> CameraPath:
        if not composition.frames:
            return CameraPath(
                source_width=composition.source_width,
                source_height=composition.source_height,
                target_aspect=composition.target_aspect,
            )

        frames: list[VirtualCameraFrame] = []
        previous: VirtualCameraFrame | None = None
        previous_velocity = (0.0, 0.0, 0.0)

        for index, frame in enumerate(composition.frames):
            delta_seconds = _delta_seconds(composition.frames, index)
            target = frame.framing
            if previous is None or _should_reset_at_boundary(
                frame,
                scene_result=scene_result,
                tolerance=self.settings.camera_scene_boundary_tolerance,
                reset_enabled=self.settings.camera_scene_reset,
            ):
                current = VirtualCameraFrame(
                    frame_number=frame.frame_number,
                    timestamp=frame.timestamp,
                    center_x=target.center_x,
                    center_y=target.center_y,
                    zoom=target.crop_width,
                    crop_height=target.crop_height,
                )
                frames.append(current)
                previous = current
                previous_velocity = (0.0, 0.0, 0.0)
                continue

            assert previous is not None
            next_center_x, next_center_y, next_zoom = _pursue_target(
                previous.center_x,
                previous.center_y,
                previous.zoom,
                target.center_x,
                target.center_y,
                target.crop_width,
                delta_seconds=delta_seconds,
                max_pan_speed=self.settings.camera_max_pan_speed,
                max_zoom_speed=self.settings.camera_max_zoom_speed,
                smoothing=self.settings.camera_smoothing,
            )
            velocity_x = (next_center_x - previous.center_x) / delta_seconds
            velocity_y = (next_center_y - previous.center_y) / delta_seconds
            zoom_velocity = (next_zoom - previous.zoom) / delta_seconds
            acceleration_x = (velocity_x - previous_velocity[0]) / delta_seconds
            acceleration_y = (velocity_y - previous_velocity[1]) / delta_seconds
            zoom_acceleration = (zoom_velocity - previous_velocity[2]) / delta_seconds

            current = VirtualCameraFrame(
                frame_number=frame.frame_number,
                timestamp=frame.timestamp,
                center_x=next_center_x,
                center_y=next_center_y,
                zoom=next_zoom,
                crop_height=target.crop_height,
                velocity_x=velocity_x,
                velocity_y=velocity_y,
                zoom_velocity=zoom_velocity,
                acceleration_x=acceleration_x,
                acceleration_y=acceleration_y,
                zoom_acceleration=zoom_acceleration,
            )
            frames.append(current)
            previous = current
            previous_velocity = (velocity_x, velocity_y, zoom_velocity)

        return CameraPath(
            source_width=composition.source_width,
            source_height=composition.source_height,
            target_aspect=composition.target_aspect,
            frames=frames,
        )


def _delta_seconds(frames: list[FrameComposition], index: int) -> float:
    if index == 0:
        return 0.5

    current = frames[index].timestamp
    previous = frames[index - 1].timestamp
    delta = current - previous
    return delta if delta > 0 else 0.5


def _should_reset_at_boundary(
    frame: FrameComposition,
    *,
    scene_result: SceneDetectionResult | None,
    tolerance: float,
    reset_enabled: bool,
) -> bool:
    if not reset_enabled or scene_result is None:
        return False
    return scene_result.is_near_boundary(frame.timestamp, tolerance=tolerance)


def _pursue_target(
    center_x: float,
    center_y: float,
    zoom: float,
    target_x: float,
    target_y: float,
    target_zoom: float,
    *,
    delta_seconds: float,
    max_pan_speed: float,
    max_zoom_speed: float,
    smoothing: float,
) -> tuple[float, float, float]:
    dx = target_x - center_x
    dy = target_y - center_y
    dz = target_zoom - zoom

    pan_distance = math.hypot(dx, dy)
    max_pan_move = max_pan_speed * delta_seconds
    if pan_distance > 0:
        pan_step = min(1.0, max_pan_move / pan_distance)
        pan_step = min(pan_step, smoothing)
        center_x += dx * pan_step
        center_y += dy * pan_step

    max_zoom_move = max_zoom_speed * delta_seconds
    if abs(dz) > 0:
        zoom_step = min(1.0, max_zoom_move / abs(dz))
        zoom_step = min(zoom_step, smoothing)
        zoom += dz * zoom_step

    return (center_x, center_y, zoom)
