"""Tests for SRT formatting utilities."""

from app.models.subtitle import SubtitleCue
from app.utils.srt_utils import cues_to_srt, format_srt_timestamp, write_srt_file


class TestFormatSrtTimestamp:
    def test_formats_with_millis(self) -> None:
        assert format_srt_timestamp(83.5) == "00:01:23,500"

    def test_formats_zero(self) -> None:
        assert format_srt_timestamp(0.0) == "00:00:00,000"

    def test_formats_hours(self) -> None:
        assert format_srt_timestamp(3661.25) == "01:01:01,250"


class TestCuesToSrt:
    def test_renders_srt_blocks(self) -> None:
        cues = [
            SubtitleCue(index=1, start_seconds=0.0, end_seconds=2.5, text="Hello."),
            SubtitleCue(index=2, start_seconds=2.5, end_seconds=5.0, text="World."),
        ]
        content = cues_to_srt(cues)
        assert "1\n00:00:00,000 --> 00:00:02,500\nHello." in content
        assert "2\n00:00:02,500 --> 00:00:05,000\nWorld." in content

    def test_empty_cues(self) -> None:
        assert cues_to_srt([]) == ""


class TestWriteSrtFile:
    def test_writes_file(self, tmp_path) -> None:
        cues = [SubtitleCue(index=1, start_seconds=0.0, end_seconds=1.0, text="Hi")]
        path = write_srt_file(cues, tmp_path / "clip1.srt")
        assert path.exists()
        assert "Hi" in path.read_text(encoding="utf-8")
