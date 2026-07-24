"""Tests for transcript parsing."""

from pathlib import Path

import pytest

from app.core.exceptions import TranscriptParseError
from app.models.transcript import TranscriptSegment
from app.services.transcript_parser import (
    TranscriptFormat,
    detect_format,
    parse_transcript,
    parse_transcript_file,
)
from app.utils.time_utils import format_timestamp, parse_timestamp

FIXTURES = Path(__file__).parent / "fixtures"


class TestTimeUtils:
    def test_parse_hh_mm_ss(self) -> None:
        assert parse_timestamp("00:01:23") == 83.0

    def test_parse_mm_ss(self) -> None:
        assert parse_timestamp("01:23") == 83.0

    def test_parse_with_comma_millis(self) -> None:
        assert parse_timestamp("00:01:23,500") == 83.5

    def test_parse_with_dot_millis(self) -> None:
        assert parse_timestamp("00:01:23.500") == 83.5

    def test_format_timestamp(self) -> None:
        assert format_timestamp(83.0) == "00:01:23"

    def test_invalid_timestamp_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid timestamp"):
            parse_timestamp("not-a-time")


class TestTranscriptSegment:
    def test_creates_valid_segment(self) -> None:
        segment = TranscriptSegment(
            start="00:00:13",
            seconds=13.0,
            speaker="Player A",
            text="I didn't kill him.",
        )
        assert segment.speaker == "Player A"
        assert segment.text == "I didn't kill him."

    def test_normalizes_whitespace_in_text(self) -> None:
        segment = TranscriptSegment(
            start="00:00:13",
            seconds=13.0,
            text="  hello   world  ",
        )
        assert segment.text == "hello world"


class TestFormatDetection:
    def test_detects_youtube_multiline(self) -> None:
        text = (FIXTURES / "youtube_multiline.txt").read_text(encoding="utf-8")
        assert detect_format(text) == TranscriptFormat.YOUTUBE_MULTILINE

    def test_detects_inline_bracket(self) -> None:
        text = (FIXTURES / "inline_bracket.txt").read_text(encoding="utf-8")
        assert detect_format(text) == TranscriptFormat.INLINE_BRACKET

    def test_detects_srt(self) -> None:
        text = (FIXTURES / "sample.srt").read_text(encoding="utf-8")
        assert detect_format(text) == TranscriptFormat.SRT

    def test_detects_vtt(self) -> None:
        text = (FIXTURES / "sample.vtt").read_text(encoding="utf-8")
        assert detect_format(text) == TranscriptFormat.VTT

    def test_empty_text_raises(self) -> None:
        with pytest.raises(TranscriptParseError, match="empty"):
            detect_format("   ")


class TestYouTubeMultilineParser:
    def test_parses_speakers_and_dialogue(self) -> None:
        text = (FIXTURES / "youtube_multiline.txt").read_text(encoding="utf-8")
        segments = parse_transcript(text)

        assert len(segments) == 3
        assert segments[0] == TranscriptSegment(
            start="00:00:13",
            seconds=13.0,
            speaker="Player A",
            text="I didn't kill him.",
        )
        assert segments[1].speaker == "Player B"
        assert segments[1].text == "You're lying."
        assert segments[2].seconds == 24.0

    def test_parses_from_file(self) -> None:
        segments = parse_transcript_file(str(FIXTURES / "youtube_multiline.txt"))
        assert len(segments) == 3


class TestInlineFormats:
    def test_parses_bracket_format(self) -> None:
        text = (FIXTURES / "inline_bracket.txt").read_text(encoding="utf-8")
        segments = parse_transcript(text)

        assert len(segments) == 3
        assert segments[0].speaker == "Player A"
        assert segments[2].text == "Then who did?"

    def test_parses_inline_timestamp_format(self) -> None:
        text = (FIXTURES / "inline_timestamp.txt").read_text(encoding="utf-8")
        segments = parse_transcript(text)

        assert len(segments) == 3
        assert segments[2].speaker is None
        assert segments[2].text == "Then who did?"


class TestCueBasedFormats:
    def test_parses_srt(self) -> None:
        text = (FIXTURES / "sample.srt").read_text(encoding="utf-8")
        segments = parse_transcript(text)

        assert len(segments) == 3
        assert segments[0].speaker == "Player A"
        assert segments[0].seconds == 13.0

    def test_parses_vtt(self) -> None:
        text = (FIXTURES / "sample.vtt").read_text(encoding="utf-8")
        segments = parse_transcript(text)

        assert len(segments) == 3
        assert segments[1].speaker == "Player B"


class TestParserErrors:
    def test_empty_transcript_raises(self) -> None:
        with pytest.raises(TranscriptParseError, match="empty"):
            parse_transcript("")

    def test_no_segments_raises(self) -> None:
        with pytest.raises(TranscriptParseError, match="No transcript segments"):
            parse_transcript("Hello world\nNo timestamps here.")

    def test_missing_file_raises(self) -> None:
        with pytest.raises(TranscriptParseError, match="Could not read file"):
            parse_transcript_file("/nonexistent/path.txt")
