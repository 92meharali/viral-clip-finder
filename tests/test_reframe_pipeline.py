"""Tests for the end-to-end reframe pipeline."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.core.config import Settings
from app.reframe.models.camera import CameraPath, VirtualCameraFrame
from app.reframe.models.importance import FrameImportance, ImportanceFactor, ImportanceScore, ImportanceScoringResult
from app.reframe.models.tracking import FrameTracks, TrackedFace, TrackingResult
from app.reframe.pipeline.service import ReframePipelineService
from app.reframe.models.faces import BoundingBox


def _tracked_face(track_id: str, x: float, y: float) -> TrackedFace:
    return TrackedFace(
        track_id=track_id,
        bounding_box=BoundingBox(x=x, y=y, width=120, height=150),
        detection_confidence=0.95,
    )


def _frame(frame_number: int, faces: list[TrackedFace]) -> FrameTracks:
    return FrameTracks(
        frame_number=frame_number,
        timestamp=float(frame_number),
        image_width=1920,
        image_height=1080,
        faces=faces,
        active_track_ids=[face.track_id for face in faces],
    )


@pytest.fixture
def settings() -> Settings:
    return Settings(
        composition_planner="heuristic",
        camera_planner="pursuit",
        temporal_smoother="ema",
        crop_generator="safe",
        reframe_renderer="ffmpeg",
    )


class TestReframePipelineService:
    def test_process_tracking_returns_crop_plan(self, settings: Settings) -> None:
        tracking = TrackingResult(
            frames=[
                _frame(0, [_tracked_face("person_1", 860, 420)]),
                _frame(1, [_tracked_face("person_1", 865, 422)]),
            ],
            tracks={},
        )
        importance = ImportanceScoringResult(
            frames=[
                FrameImportance(
                    frame_number=0,
                    timestamp=0.0,
                    scores=[
                        ImportanceScore(
                            track_id="person_1",
                            score=0.9,
                            reasoning="currently speaking",
                            factors=[ImportanceFactor(factor_type="currently_speaking", score=0.9)],
                        )
                    ],
                ),
                FrameImportance(
                    frame_number=1,
                    timestamp=1.0,
                    scores=[
                        ImportanceScore(
                            track_id="person_1",
                            score=0.88,
                            reasoning="currently speaking",
                            factors=[ImportanceFactor(factor_type="currently_speaking", score=0.88)],
                        )
                    ],
                ),
            ]
        )

        service = ReframePipelineService(settings=settings)
        result = service.process_tracking(tracking, importance)

        assert result.composition.frames
        assert result.camera_path.frames
        assert result.smoothed_path.frames
        assert result.crop_plan.frames
        assert len(result.smoothed_path.frames) == len(result.camera_path.frames)

    def test_render_video_invokes_renderer(self, settings: Settings, tmp_path) -> None:
        source = tmp_path / "source.mp4"
        output = tmp_path / "vertical.mp4"
        source.write_bytes(b"x")

        service = ReframePipelineService(settings=settings)
        with (
            patch.object(service, "process_video") as mock_process,
            patch.object(service.render_service, "render") as mock_render,
        ):
            mock_process.return_value = type(
                "PipelineResult",
                (),
                {
                    "crop_plan": type(
                        "CropPlan",
                        (),
                        {"frames": [object()], "segments": [object()]},
                    )(),
                },
            )()
            mock_render.return_value = type(
                "RenderResult",
                (),
                {
                    "source_path": str(source),
                    "output_path": str(output),
                    "width": 1080,
                    "height": 1920,
                    "segment_count": 1,
                    "crop_keyframe_count": 1,
                    "blurred_background": False,
                    "render_fps": 30.0,
                },
            )()

            result = service.render_video(source, output)

        assert result.render_result is not None
        mock_render.assert_called_once()
