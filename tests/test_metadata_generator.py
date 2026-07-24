"""Tests for LLM metadata generation."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.core.exceptions import MetadataGenerationError
from app.llm.json_utils import parse_llm_json, strip_json_fences
from app.llm.metadata_generator import MetadataGenerator, generate_metadata, save_metadata
from app.llm.transcript_formatter import format_clip_transcript
from app.models.clip import ViralClip
from app.models.metadata import ClipMetadata, ClipMetadataBase
from app.models.transcript import TranscriptSegment

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def settings() -> Settings:
    return Settings(openai_api_key="test-key", openai_model="gpt-4o")


@pytest.fixture
def segments() -> list[TranscriptSegment]:
    return [
        TranscriptSegment(start="00:00:10", seconds=10.0, speaker="A", text="Hello."),
        TranscriptSegment(start="00:00:15", seconds=15.0, speaker="B", text="You're lying."),
        TranscriptSegment(start="00:00:22", seconds=22.0, speaker="A", text="I didn't do it."),
    ]


@pytest.fixture
def clip() -> ViralClip:
    return ViralClip(
        start="00:00:08",
        end="00:00:30",
        reason="Major betrayal moment",
        viral_score=9.5,
        emotion="betrayal",
        hook="He trusted the wrong player.",
        summary="Alliance breaks down during vote.",
        start_seconds=8.0,
        end_seconds=30.0,
        duration_seconds=22.0,
    )


@pytest.fixture
def llm_response_json() -> str:
    return (FIXTURES / "llm_metadata_response.json").read_text(encoding="utf-8")


def _make_mock_client(response_content: str) -> MagicMock:
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = response_content
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


class TestJsonUtils:
    def test_strips_fences(self, llm_response_json: str) -> None:
        fenced = f"```json\n{llm_response_json}\n```"
        result = parse_llm_json(fenced, ClipMetadataBase)
        assert result.title.startswith("He Trusted")

    def test_strip_json_fences_helper(self) -> None:
        assert strip_json_fences('```json\n{"a": 1}\n```') == '{"a": 1}'


class TestFormatClipTranscript:
    def test_filters_to_clip_window(self, segments: list[TranscriptSegment]) -> None:
        text = format_clip_transcript(segments, clip_start_seconds=8.0, clip_end_seconds=20.0)
        assert "Hello." in text
        assert "You're lying." in text
        assert "I didn't do it." not in text


class TestMetadataGenerator:
    def test_generates_metadata(
        self,
        settings: Settings,
        segments: list[TranscriptSegment],
        clip: ViralClip,
        llm_response_json: str,
    ) -> None:
        generator = MetadataGenerator(
            settings=settings,
            client=_make_mock_client(llm_response_json),
        )
        metadata = generator.generate_for_clip(clip, segments, index=1)

        assert metadata.index == 1
        assert metadata.title == "He Trusted The Wrong Person..."
        assert len(metadata.title_variations) == 2
        assert metadata.hashtags[0] == "#mafia"
        assert metadata.clip_start == "00:00:08"

    def test_generates_batch_with_export(
        self,
        settings: Settings,
        segments: list[TranscriptSegment],
        clip: ViralClip,
        llm_response_json: str,
        tmp_path: Path,
    ) -> None:
        results = generate_metadata(
            [clip],
            segments,
            output_dir=tmp_path,
            settings=settings,
            client=_make_mock_client(llm_response_json),
        )

        assert len(results) == 1
        assert results[0].json_path is not None
        assert Path(results[0].json_path).exists()
        exported = json.loads(Path(results[0].json_path).read_text(encoding="utf-8"))
        assert "title" in exported
        assert "hashtags" in exported

    def test_empty_clips_raises(
        self,
        settings: Settings,
        segments: list[TranscriptSegment],
    ) -> None:
        with pytest.raises(MetadataGenerationError, match="empty clip list"):
            generate_metadata([], segments, settings=settings, client=MagicMock())

    def test_empty_transcript_raises(
        self,
        settings: Settings,
        clip: ViralClip,
    ) -> None:
        with pytest.raises(MetadataGenerationError, match="empty transcript"):
            generate_metadata([clip], [], settings=settings, client=MagicMock())

    def test_empty_llm_response_raises(
        self,
        settings: Settings,
        segments: list[TranscriptSegment],
        clip: ViralClip,
    ) -> None:
        generator = MetadataGenerator(settings=settings, client=_make_mock_client(""))
        with pytest.raises(MetadataGenerationError, match="empty response"):
            generator.generate_for_clip(clip, segments)

    def test_api_failure_raises(
        self,
        settings: Settings,
        segments: list[TranscriptSegment],
        clip: ViralClip,
    ) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("API down")
        generator = MetadataGenerator(settings=settings, client=mock_client)

        with pytest.raises(MetadataGenerationError, match="API call failed"):
            generator.generate_for_clip(clip, segments)


class TestSaveMetadata:
    def test_exports_json(self, tmp_path: Path) -> None:
        metadata = ClipMetadata(
            index=1,
            clip_start="00:00:10",
            clip_end="00:00:30",
            title="Test",
            title_variations=["A", "B"],
            hook="Hook",
            description="Desc",
            hashtags=["#a", "#b", "#c"],
            call_to_action="CTA",
            seo_keywords=["k1", "k2", "k3"],
        )
        saved = save_metadata(metadata, tmp_path)
        assert saved.json_path is not None
        assert Path(saved.json_path).name == "clip1_metadata.json"
