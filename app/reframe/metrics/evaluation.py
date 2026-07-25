"""Compute reframing quality metrics."""

from __future__ import annotations

import math

from app.reframe.crop.geometry import face_visibility_ratio
from app.reframe.metrics.models import ReframeEvaluationMetrics
from app.reframe.models.camera import CameraPath
from app.reframe.models.crop import CropPlan
from app.reframe.models.scenes import SceneDetectionResult
from app.reframe.models.tracking import TrackingResult


def evaluate_reframe(
    *,
    tracking: TrackingResult,
    crop_plan: CropPlan,
    camera_path: CameraPath,
    scene_result: SceneDetectionResult | None = None,
    visibility_threshold: float = 0.95,
) -> ReframeEvaluationMetrics:
    """Compute evaluation metrics for a reframed clip."""
    crop_by_frame = {frame.frame_number: frame for frame in crop_plan.frames}
    tracking_by_frame = {frame.frame_number: frame for frame in tracking.frames}

    visibility_values: list[float] = []
    clipped_faces = 0
    total_face_frames = 0
    empty_space_values: list[float] = []

    for frame_number, crop in crop_by_frame.items():
        tracked = tracking_by_frame.get(frame_number)
        if tracked is None or not tracked.faces:
            empty_space_values.append(1.0)
            continue

        face_area = sum(face.bounding_box.area for face in tracked.faces)
        crop_area = max(1.0, crop.width * crop.height)
        empty_space_values.append(max(0.0, 1.0 - min(1.0, face_area / crop_area)))

        for face in tracked.faces:
            visibility = face_visibility_ratio(crop, face)
            visibility_values.append(visibility)
            total_face_frames += 1
            if visibility < visibility_threshold:
                clipped_faces += 1

    movement_distance = _camera_movement_distance(camera_path)
    jitter_score = _camera_jitter_score(camera_path)
    unnecessary_cuts = _unnecessary_cut_count(camera_path, scene_result)

    average_visibility = (
        sum(visibility_values) / len(visibility_values) if visibility_values else 0.0
    )
    clipped_percentage = (
        (clipped_faces / total_face_frames) * 100.0 if total_face_frames > 0 else 0.0
    )
    average_empty_space = (
        sum(empty_space_values) / len(empty_space_values) if empty_space_values else 1.0
    )

    return ReframeEvaluationMetrics(
        average_face_visibility=average_visibility,
        clipped_face_percentage=clipped_percentage,
        average_empty_space_ratio=average_empty_space,
        camera_movement_distance=movement_distance,
        camera_jitter_score=jitter_score,
        unnecessary_cut_count=unnecessary_cuts,
        frame_count=len(crop_plan.frames),
        face_frame_count=total_face_frames,
    )


def _camera_movement_distance(camera_path: CameraPath) -> float:
    if len(camera_path.frames) < 2:
        return 0.0

    total = 0.0
    for index in range(1, len(camera_path.frames)):
        previous = camera_path.frames[index - 1]
        current = camera_path.frames[index]
        total += math.hypot(
            current.center_x - previous.center_x,
            current.center_y - previous.center_y,
        )
    return total


def _camera_jitter_score(camera_path: CameraPath) -> float:
    if len(camera_path.frames) < 2:
        return 0.0

    jitter = 0.0
    for frame in camera_path.frames[1:]:
        jitter += math.hypot(frame.acceleration_x, frame.acceleration_y)
        jitter += abs(frame.zoom_acceleration)
    return jitter


def _unnecessary_cut_count(
    camera_path: CameraPath,
    scene_result: SceneDetectionResult | None,
) -> int:
    if scene_result is None or len(camera_path.frames) < 2:
        return 0

    unnecessary = 0
    for index in range(1, len(camera_path.frames)):
        timestamp = camera_path.frames[index].timestamp
        if not scene_result.is_near_boundary(timestamp, tolerance=0.15):
            previous = camera_path.frames[index - 1]
            current = camera_path.frames[index]
            jump = math.hypot(
                current.center_x - previous.center_x,
                current.center_y - previous.center_y,
            )
            zoom_jump = abs(current.zoom - previous.zoom)
            if jump > 250.0 or zoom_jump > 200.0:
                unnecessary += 1
    return unnecessary
