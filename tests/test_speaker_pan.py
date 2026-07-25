"""Tests for speaker-driven pan cropping."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.reframe.crop.speaker_pan import resolve_speaker_pan_center, smooth_pan_crop_frames
from app.reframe.models.crop import CropFrame
from app.reframe.models.faces import BoundingBox
from app.reframe.models.importance import FrameImportance, ImportanceScore
from app.reframe.models.speakers import FrameSpeakerConfidence
from app.reframe.models.tracking import FrameTracks, TrackedFace


def _face(track_id: str, x: float) -> TrackedFace:
    return TrackedFace(
        track_id=track_id,
        bounding_box=BoundingBox(x=x, y=100.0, width=120.0, height=150.0),
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


class TestSpeakerPan:
    def test_resolve_speaker_pan_center_uses_active_track(self) -> None:
        tracked = _frame(0, [_face("person_1", 400.0), _face("person_2", 1200.0)])
        speaker = FrameSpeakerConfidence(
            frame_number=0,
            timestamp=0.0,
            active_track_id="person_2",
            track_scores={"person_2": 0.9},
        )

        center_x, _center_y = resolve_speaker_pan_center(
            tracked,
            speaker,
            None,
            fallback_center_x=960.0,
            fallback_center_y=540.0,
            min_speaker_confidence=0.4,
        )

        assert center_x == pytest.approx(1260.0)

    def test_smooth_pan_crop_frames_reduces_jitter(self) -> None:
        frames = [
            CropFrame(frame_number=0, timestamp=0.0, x=100.0, y=50.0, width=200.0, height=360.0),
            CropFrame(frame_number=1, timestamp=0.5, x=108.0, y=50.0, width=200.0, height=360.0),
            CropFrame(frame_number=2, timestamp=1.0, x=92.0, y=50.0, width=200.0, height=360.0),
            CropFrame(frame_number=3, timestamp=1.5, x=140.0, y=50.0, width=200.0, height=360.0),
        ]
        settings = Settings(
            reframe_pan_smoothing_strength=0.1,
            reframe_pan_speaker_switch_smoothing=0.2,
            reframe_pan_deadband_pixels=4.0,
        )

        smoothed = smooth_pan_crop_frames(frames, settings=settings)

        assert len(smoothed) == len(frames)
        assert smoothed[-1].center_x > smoothed[0].center_x
        deltas = [
            abs(smoothed[index].center_x - smoothed[index - 1].center_x)
            for index in range(1, len(smoothed))
        ]
        raw_deltas = [abs(frames[index].center_x - frames[index - 1].center_x) for index in range(1, len(frames))]
        assert max(deltas) <= max(raw_deltas)
