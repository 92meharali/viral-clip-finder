"""Tests for temporal smoothing."""

from __future__ import annotations

import math

import pytest

from app.core.config import Settings
from app.core.exceptions import UnknownTemporalSmootherError
from app.reframe.models.camera import CameraPath, VirtualCameraFrame
from app.reframe.models.scenes import SceneBoundary, SceneBoundaryType, SceneDetectionResult, SceneSegment
from app.reframe.smoothing.ema import EmaTemporalSmoother
from app.reframe.smoothing.factory import get_temporal_smoother
from app.reframe.smoothing.service import TemporalSmoothingService, smooth_camera_path


def _camera_frame(
    frame_number: int,
    *,
    center_x: float,
    center_y: float,
    zoom: float = 900.0,
    timestamp: float | None = None,
) -> VirtualCameraFrame:
    return VirtualCameraFrame(
        frame_number=frame_number,
        timestamp=timestamp if timestamp is not None else float(frame_number),
        center_x=center_x,
        center_y=center_y,
        zoom=zoom,
        crop_height=1600.0,
    )


@pytest.fixture
def settings() -> Settings:
    return Settings(
        temporal_smoother="ema",
        smoothing_strength=0.3,
        smoothing_max_jerk=500.0,
        smoothing_zoom_oscillation_damping=0.5,
        smoothing_scene_boundary_tolerance=0.1,
    )


class TestEmaTemporalSmoother:
    def test_reduces_position_jitter(self, settings: Settings) -> None:
        camera_path = CameraPath(
            source_width=1920,
            source_height=1080,
            target_aspect=1080 / 1920,
            frames=[
                _camera_frame(0, center_x=500.0, center_y=400.0, timestamp=0.0),
                _camera_frame(1, center_x=900.0, center_y=400.0, timestamp=0.5),
                _camera_frame(2, center_x=520.0, center_y=410.0, timestamp=1.0),
                _camera_frame(3, center_x=880.0, center_y=390.0, timestamp=1.5),
            ],
        )

        smoothed = EmaTemporalSmoother(settings).smooth(camera_path)
        raw_deltas = [
            math.hypot(
                camera_path.frames[index].center_x - camera_path.frames[index - 1].center_x,
                camera_path.frames[index].center_y - camera_path.frames[index - 1].center_y,
            )
            for index in range(1, len(camera_path.frames))
        ]
        smooth_deltas = [
            math.hypot(
                smoothed.frames[index].center_x - smoothed.frames[index - 1].center_x,
                smoothed.frames[index].center_y - smoothed.frames[index - 1].center_y,
            )
            for index in range(1, len(smoothed.frames))
        ]

        assert max(smooth_deltas) <= max(raw_deltas)

    def test_respects_scene_boundaries(self, settings: Settings) -> None:
        camera_path = CameraPath(
            source_width=1920,
            source_height=1080,
            target_aspect=1080 / 1920,
            frames=[
                _camera_frame(0, center_x=400.0, center_y=400.0, timestamp=0.0),
                _camera_frame(1, center_x=1400.0, center_y=650.0, timestamp=1.0),
            ],
        )
        scene_result = SceneDetectionResult(
            source_path="clip.mp4",
            duration_seconds=5.0,
            boundaries=[SceneBoundary(timestamp=1.0, confidence=0.9, boundary_type=SceneBoundaryType.CUT)],
            segments=[
                SceneSegment(index=0, start_seconds=0.0, end_seconds=1.0, duration_seconds=1.0),
                SceneSegment(index=1, start_seconds=1.0, end_seconds=5.0, duration_seconds=4.0),
            ],
        )

        smoothed = EmaTemporalSmoother(settings).smooth(camera_path, scene_result=scene_result)

        assert smoothed.frames[1].center_x == 1400.0
        assert smoothed.frames[1].center_y == 650.0


class TestTemporalSmoothingFactory:
    def test_factory_returns_ema_smoother(self, settings: Settings) -> None:
        assert get_temporal_smoother(settings).smoother_name == "ema"

    def test_unknown_smoother_raises(self) -> None:
        with pytest.raises(UnknownTemporalSmootherError):
            get_temporal_smoother(Settings(temporal_smoother="unknown"))

    def test_service_wrapper(self, settings: Settings) -> None:
        path = CameraPath(
            source_width=1920,
            source_height=1080,
            target_aspect=1080 / 1920,
            frames=[_camera_frame(0, center_x=700.0, center_y=500.0)],
        )
        service = TemporalSmoothingService(settings=settings)
        result = service.smooth(path)
        assert len(result.frames) == 1
        assert smooth_camera_path(path, settings=settings).frames[0].center_x == 700.0
