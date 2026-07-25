"""Tests for clip segment helpers and reframe export."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.models.export import ExtractedClip
from app.models.transcript import TranscriptSegment
from app.reframe.export.vertical import ClipReframer, REFRAME_CROP_MODE
from app.utils.clip_segments import format_timestamp, segments_for_clip_window


class TestClipSegments:
    def test_segments_for_clip_window_relative(self) -> None:
        segments = [
            TranscriptSegment(start="00:00:10", seconds=10.0, speaker="A", text="Hello."),
            TranscriptSegment(start="00:00:20", seconds=20.0, speaker="B", text="World."),
            TranscriptSegment(start="00:01:00", seconds=60.0, speaker="C", text="Outside."),
        ]

        clip_segments = segments_for_clip_window(
            segments,
            clip_start_seconds=10.0,
            clip_end_seconds=30.0,
            relative_to_clip=True,
        )

        assert len(clip_segments) == 2
        assert clip_segments[0].seconds == 0.0
        assert clip_segments[1].seconds == 10.0

    def test_format_timestamp(self) -> None:
        assert format_timestamp(65.0) == "00:01:05"


class TestClipReframer:
    def test_reframe_to_vertical_uses_pipeline(self, tmp_path: Path) -> None:
        source = tmp_path / "clip1.mp4"
        source.write_bytes(b"video")
        extracted = ExtractedClip(
            index=1,
            source_path=str(source),
            output_path=str(source),
            start="00:00:10",
            end="00:00:50",
            start_seconds=10.0,
            end_seconds=50.0,
            duration_seconds=40.0,
        )
        settings = Settings(vertical_width=1080, vertical_height=1920)

        mock_pipeline = MagicMock()
        mock_pipeline.process_video.return_value = MagicMock(
            tracking=MagicMock(frames=[]),
            crop_plan=MagicMock(frames=[MagicMock()]),
            smoothed_path=MagicMock(frames=[]),
        )
        mock_pipeline.render_service.render.return_value = MagicMock()

        with patch("app.reframe.export.vertical.ReframePipelineService", return_value=mock_pipeline):
            results = ClipReframer(settings=settings).reframe(
                [extracted],
                output_dir=tmp_path,
                transcript_segments=[
                    TranscriptSegment(start="00:00:00", seconds=0.0, speaker="A", text="Hi."),
                ],
            )

        assert len(results) == 1
        assert results[0].crop_mode == REFRAME_CROP_MODE
        mock_pipeline.process_video.assert_called_once()
        mock_pipeline.render_service.render.assert_called_once()
