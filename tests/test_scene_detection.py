"""Tests for scene detection."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.core.exceptions import UnknownSceneDetectorError
from app.reframe.models.faces import VideoFrame
from app.reframe.models.scenes import SceneBoundary, SceneBoundaryType
from app.reframe.scenes.factory import get_scene_detector
from app.reframe.scenes.ffmpeg import FFmpegSceneDetector
from app.reframe.scenes.histogram import HistogramSceneDetector, _histogram_difference
from app.reframe.scenes.segments import build_scene_segments, merge_close_boundaries
from app.reframe.scenes.service import SceneDetectionService


@pytest.fixture
def settings() -> Settings:
    return Settings(
        scene_detector="ffmpeg",
        scene_detection_threshold=0.35,
        scene_min_gap_seconds=0.5,
        scene_extraction_fps=4.0,
        ffmpeg_path="ffmpeg",
        ffprobe_path="ffprobe",
    )


class TestSceneSegments:
    def test_build_segments_from_boundaries(self) -> None:
        boundaries = [
            SceneBoundary(timestamp=10.0, confidence=0.8),
            SceneBoundary(timestamp=25.0, confidence=0.7),
        ]
        segments = build_scene_segments(boundaries, 40.0)

        assert len(segments) == 3
        assert segments[0].start_seconds == 0.0
        assert segments[0].end_seconds == 10.0
        assert segments[2].end_seconds == 40.0

    def test_merge_close_boundaries_keeps_higher_confidence(self) -> None:
        boundaries = [
            SceneBoundary(timestamp=10.0, confidence=0.4),
            SceneBoundary(timestamp=10.3, confidence=0.9),
        ]
        merged = merge_close_boundaries(boundaries, min_gap_seconds=0.5)

        assert len(merged) == 1
        assert merged[0].confidence == 0.9


class TestHistogramDifference:
    def test_identical_histograms_have_zero_difference(self) -> None:
        hist = [0.25, 0.25, 0.25, 0.25]
        assert _histogram_difference(hist, hist) == 0.0

    def test_disjoint_histograms_have_high_difference(self) -> None:
        left = [1.0, 0.0, 0.0, 0.0]
        right = [0.0, 0.0, 0.0, 1.0]
        assert _histogram_difference(left, right) == 1.0


class TestHistogramSceneDetector:
    def test_detects_boundary_between_different_frames(
        self,
        settings: Settings,
        tmp_path: Path,
    ) -> None:
        pytest.importorskip("PIL")
        from PIL import Image

        dark = tmp_path / "dark.jpg"
        bright = tmp_path / "bright.jpg"
        Image.new("L", (64, 64), color=10).save(dark)
        Image.new("L", (64, 64), color=245).save(bright)

        frames = [
            VideoFrame(
                frame_number=0,
                timestamp=0.0,
                image_path=str(dark),
                width=64,
                height=64,
            ),
            VideoFrame(
                frame_number=1,
                timestamp=0.5,
                image_path=str(bright),
                width=64,
                height=64,
            ),
        ]

        detector = HistogramSceneDetector(settings)
        boundaries = detector.detect_frames(frames)

        assert len(boundaries) == 1
        assert boundaries[0].timestamp == 0.5


class TestFFmpegSceneDetector:
    @patch("app.reframe.scenes.ffmpeg.probe_duration", return_value=30.0)
    @patch("app.reframe.scenes.ffmpeg.validate_source_video")
    @patch("app.reframe.scenes.ffmpeg.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("app.reframe.scenes.ffmpeg.subprocess.run")
    def test_parses_showinfo_boundaries(
        self,
        mock_run: MagicMock,
        _mock_which: MagicMock,
        _mock_validate: MagicMock,
        _mock_duration: MagicMock,
        settings: Settings,
        tmp_path: Path,
    ) -> None:
        video = tmp_path / "clip.mp4"
        video.write_bytes(b"video")

        mock_run.return_value = MagicMock(
            returncode=0,
            stderr=(
                "[Parsed_showinfo_0 @ 0x1] n:   0 pts:  12345 pts_time:5.000 scene:0.42\n"
                "[Parsed_showinfo_0 @ 0x1] n:   1 pts:  24680 pts_time:12.500 scene:0.51\n"
            ),
        )

        result = FFmpegSceneDetector(settings).detect(video)

        assert result.scene_count == 3
        assert len(result.boundaries) == 2
        assert result.boundaries[0].timestamp == 5.0
        assert result.boundaries[1].boundary_type == SceneBoundaryType.CUT
        assert result.segment_at(6.0) is not None
        assert result.is_near_boundary(5.0, tolerance=0.1)


class TestSceneDetectorFactory:
    def test_creates_ffmpeg_detector(self, settings: Settings) -> None:
        assert get_scene_detector(settings).detector_name == "ffmpeg"

    def test_unknown_detector_raises(self, settings: Settings) -> None:
        settings = settings.model_copy(update={"scene_detector": "pyscenedetect"})
        with pytest.raises(UnknownSceneDetectorError, match="pyscenedetect"):
            get_scene_detector(settings)


class TestSceneDetectionService:
    def test_detect_delegates_to_detector(self, settings: Settings, tmp_path: Path) -> None:
        video = tmp_path / "clip.mp4"
        video.write_bytes(b"video")
        detector = MagicMock()
        detector.detector_name = "mock"
        detector.detect.return_value = MagicMock(scene_count=2)

        result = SceneDetectionService(settings, detector=detector).detect(video)

        detector.detect.assert_called_once()
        assert result.scene_count == 2
