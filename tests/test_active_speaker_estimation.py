"""Tests for active speaker estimation."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.exceptions import UnknownSpeakerEstimatorError
from app.models.transcript import TranscriptSegment
from app.reframe.models.faces import BoundingBox, FaceLandmarks
from app.reframe.models.tracking import FrameTracks, TrackedFace, TrackingResult, TrackSummary
from app.reframe.speakers.factory import get_speaker_estimator
from app.reframe.speakers.fusion import FusionActiveSpeakerEstimator
from app.reframe.speakers.service import ActiveSpeakerEstimationService, estimate_active_speakers
from app.reframe.speakers.signals.audio import AudioEnergySignal
from app.reframe.speakers.signals.mouth import MouthMovementSignal
from app.reframe.speakers.signals.transcript import TranscriptTimingSignal


def _tracked_face(
    track_id: str,
    x: float,
    y: float,
    *,
    mouth: tuple[float, float] | None = None,
    left_eye: tuple[float, float] | None = None,
    right_eye: tuple[float, float] | None = None,
) -> TrackedFace:
    landmarks = None
    if mouth or left_eye or right_eye:
        landmarks = FaceLandmarks(
            left_eye=left_eye,
            right_eye=right_eye,
            mouth=mouth,
        )
    return TrackedFace(
        track_id=track_id,
        bounding_box=BoundingBox(x=x, y=y, width=120, height=150),
        detection_confidence=0.95,
        landmarks=landmarks,
    )


def _frame(
    frame_number: int,
    faces: list[TrackedFace],
    *,
    timestamp: float | None = None,
) -> FrameTracks:
    return FrameTracks(
        frame_number=frame_number,
        timestamp=timestamp if timestamp is not None else float(frame_number),
        image_width=1920,
        image_height=1080,
        faces=faces,
        active_track_ids=[face.track_id for face in faces],
    )


@pytest.fixture
def settings() -> Settings:
    return Settings(
        speaker_estimator="fusion",
        speaker_weight_transcript=0.25,
        speaker_weight_mouth=0.45,
        speaker_weight_orientation=0.15,
        speaker_weight_audio=0.15,
        speaker_min_confidence=0.35,
        speaker_min_segment_seconds=0.2,
    )


class TestTranscriptTimingSignal:
    def test_single_visible_face_during_dialogue_scores_high(self) -> None:
        tracking = TrackingResult(
            frames=[
                _frame(
                    0,
                    [_tracked_face("person_1", 400, 200)],
                    timestamp=10.0,
                )
            ],
            tracks={
                "person_1": TrackSummary(
                    track_id="person_1",
                    first_frame=0,
                    last_frame=0,
                    first_timestamp=10.0,
                    last_timestamp=10.0,
                    total_detections=1,
                )
            },
        )
        segments = [
            TranscriptSegment(start="00:00:10", seconds=10.0, speaker="Host", text="Hello everyone."),
        ]

        scores = TranscriptTimingSignal().score_frames(
            tracking,
            transcript_segments=segments,
            video_duration=30.0,
        )

        assert scores[0]["person_1"] == 1.0

    def test_multiple_faces_receive_neutral_score(self) -> None:
        tracking = TrackingResult(
            frames=[
                _frame(
                    0,
                    [
                        _tracked_face("person_1", 300, 200),
                        _tracked_face("person_2", 900, 200),
                    ],
                    timestamp=5.0,
                )
            ],
            tracks={},
        )
        segments = [
            TranscriptSegment(start="00:00:05", seconds=5.0, speaker="A", text="Debate time."),
        ]

        scores = TranscriptTimingSignal().score_frames(
            tracking,
            transcript_segments=segments,
            video_duration=20.0,
        )

        assert scores[0]["person_1"] == 0.5
        assert scores[0]["person_2"] == 0.5


class TestMouthMovementSignal:
    def test_moving_mouth_scores_higher_than_static_face(self) -> None:
        tracking = TrackingResult(
            frames=[
                _frame(
                    0,
                    [
                        _tracked_face("speaker", 300, 200, mouth=(360.0, 290.0)),
                        _tracked_face("listener", 900, 200, mouth=(960.0, 290.0)),
                    ],
                    timestamp=0.0,
                ),
                _frame(
                    1,
                    [
                        _tracked_face("speaker", 300, 200, mouth=(360.0, 305.0)),
                        _tracked_face("listener", 900, 200, mouth=(960.0, 291.0)),
                    ],
                    timestamp=0.5,
                ),
            ],
            tracks={},
        )

        scores = MouthMovementSignal().score_frames(tracking)

        assert scores[1]["speaker"] > scores[1]["listener"]
        assert scores[1]["speaker"] == 1.0


class TestFusionActiveSpeakerEstimator:
    def test_selects_mouth_mover_during_dialogue(self, settings: Settings) -> None:
        tracking = TrackingResult(
            frames=[
                _frame(
                    0,
                    [
                        _tracked_face("person_1", 300, 200, mouth=(360.0, 290.0)),
                        _tracked_face("person_2", 900, 200, mouth=(960.0, 290.0)),
                    ],
                    timestamp=10.0,
                ),
                _frame(
                    1,
                    [
                        _tracked_face("person_1", 300, 200, mouth=(360.0, 308.0)),
                        _tracked_face("person_2", 900, 200, mouth=(960.0, 291.0)),
                    ],
                    timestamp=10.5,
                ),
                _frame(
                    2,
                    [
                        _tracked_face("person_1", 300, 200, mouth=(360.0, 292.0)),
                        _tracked_face("person_2", 900, 200, mouth=(960.0, 292.0)),
                    ],
                    timestamp=11.0,
                ),
            ],
            tracks={},
        )
        segments = [
            TranscriptSegment(start="00:00:10", seconds=10.0, speaker="A", text="I disagree."),
        ]
        audio = AudioEnergySignal(
            energy_cache=[(10.0, 0.9), (10.5, 0.95), (11.0, 0.8)],
        )
        estimator = FusionActiveSpeakerEstimator(
            settings,
            audio_signal=audio,
        )

        result = estimator.estimate(
            tracking,
            transcript_segments=segments,
            video_duration=30.0,
        )

        assert result.segment_count >= 1
        assert result.segments[0].track_id == "person_1"
        assert result.frames[1].active_track_id == "person_1"
        assert result.frames[1].track_scores["person_1"] > result.frames[1].track_scores["person_2"]

    def test_merges_consecutive_frames_into_one_segment(self, settings: Settings) -> None:
        tracking = TrackingResult(
            frames=[
                _frame(
                    index,
                    [_tracked_face("person_1", 400, 200, mouth=(460.0, 290.0 + index))],
                    timestamp=1.0 + index * 0.5,
                )
                for index in range(4)
            ],
            tracks={},
        )
        segments = [
            TranscriptSegment(start="00:00:01", seconds=1.0, speaker="Host", text="Talking."),
        ]
        estimator = FusionActiveSpeakerEstimator(
            settings,
            audio_signal=AudioEnergySignal(energy_cache=[(1.0, 0.8), (2.5, 0.7)]),
        )

        result = estimator.estimate(
            tracking,
            transcript_segments=segments,
            video_duration=10.0,
        )

        assert result.segment_count == 1
        assert result.segments[0].track_id == "person_1"
        assert result.segments[0].start_time == pytest.approx(1.0)
        assert result.segments[0].end_time == pytest.approx(2.5)

    def test_speaker_switch_produces_two_segments(self, settings: Settings) -> None:
        frames = []
        for index in range(3):
            frames.append(
                _frame(
                    index,
                    [_tracked_face("person_1", 300, 200, mouth=(360.0, 290.0 + index * 8))],
                    timestamp=float(index),
                )
            )
        for index in range(3, 6):
            frames.append(
                _frame(
                    index,
                    [_tracked_face("person_2", 900, 200, mouth=(960.0, 290.0 + (index - 3) * 8))],
                    timestamp=float(index),
                )
            )

        tracking = TrackingResult(frames=frames, tracks={})
        segments = [
            TranscriptSegment(start="00:00:00", seconds=0.0, speaker="A", text="First."),
            TranscriptSegment(start="00:00:03", seconds=3.0, speaker="B", text="Reply."),
        ]
        estimator = FusionActiveSpeakerEstimator(
            settings,
            audio_signal=AudioEnergySignal(
                energy_cache=[(0.0, 0.8), (1.0, 0.8), (2.0, 0.8), (3.0, 0.8), (4.0, 0.8), (5.0, 0.8)],
            ),
        )

        result = estimator.estimate(
            tracking,
            transcript_segments=segments,
            video_duration=10.0,
        )

        assert result.segment_count == 2
        assert result.segments[0].track_id == "person_1"
        assert result.segments[1].track_id == "person_2"


class TestSpeakerFactoryAndService:
    def test_factory_returns_fusion_estimator(self, settings: Settings) -> None:
        estimator = get_speaker_estimator(settings)
        assert estimator.estimator_name == "fusion"

    def test_unknown_estimator_raises(self) -> None:
        with pytest.raises(UnknownSpeakerEstimatorError):
            get_speaker_estimator(Settings(speaker_estimator="unknown"))

    def test_service_estimate_wrapper(self, settings: Settings) -> None:
        tracking = TrackingResult(
            frames=[
                _frame(
                    0,
                    [_tracked_face("person_1", 400, 200, mouth=(460.0, 290.0))],
                    timestamp=0.0,
                ),
                _frame(
                    1,
                    [_tracked_face("person_1", 400, 200, mouth=(460.0, 305.0))],
                    timestamp=0.5,
                ),
            ],
            tracks={},
        )
        service = ActiveSpeakerEstimationService(
            settings=settings,
            estimator=FusionActiveSpeakerEstimator(
                settings,
                audio_signal=AudioEnergySignal(energy_cache=[(0.0, 0.8), (0.5, 0.8)]),
            ),
        )

        result = service.estimate(
            tracking,
            transcript_segments=[
                TranscriptSegment(start="00:00:00", seconds=0.0, speaker="Host", text="Hi."),
            ],
            video_duration=5.0,
        )

        assert result.segment_count == 1
        assert result.segments[0].track_id == "person_1"

        convenience_result = estimate_active_speakers(
            tracking,
            settings=settings,
            transcript_segments=[
                TranscriptSegment(start="00:00:00", seconds=0.0, speaker="Host", text="Hi."),
            ],
            video_duration=5.0,
        )
        assert convenience_result.segment_count == 1
