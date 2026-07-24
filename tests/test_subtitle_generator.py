"""Tests for subtitle generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.exceptions import SubtitleError
from app.models.export import ExtractedClip
from app.models.transcript import TranscriptSegment
from app.video.subtitles import SubtitleGenerator, build_cues_for_clip, generate_subtitles


@pytest.fixture
def segments() -> list[TranscriptSegment]:
    return [
        TranscriptSegment(start="00:00:10", seconds=10.0, speaker="A", text="Hello there."),
        TranscriptSegment(start="00:00:15", seconds=15.0, speaker="B", text="You're lying."),
        TranscriptSegment(start="00:00:22", seconds=22.0, speaker="A", text="I didn't do it."),
        TranscriptSegment(start="00:01:00", seconds=60.0, speaker="C", text="Vote now."),
    ]


@pytest.fixture
def extracted_clip() -> ExtractedClip:
    return ExtractedClip(
        index=1,
        source_path="/videos/game.mp4",
        output_path="output/clip1.mp4",
        start="00:00:08",
        end="00:00:30",
        start_seconds=8.0,
        end_seconds=30.0,
        duration_seconds=22.0,
        reencoded=False,
    )


class TestBuildCues:
    def test_builds_clip_relative_timing(self, segments: list[TranscriptSegment]) -> None:
        cues = build_cues_for_clip(
            segments,
            clip_start_seconds=8.0,
            clip_end_seconds=30.0,
        )
        assert len(cues) == 3
        assert cues[0].start_seconds == 2.0  # 10 - 8
        assert cues[0].text == "A: Hello there."
        assert cues[1].start_seconds == 7.0  # 15 - 8
        assert cues[2].end_seconds == 22.0  # clip duration

    def test_without_speaker(self, segments: list[TranscriptSegment]) -> None:
        cues = build_cues_for_clip(
            segments,
            clip_start_seconds=8.0,
            clip_end_seconds=30.0,
            include_speaker=False,
        )
        assert cues[0].text == "Hello there."

    def test_empty_window(self, segments: list[TranscriptSegment]) -> None:
        cues = build_cues_for_clip(
            segments,
            clip_start_seconds=100.0,
            clip_end_seconds=120.0,
        )
        assert cues == []


class TestSubtitleGenerator:
    def test_generates_srt_files(
        self,
        segments: list[TranscriptSegment],
        extracted_clip: ExtractedClip,
        tmp_path: Path,
    ) -> None:
        results = generate_subtitles(
            segments,
            [extracted_clip],
            output_dir=tmp_path,
            settings=Settings(),
        )

        assert len(results) == 1
        assert results[0].cue_count == 3
        assert results[0].srt_path.endswith("clip1.srt")
        assert Path(results[0].srt_path).exists()

        content = Path(results[0].srt_path).read_text(encoding="utf-8")
        assert "You're lying." in content
        assert "-->" in content

    def test_empty_segments_raises(self, extracted_clip: ExtractedClip) -> None:
        with pytest.raises(SubtitleError, match="empty transcript"):
            generate_subtitles([], [extracted_clip])

    def test_empty_clips_raises(self, segments: list[TranscriptSegment]) -> None:
        with pytest.raises(SubtitleError, match="empty clip list"):
            generate_subtitles(segments, [])

    def test_multiple_clips(
        self,
        segments: list[TranscriptSegment],
        tmp_path: Path,
    ) -> None:
        clips = [
            ExtractedClip(
                index=1,
                source_path="/v.mp4",
                output_path="clip1.mp4",
                start="00:00:08",
                end="00:00:20",
                start_seconds=8.0,
                end_seconds=20.0,
                duration_seconds=12.0,
            ),
            ExtractedClip(
                index=2,
                source_path="/v.mp4",
                output_path="clip2.mp4",
                start="00:00:55",
                end="00:01:10",
                start_seconds=55.0,
                end_seconds=70.0,
                duration_seconds=15.0,
            ),
        ]
        results = SubtitleGenerator().generate(segments, clips, output_dir=tmp_path)
        assert len(results) == 2
        assert Path(results[1].srt_path).name == "clip2.srt"
