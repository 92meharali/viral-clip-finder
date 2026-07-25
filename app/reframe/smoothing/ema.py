"""EMA temporal smoothing with jerk and zoom-oscillation control."""

from __future__ import annotations

import math

from app.core.config import Settings, get_settings
from app.reframe.models.camera import CameraPath, VirtualCameraFrame
from app.reframe.models.scenes import SceneDetectionResult
from app.reframe.smoothing.base import TemporalSmoother


class EmaTemporalSmoother(TemporalSmoother):
    """Apply exponential smoothing within scene segments."""

    smoother_name = "ema"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def smooth(
        self,
        camera_path: CameraPath,
        *,
        scene_result: SceneDetectionResult | None = None,
    ) -> CameraPath:
        if not camera_path.frames:
            return camera_path

        segments = _split_frames_by_scene(
            camera_path.frames,
            scene_result=scene_result,
            tolerance=self.settings.smoothing_scene_boundary_tolerance,
        )

        smoothed_frames: list[VirtualCameraFrame] = []
        for segment in segments:
            smoothed_frames.extend(self._smooth_segment(segment))

        return CameraPath(
            source_width=camera_path.source_width,
            source_height=camera_path.source_height,
            target_aspect=camera_path.target_aspect,
            frames=smoothed_frames,
        )

    def _smooth_segment(self, frames: list[VirtualCameraFrame]) -> list[VirtualCameraFrame]:
        if not frames:
            return []

        alpha = self.settings.smoothing_strength
        max_jerk = self.settings.smoothing_max_jerk
        zoom_damping = self.settings.smoothing_zoom_oscillation_damping

        smoothed: list[VirtualCameraFrame] = []
        ema_center_x = frames[0].center_x
        ema_center_y = frames[0].center_y
        ema_zoom = frames[0].zoom
        prev_velocity = (0.0, 0.0, 0.0)
        prev_zoom_velocity = 0.0

        for index, frame in enumerate(frames):
            delta_seconds = _delta_seconds(frames, index)

            target_x = alpha * frame.center_x + (1.0 - alpha) * ema_center_x
            target_y = alpha * frame.center_y + (1.0 - alpha) * ema_center_y
            target_zoom = alpha * frame.zoom + (1.0 - alpha) * ema_zoom

            if index > 0 and prev_zoom_velocity != 0.0:
                raw_zoom_velocity = (target_zoom - ema_zoom) / delta_seconds
                if math.copysign(1.0, raw_zoom_velocity) != math.copysign(1.0, prev_zoom_velocity):
                    target_zoom = ema_zoom + (target_zoom - ema_zoom) * zoom_damping

            if index > 0:
                velocity_x = (target_x - ema_center_x) / delta_seconds
                velocity_y = (target_y - ema_center_y) / delta_seconds
                zoom_velocity = (target_zoom - ema_zoom) / delta_seconds

                velocity_x = _limit_jerk(velocity_x, prev_velocity[0], max_jerk, delta_seconds)
                velocity_y = _limit_jerk(velocity_y, prev_velocity[1], max_jerk, delta_seconds)
                zoom_velocity = _limit_jerk(zoom_velocity, prev_velocity[2], max_jerk, delta_seconds)

                target_x = ema_center_x + velocity_x * delta_seconds
                target_y = ema_center_y + velocity_y * delta_seconds
                target_zoom = ema_zoom + zoom_velocity * delta_seconds
            else:
                velocity_x = 0.0
                velocity_y = 0.0
                zoom_velocity = 0.0

            acceleration_x = (velocity_x - prev_velocity[0]) / delta_seconds if index > 0 else 0.0
            acceleration_y = (velocity_y - prev_velocity[1]) / delta_seconds if index > 0 else 0.0
            zoom_acceleration = (zoom_velocity - prev_velocity[2]) / delta_seconds if index > 0 else 0.0

            smoothed.append(
                VirtualCameraFrame(
                    frame_number=frame.frame_number,
                    timestamp=frame.timestamp,
                    center_x=target_x,
                    center_y=target_y,
                    zoom=target_zoom,
                    crop_height=frame.crop_height,
                    velocity_x=velocity_x,
                    velocity_y=velocity_y,
                    zoom_velocity=zoom_velocity,
                    acceleration_x=acceleration_x,
                    acceleration_y=acceleration_y,
                    zoom_acceleration=zoom_acceleration,
                )
            )

            ema_center_x = target_x
            ema_center_y = target_y
            ema_zoom = target_zoom
            prev_velocity = (velocity_x, velocity_y, zoom_velocity)
            prev_zoom_velocity = zoom_velocity

        return smoothed


def _split_frames_by_scene(
    frames: list[VirtualCameraFrame],
    *,
    scene_result: SceneDetectionResult | None,
    tolerance: float,
) -> list[list[VirtualCameraFrame]]:
    if scene_result is None or not scene_result.boundaries:
        return [frames]

    segments: list[list[VirtualCameraFrame]] = []
    current: list[VirtualCameraFrame] = []

    for frame in frames:
        if current and scene_result.is_near_boundary(frame.timestamp, tolerance=tolerance):
            segments.append(current)
            current = []
        current.append(frame)

    if current:
        segments.append(current)

    return segments


def _delta_seconds(frames: list[VirtualCameraFrame], index: int) -> float:
    if index == 0:
        return 0.5
    delta = frames[index].timestamp - frames[index - 1].timestamp
    return delta if delta > 0 else 0.5


def _limit_jerk(
    velocity: float,
    previous_velocity: float,
    max_jerk: float,
    delta_seconds: float,
) -> float:
    max_delta = max_jerk * delta_seconds
    delta_velocity = velocity - previous_velocity
    if abs(delta_velocity) <= max_delta:
        return velocity
    return previous_velocity + math.copysign(max_delta, delta_velocity)
