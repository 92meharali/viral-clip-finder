"""Tests for the Cursor manual AI provider."""

from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.exceptions import LLMAnalysisError, ManualAnalysisRequiredError
from app.models.transcript import TranscriptSegment
from app.providers.cursor_manual import CursorManualClipAnalyzer
from app.providers.factory import get_clip_analyzer

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(output_dir=str(tmp_path))


@pytest.fixture
def segments() -> list[TranscriptSegment]:
    return [
        TranscriptSegment(start="00:00:10", seconds=10.0, speaker="A", text="Hello."),
        TranscriptSegment(start="00:00:20", seconds=20.0, speaker="B", text="World."),
    ]


class TestCursorManualProvider:
    def test_exports_prompt_with_schema(
        self,
        settings: Settings,
        segments: list[TranscriptSegment],
    ) -> None:
        analyzer = CursorManualClipAnalyzer(settings)
        prompt = analyzer.export_analysis_prompt(segments)

        assert "Hello." in prompt
        assert '"clips"' in prompt
        assert "betrayal" in prompt.lower()

    def test_writes_prompt_file(
        self,
        settings: Settings,
        segments: list[TranscriptSegment],
        tmp_path: Path,
    ) -> None:
        analyzer = CursorManualClipAnalyzer(settings)
        path = analyzer.write_analysis_prompt(segments, tmp_path / "prompt.md")

        assert path.exists()
        assert "Hello." in path.read_text(encoding="utf-8")

    def test_imports_valid_response(self, settings: Settings) -> None:
        content = (FIXTURES / "llm_clip_response.json").read_text(encoding="utf-8")
        analyzer = CursorManualClipAnalyzer(settings)
        clips = analyzer.import_analysis_response(content)

        assert len(clips) == 2
        assert clips[0].emotion == "betrayal"

    def test_analyze_requires_response_when_missing(
        self,
        settings: Settings,
        segments: list[TranscriptSegment],
    ) -> None:
        analyzer = CursorManualClipAnalyzer(settings)

        with pytest.raises(ManualAnalysisRequiredError, match="No clip analysis response"):
            analyzer.analyze_transcript(segments)

    def test_analyze_uses_response_file(
        self,
        settings: Settings,
        segments: list[TranscriptSegment],
        tmp_path: Path,
    ) -> None:
        response_path = tmp_path / "analysis_response.json"
        response_path.write_text(
            (FIXTURES / "llm_clip_response.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        analyzer = CursorManualClipAnalyzer(settings, analysis_response_path=response_path)
        clips = analyzer.analyze_transcript(segments)

        assert len(clips) == 2

    def test_factory_returns_cursor_provider(self, settings: Settings) -> None:
        analyzer = get_clip_analyzer(settings, provider="cursor")
        assert analyzer.provider_name == "cursor"

    def test_empty_transcript_raises(self, settings: Settings) -> None:
        analyzer = CursorManualClipAnalyzer(settings)
        with pytest.raises(LLMAnalysisError, match="empty transcript"):
            analyzer.export_analysis_prompt([])
