"""Tests for subtitle burn-in."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.core.config import Settings
from app.core.exceptions import SubtitleError
from app.models.subtitle import SubtitleFile, SubtitlePosition, SubtitleStyle
from app.video.subtitle_burner import (
    SubtitleBurner,
    build_force_style,
    color_to_ass,
    default_style_from_settings,
    escape_subtitles_path,
)


class TestColorToAss:
    def test_named_white(self) -> None:
        assert color_to_ass("white") == "&H00FFFFFF"

    def test_hex_color(self) -> None:
        assert color_to_ass("#FF0000") == "&H000000FF"

    def test_invalid_raises(self) -> None:
        with pytest.raises(SubtitleError, match="Unsupported"):
            color_to_ass("not-a-color")


class TestBuildForceStyle:
    def test_includes_all_properties(self) -> None:
        style = SubtitleStyle(
            font="Helvetica",
            size=32,
            outline=3,
            color="yellow",
            position=SubtitlePosition.TOP,
        )
        result = build_force_style(style)
        assert "FontName=Helvetica" in result
        assert "FontSize=32" in result
        assert "Outline=3" in result
        assert "Alignment=8" in result


class TestEscapeSubtitlesPath:
    def test_escapes_colons(self, tmp_path: Path) -> None:
        path = tmp_path / "clip1.srt"
        escaped = escape_subtitles_path(path)
        assert "\\:" not in escaped or "/" in escaped


class TestDefaultStyleFromSettings:
    def test_reads_settings(self) -> None:
        style = default_style_from_settings(
            Settings(subtitle_font="Impact", subtitle_size=28, subtitle_position="center")
        )
        assert style.font == "Impact"
        assert style.size == 28
        assert style.position == SubtitlePosition.CENTER


class TestSubtitleBurner:
    def test_burns_subtitles(self, tmp_path: Path) -> None:
        video = tmp_path / "clip1_vertical.mp4"
        srt = tmp_path / "clip1.srt"
        video.write_bytes(b"video")
        srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello", encoding="utf-8")

        with patch("app.video.subtitle_burner.run_ffmpeg") as mock_ffmpeg:
            result = SubtitleBurner().burn(video, srt)
            assert "subtitled" in result
            cmd = mock_ffmpeg.call_args[0][0]
            assert "-vf" in cmd
            assert any("subtitles=" in arg for arg in cmd)

    def test_missing_srt_raises(self, tmp_path: Path) -> None:
        video = tmp_path / "clip1.mp4"
        video.write_bytes(b"video")
        with pytest.raises(SubtitleError, match="not found"):
            SubtitleBurner().burn(video, tmp_path / "missing.srt")

    def test_burn_for_subtitle_files(
        self,
        tmp_path: Path,
    ) -> None:
        video = tmp_path / "clip1_vertical.mp4"
        srt = tmp_path / "clip1.srt"
        video.write_bytes(b"video")
        srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi", encoding="utf-8")

        subtitle = SubtitleFile(
            index=1,
            clip_start="00:00:10",
            clip_end="00:00:30",
            srt_path=str(srt),
            cue_count=1,
        )

        with patch("app.video.subtitle_burner.run_ffmpeg"):
            updated = SubtitleBurner().burn_for_subtitle_files(
                {1: video},
                [subtitle],
            )

        assert updated[0].burned_output_path is not None
        assert "subtitled" in updated[0].burned_output_path
