"""Tests for reframe rendering."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.core.config import Settings
from app.core.exceptions import ReframeRenderError, UnknownReframeRendererError
from app.reframe.models.crop import CropFrame, CropPlan, CropSegment
from app.reframe.render.factory import get_reframe_renderer
from app.reframe.render.ffmpeg import FFmpegReframeRenderer
from app.reframe.render.filters import build_segment_blur_filter, build_segment_crop_filter
from app.reframe.render.service import ReframeRenderService, render_reframed_video


@pytest.fixture
def settings() -> Settings:
    return Settings(
        reframe_renderer="ffmpeg",
        reframe_render_fps=30.0,
        reframe_segment_merge_threshold=5.0,
        vertical_width=1080,
        vertical_height=1920,
        reframe_render_preset="fast",
        reframe_render_crf=23,
    )


@pytest.fixture
def crop_plan() -> CropPlan:
    frame = CropFrame(frame_number=0, timestamp=0.0, x=420, y=80, width=600, height=1066)
    return CropPlan(
        source_width=1920,
        source_height=1080,
        target_width=1080,
        target_height=1920,
        frames=[frame],
        segments=[CropSegment(start_time=0.0, end_time=2.0, crop=frame)],
    )


class TestRenderFilters:
    def test_build_segment_crop_filter(self, crop_plan: CropPlan) -> None:
        segment = crop_plan.segments[0]
        video_filter = build_segment_crop_filter(segment, target_width=1080, target_height=1920)
        assert "crop=600:1066:420:80" in video_filter
        assert "scale=1080:1920:flags=lanczos" in video_filter

    def test_build_segment_blur_filter(self, crop_plan: CropPlan) -> None:
        segment = crop_plan.segments[0]
        filter_complex = build_segment_blur_filter(
            segment,
            target_width=1080,
            target_height=1920,
            blur_strength=20,
        )
        assert "boxblur=20:5" in filter_complex
        assert "[vout]" in filter_complex


class TestFFmpegReframeRenderer:
    def test_render_single_segment(self, settings: Settings, crop_plan: CropPlan, tmp_path: Path) -> None:
        source = tmp_path / "source.mp4"
        output = tmp_path / "vertical.mp4"
        source.write_bytes(b"not-a-real-video")

        with (
            patch("app.reframe.render.ffmpeg.validate_source_video"),
            patch("app.reframe.render.ffmpeg.run_ffmpeg") as mock_ffmpeg,
        ):
            result = FFmpegReframeRenderer(settings).render(
                source,
                crop_plan,
                output,
                duration_seconds=2.0,
            )

        assert result.output_path == str(output)
        assert result.segment_count == 1
        cmd = mock_ffmpeg.call_args[0][0]
        assert "-vf" in cmd
        assert "crop=600:1066:420:80" in cmd[cmd.index("-vf") + 1]

    def test_render_empty_plan_raises(self, settings: Settings, tmp_path: Path) -> None:
        source = tmp_path / "source.mp4"
        source.write_bytes(b"x")
        empty_plan = CropPlan(
            source_width=1920,
            source_height=1080,
            target_width=1080,
            target_height=1920,
        )

        with (
            patch("app.reframe.render.ffmpeg.validate_source_video"),
            pytest.raises(ReframeRenderError, match="empty crop plan"),
        ):
            FFmpegReframeRenderer(settings).render(
                source,
                empty_plan,
                tmp_path / "out.mp4",
                duration_seconds=1.0,
            )


class TestRenderFactoryAndService:
    def test_factory_returns_ffmpeg_renderer(self, settings: Settings) -> None:
        assert get_reframe_renderer(settings).renderer_name == "ffmpeg"

    def test_unknown_renderer_raises(self) -> None:
        with pytest.raises(UnknownReframeRendererError):
            get_reframe_renderer(Settings(reframe_renderer="unknown"))

    def test_service_wrapper(self, settings: Settings, crop_plan: CropPlan, tmp_path: Path) -> None:
        source = tmp_path / "source.mp4"
        output = tmp_path / "vertical.mp4"
        source.write_bytes(b"x")

        with (
            patch("app.reframe.render.service.probe_duration", return_value=2.0),
            patch("app.reframe.render.ffmpeg.validate_source_video"),
            patch("app.reframe.render.ffmpeg.run_ffmpeg"),
            patch("app.video.ffmpeg.ensure_ffmpeg_available"),
        ):
            service = ReframeRenderService(settings=settings)
            result = service.render(source, crop_plan, output)

        assert result.width == 1080
        with (
            patch("app.reframe.render.service.probe_duration", return_value=2.0),
            patch("app.reframe.render.ffmpeg.validate_source_video"),
            patch("app.reframe.render.ffmpeg.run_ffmpeg"),
            patch("app.video.ffmpeg.ensure_ffmpeg_available"),
        ):
            assert render_reframed_video(
                source,
                crop_plan,
                output,
                settings=settings,
                duration_seconds=2.0,
            ).height == 1920
