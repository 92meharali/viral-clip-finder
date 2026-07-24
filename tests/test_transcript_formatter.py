"""Tests for transcript formatting for LLM input."""

from app.llm.transcript_formatter import format_transcript_for_llm
from app.models.transcript import TranscriptSegment


class TestTranscriptFormatter:
    def test_formats_with_speaker(self) -> None:
        segments = [
            TranscriptSegment(
                start="00:00:13",
                seconds=13.0,
                speaker="Player A",
                text="I didn't kill him.",
            )
        ]
        result = format_transcript_for_llm(segments)
        assert result == "[00:00:13] Player A: I didn't kill him."

    def test_formats_without_speaker(self) -> None:
        segments = [
            TranscriptSegment(
                start="00:00:19",
                seconds=19.0,
                text="You're lying.",
            )
        ]
        result = format_transcript_for_llm(segments)
        assert result == "[00:00:19] You're lying."

    def test_formats_multiple_segments(self) -> None:
        segments = [
            TranscriptSegment(
                start="00:00:13",
                seconds=13.0,
                speaker="Player A",
                text="Hello.",
            ),
            TranscriptSegment(
                start="00:00:19",
                seconds=19.0,
                speaker="Player B",
                text="Goodbye.",
            ),
        ]
        lines = format_transcript_for_llm(segments).splitlines()
        assert len(lines) == 2
