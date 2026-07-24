"""Tests for vertical video cropping."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.core.exceptions import VerticalCropError
from app.models.export import ExtractedClip
from app.video.cropper import CropMode, VerticalCropper, crop_to_vertical
from app.video.ffmpeg import probe_dimensions


@pytest.fixture
def settings() -> Settings:
    return Settings(
        output_dir="output",
        vertical_width=1080,
        vertical_height=1920,
        vertical_blur_strength=20,
    )


@pytest.fixture
def source_clip(tmp_path: Path) -> Path:
    clip = tmp_path / "clip1.mp4"
    clip.write_bytes(b"fake-video")
    return clip


@pytest.fixture
def extracted_clip(source_clip: Path) -> ExtractedClip:
    return ExtractedClip(
        index=1,
        source_path="/videos/game.mp4",
        output_path=str(source_clip),
        start="00:00:10",
        end="00:00:50",
        start_seconds=10.0,
        end_seconds=50.0,
        duration_seconds=40.0,
        reencoded=False,
    )


@pytest.fixture
def mock_ffmpeg_stack() -> MagicMock:
    with (
        patch("app.video.ffmpeg.shutil.which", return_value="/usr/bin/ffmpeg"),
        patch("app.video.ffmpeg.subprocess.run") as mock_run,
        patch("app.video.cropper.probe_dimensions", return_value=(1920, 1080)),
    ):
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
        yield mock_run


class TestProbeDimensions:
    def test_parses_dimensions(self, source_clip: Path) -> None:
        with patch("app.video.ffmpeg.shutil.which", return_value="/usr/bin/ffprobe"):
            with patch("app.video.ffmpeg.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(stdout="1920x1080\n", returncode=0)
                width, height = probe_dimensions(source_clip)
        assert width == 1920
        assert height == 1080


class TestVerticalCropper:
    def test_center_crop_mode(
        self,
        source_clip: Path,
        tmp_path: Path,
        settings: Settings,
        mock_ffmpeg_stack: MagicMock,
    ) -> None:
        results = crop_to_vertical(
            [source_clip],
            output_dir=tmp_path / "vertical",
            settings=settings,
            blurred_background=False,
        )

        assert len(results) == 1
        assert results[0].width == 1080
        assert results[0].height == 1920
        assert results[0].crop_mode == "center_crop"
        assert results[0].blurred_background is False
        assert results[0].output_path.endswith("clip1_vertical.mp4")

        cmd = mock_ffmpeg_stack.call_args[0][0]
        assert "-vf" in cmd
        assert "crop=" in " ".join(cmd)

    def test_blur_background_mode(
        self,
        source_clip: Path,
        tmp_path: Path,
        settings: Settings,
        mock_ffmpeg_stack: MagicMock,
    ) -> None:
        results = crop_to_vertical(
            [source_clip],
            output_dir=tmp_path / "vertical",
            settings=settings,
            blurred_background=True,
        )

        assert results[0].crop_mode == "blur_background"
        assert results[0].blurred_background is True

        cmd = mock_ffmpeg_stack.call_args[0][0]
        assert "-filter_complex" in cmd
        assert "boxblur" in " ".join(cmd)

    def test_accepts_extracted_clip(
        self,
        extracted_clip: ExtractedClip,
        tmp_path: Path,
        settings: Settings,
        mock_ffmpeg_stack: MagicMock,
    ) -> None:
        results = crop_to_vertical(
            [extracted_clip],
            output_dir=tmp_path / "vertical",
            settings=settings,
        )
        assert results[0].source_path == extracted_clip.output_path

    def test_crops_multiple_clips(
        self,
        tmp_path: Path,
        settings: Settings,
        mock_ffmpeg_stack: MagicMock,
    ) -> None:
        clips = []
        for i in range(1, 4):
            path = tmp_path / f"clip{i}.mp4"
            path.write_bytes(b"video")
            clips.append(path)

        results = crop_to_vertical(clips, output_dir=tmp_path / "vertical", settings=settings)
        assert len(results) == 3
        assert results[2].output_path.endswith("clip3_vertical.mp4")

    def test_explicit_mode_override(
        self,
        source_clip: Path,
        tmp_path: Path,
        settings: Settings,
        mock_ffmpeg_stack: MagicMock,
    ) -> None:
        results = crop_to_vertical(
            [source_clip],
            output_dir=tmp_path / "vertical",
            settings=settings,
            mode=CropMode.BLUR_BACKGROUND,
        )
        assert results[0].blurred_background is True

    def test_custom_dimensions(
        self,
        source_clip: Path,
        tmp_path: Path,
        settings: Settings,
        mock_ffmpeg_stack: MagicMock,
    ) -> None:
        results = crop_to_vertical(
            [source_clip],
            output_dir=tmp_path / "vertical",
            settings=settings,
            width=720,
            height=1280,
        )
        assert results[0].width == 720
        assert results[0].height == 1280

    def test_empty_clips_raises(self) -> None:
        with pytest.raises(VerticalCropError, match="empty clip list"):
            crop_to_vertical([])

    def test_missing_source_raises(
        self,
        tmp_path: Path,
        settings: Settings,
    ) -> None:
        missing = tmp_path / "missing.mp4"
        with pytest.raises(VerticalCropError, match="not found"):
            crop_to_vertical([missing], settings=settings)

    def test_creates_output_directory(
        self,
        source_clip: Path,
        tmp_path: Path,
        settings: Settings,
        mock_ffmpeg_stack: MagicMock,
    ) -> None:
        out = tmp_path / "nested" / "vertical"
        crop_to_vertical([source_clip], output_dir=out, settings=settings)
        assert out.exists()

    def test_ffmpeg_failure_raises(
        self,
        source_clip: Path,
        tmp_path: Path,
        settings: Settings,
    ) -> None:
        import subprocess

        with (
            patch("app.video.ffmpeg.shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("app.video.cropper.probe_dimensions", return_value=(1920, 1080)),
            patch("app.video.ffmpeg.subprocess.run") as mock_run,
        ):
            mock_run.side_effect = subprocess.CalledProcessError(1, "ffmpeg", stderr="filter error")
            with pytest.raises(Exception, match="ffmpeg command failed"):
                VerticalCropper(settings=settings).crop(
                    [source_clip],
                    output_dir=tmp_path / "vertical",
                )
