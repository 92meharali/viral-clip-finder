"""Tests for FFmpeg utilities and video cutting."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.core.exceptions import VideoCutError
from app.models.clip import ViralClip
from app.video.cutter import VideoCutter, cut_clips
from app.video.ffmpeg import (
    ensure_ffmpeg_available,
    probe_duration,
    run_ffmpeg,
    validate_source_video,
)


def _make_clip(
    *,
    start_seconds: float = 10.0,
    end_seconds: float = 50.0,
    duration_seconds: float = 40.0,
) -> ViralClip:
    return ViralClip(
        start="00:00:10",
        end="00:00:50",
        reason="Test",
        viral_score=8.0,
        emotion="betrayal",
        hook="Test hook",
        summary="Test summary",
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        duration_seconds=duration_seconds,
    )


@pytest.fixture
def settings() -> Settings:
    return Settings(output_dir="output")


@pytest.fixture
def source_video(tmp_path: Path) -> Path:
    video = tmp_path / "source.mp4"
    video.write_bytes(b"fake-video-content")
    return video


@pytest.fixture
def mock_ffmpeg() -> MagicMock:
    with patch("app.video.ffmpeg.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="120.5\n", stderr="", returncode=0)
        yield mock_run


@pytest.fixture
def mock_which() -> MagicMock:
    with patch("app.video.ffmpeg.shutil.which", return_value="/usr/bin/ffmpeg"):
        yield


class TestValidateSourceVideo:
    def test_valid_mp4(self, source_video: Path) -> None:
        validate_source_video(source_video)

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(VideoCutError, match="not found"):
            validate_source_video(tmp_path / "missing.mp4")

    def test_unsupported_format_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "video.avi"
        bad.write_bytes(b"data")
        with pytest.raises(VideoCutError, match="Unsupported"):
            validate_source_video(bad)

    def test_supports_mov_and_mkv(self, tmp_path: Path) -> None:
        for ext in (".mov", ".mkv"):
            path = tmp_path / f"video{ext}"
            path.write_bytes(b"data")
            validate_source_video(path)


class TestProbeDuration:
    def test_returns_duration(
        self,
        source_video: Path,
        mock_ffmpeg: MagicMock,
        mock_which: MagicMock,
    ) -> None:
        duration = probe_duration(source_video)
        assert duration == 120.5

    def test_invalid_duration_raises(
        self,
        source_video: Path,
        mock_which: MagicMock,
    ) -> None:
        with patch("app.video.ffmpeg.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="invalid", stderr="", returncode=0)
            with pytest.raises(VideoCutError, match="Invalid duration"):
                probe_duration(source_video)


class TestEnsureFfmpeg:
    def test_raises_when_missing(self, settings: Settings) -> None:
        with patch("app.video.ffmpeg.shutil.which", return_value=None):
            with pytest.raises(VideoCutError, match="ffmpeg not found"):
                ensure_ffmpeg_available(settings)

    def test_passes_when_available(self, settings: Settings, mock_which: MagicMock) -> None:
        ensure_ffmpeg_available(settings)


class TestRunFfmpeg:
    def test_runs_command(self, mock_ffmpeg: MagicMock, mock_which: MagicMock) -> None:
        run_ffmpeg(["-version"])
        assert mock_ffmpeg.called
        cmd = mock_ffmpeg.call_args[0][0]
        assert cmd[0] == "ffmpeg"

    def test_raises_on_failure(self, mock_which: MagicMock) -> None:
        import subprocess

        with patch("app.video.ffmpeg.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "ffmpeg", stderr="codec error")
            with pytest.raises(VideoCutError, match="ffmpeg command failed"):
                run_ffmpeg(["-i", "input.mp4"])


class TestVideoCutter:
    def test_cuts_clips_with_stream_copy(
        self,
        source_video: Path,
        tmp_path: Path,
        settings: Settings,
        mock_which: MagicMock,
    ) -> None:
        with patch("app.video.ffmpeg.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="300.0\n", stderr="", returncode=0)

            cutter = VideoCutter(settings=settings)
            clips = [
                _make_clip(),
                _make_clip(start_seconds=60.0, end_seconds=100.0, duration_seconds=40.0),
            ]
            extracted = cutter.cut(source_video, clips, output_dir=tmp_path / "clips")

        assert len(extracted) == 2
        assert extracted[0].output_path.endswith("clip1.mp4")
        assert extracted[1].output_path.endswith("clip2.mp4")
        assert extracted[0].reencoded is False

        ffmpeg_calls = [call[0][0] for call in mock_run.call_args_list]
        cut_commands = [cmd for cmd in ffmpeg_calls if "-c" in cmd]
        assert any("copy" in cmd for cmd in cut_commands)

    def test_falls_back_to_reencode(
        self,
        source_video: Path,
        tmp_path: Path,
        settings: Settings,
        mock_which: MagicMock,
    ) -> None:
        import subprocess

        call_count = 0

        def side_effect(cmd: list[str], **kwargs: object) -> MagicMock:
            nonlocal call_count
            if cmd[0] == "ffprobe":
                return MagicMock(stdout="300.0\n", stderr="", returncode=0)
            call_count += 1
            if "-c" in cmd and "copy" in cmd:
                raise subprocess.CalledProcessError(1, "ffmpeg", stderr="copy failed")
            return MagicMock(stdout="", stderr="", returncode=0)

        with patch("app.video.ffmpeg.subprocess.run", side_effect=side_effect):
            extracted = cut_clips(
                source_video,
                [_make_clip()],
                output_dir=tmp_path / "clips",
                settings=settings,
            )

        assert len(extracted) == 1
        assert extracted[0].reencoded is True

    def test_empty_clips_raises(self, source_video: Path) -> None:
        with pytest.raises(VideoCutError, match="empty clip list"):
            cut_clips(source_video, [])

    def test_skips_clips_beyond_duration(
        self,
        source_video: Path,
        tmp_path: Path,
        settings: Settings,
        mock_which: MagicMock,
    ) -> None:
        with patch("app.video.ffmpeg.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="50.0\n", stderr="", returncode=0)

            valid = _make_clip(start_seconds=5.0, end_seconds=30.0, duration_seconds=25.0)
            invalid = _make_clip(start_seconds=40.0, end_seconds=80.0, duration_seconds=40.0)
            extracted = cut_clips(
                source_video,
                [invalid, valid],
                output_dir=tmp_path / "clips",
                settings=settings,
            )

        assert len(extracted) == 1
        assert extracted[0].index == 1
        assert extracted[0].start_seconds == 5.0

    def test_all_clips_invalid_raises(
        self,
        source_video: Path,
        tmp_path: Path,
        settings: Settings,
        mock_which: MagicMock,
    ) -> None:
        with patch("app.video.ffmpeg.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="10.0\n", stderr="", returncode=0)

            clip = _make_clip(start_seconds=20.0, end_seconds=50.0, duration_seconds=30.0)
            with pytest.raises(VideoCutError, match="No clips were extracted"):
                cut_clips(source_video, [clip], output_dir=tmp_path / "clips", settings=settings)

    def test_creates_output_directory(
        self,
        source_video: Path,
        tmp_path: Path,
        settings: Settings,
        mock_which: MagicMock,
    ) -> None:
        out = tmp_path / "nested" / "clips"
        with patch("app.video.ffmpeg.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="300.0\n", stderr="", returncode=0)
            cut_clips(source_video, [_make_clip()], output_dir=out, settings=settings)

        assert out.exists()
