"""Tests for batch export pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.core.exceptions import BatchExportError
from app.models.clip import RankedClip, ViralClip
from app.models.export import ExtractedClip, VerticalClip
from app.models.metadata import ClipMetadata
from app.models.subtitle import SubtitleFile
from app.models.transcript import TranscriptSegment
from app.services.batch_exporter import BatchExportOptions, BatchExporter, save_manifest
from app.models.batch import BatchExportManifest


@pytest.fixture
def settings() -> Settings:
    return Settings(openai_api_key="test-key", max_clips=5)


@pytest.fixture
def segments() -> list[TranscriptSegment]:
    return [
        TranscriptSegment(start="00:00:10", seconds=10.0, speaker="A", text="Hello."),
        TranscriptSegment(start="00:00:20", seconds=20.0, speaker="B", text="World."),
        TranscriptSegment(start="00:01:00", seconds=60.0, speaker="C", text="Again."),
        TranscriptSegment(start="00:01:10", seconds=70.0, speaker="D", text="More."),
    ]


@pytest.fixture
def video_file(tmp_path: Path) -> Path:
    path = tmp_path / "source.mp4"
    path.write_bytes(b"video")
    return path


@pytest.fixture
def transcript_file(tmp_path: Path) -> Path:
    path = tmp_path / "transcript.txt"
    path.write_text("00:00:10\n\nA:\nHello.\n", encoding="utf-8")
    return path


def _make_viral_clip(
    *,
    start_seconds: float = 10.0,
    end_seconds: float = 50.0,
    viral_score: float = 8.0,
) -> ViralClip:
    return ViralClip(
        start="00:00:10",
        end="00:00:50",
        reason="Great moment",
        viral_score=viral_score,
        emotion="betrayal",
        hook="Test hook",
        summary="Test summary",
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        duration_seconds=end_seconds - start_seconds,
    )


def _make_ranked_clip(**kwargs: object) -> RankedClip:
    clip = _make_viral_clip(**kwargs)  # type: ignore[arg-type]
    return RankedClip(
        **clip.model_dump(),
        rank_score=8.5,
        emotion_intensity=1.0,
        dialogue_density=5.0,
        length_score=1.0,
    )


@pytest.fixture
def mock_llm_client() -> MagicMock:
    return MagicMock()


class TestSaveManifest:
    def test_writes_manifest_json(self, tmp_path: Path) -> None:
        manifest = BatchExportManifest(
            source_video="/video.mp4",
            transcript_source="/transcript.txt",
            output_dir=str(tmp_path),
            clips_analyzed=2,
            clips_ranked=2,
            clips_exported=1,
            clips_rejected_quality=1,
        )
        saved = save_manifest(manifest, tmp_path)
        assert saved.manifest_path is not None
        payload = json.loads(Path(saved.manifest_path).read_text(encoding="utf-8"))
        assert payload["clips_exported"] == 1


class TestBatchExporter:
    @patch("app.services.batch_exporter.generate_metadata")
    @patch("app.services.batch_exporter.filter_quality_clips")
    @patch("app.services.batch_exporter.rank_clips")
    @patch("app.services.batch_exporter.analyze_transcript")
    def test_full_export_pipeline(
        self,
        mock_analyze: MagicMock,
        mock_rank: MagicMock,
        mock_quality: MagicMock,
        mock_metadata: MagicMock,
        settings: Settings,
        segments: list[TranscriptSegment],
        video_file: Path,
        transcript_file: Path,
        tmp_path: Path,
        mock_llm_client: MagicMock,
    ) -> None:
        clips = [_make_ranked_clip(), _make_ranked_clip(start_seconds=60.0, end_seconds=100.0)]
        mock_analyze.return_value = clips
        mock_rank.return_value = clips
        mock_quality.return_value = ([clips[0]], MagicMock(rejected=[], total=2))
        mock_metadata.return_value = [
            ClipMetadata(
                index=1,
                clip_start="00:00:10",
                clip_end="00:00:50",
                title="Title One",
                title_variations=["Alt 1", "Alt 2"],
                hook="Hook one",
                description="Description",
                hashtags=["#a", "#b", "#c"],
                call_to_action="Follow",
                seo_keywords=["k1", "k2", "k3"],
                json_path=str(tmp_path / "clip1_metadata.json"),
            )
        ]

        exporter = BatchExporter(settings=settings, client=mock_llm_client)
        result = exporter.export(
            video_file,
            transcript_file,
            output_dir=tmp_path / "export",
            options=BatchExportOptions(skip_video_processing=True),
            segments=segments,
        )

        assert result.manifest.clips_exported == 1
        assert result.manifest.clips_analyzed == 2
        assert len(result.manifest.clips) == 1
        assert result.manifest.clips[0].title == "Title One"
        assert result.manifest.manifest_path is not None
        assert Path(result.manifest.manifest_path).exists()

    @patch("app.services.batch_exporter.analyze_transcript")
    def test_raises_when_no_clips_pass_quality(
        self,
        mock_analyze: MagicMock,
        settings: Settings,
        segments: list[TranscriptSegment],
        video_file: Path,
        transcript_file: Path,
        tmp_path: Path,
    ) -> None:
        clips = [_make_viral_clip(viral_score=2.0)]
        mock_analyze.return_value = clips

        with (
            patch("app.services.batch_exporter.rank_clips", return_value=clips),
            patch(
                "app.services.batch_exporter.filter_quality_clips",
                return_value=([], MagicMock(rejected=[MagicMock()], total=1)),
            ),
            pytest.raises(BatchExportError, match="No clips passed quality"),
        ):
            BatchExporter(settings=settings).export(
                video_file,
                transcript_file,
                output_dir=tmp_path,
                options=BatchExportOptions(skip_video_processing=True),
                segments=segments,
            )

    def test_missing_video_raises(
        self,
        transcript_file: Path,
        tmp_path: Path,
    ) -> None:
        with pytest.raises(BatchExportError, match="video not found"):
            BatchExporter().export(
                tmp_path / "missing.mp4",
                transcript_file,
                options=BatchExportOptions(skip_video_processing=True),
            )

    @patch("app.services.batch_exporter.generate_subtitles")
    @patch("app.services.batch_exporter.crop_to_vertical")
    @patch("app.services.batch_exporter.cut_clips")
    @patch("app.services.batch_exporter.generate_metadata")
    @patch("app.services.batch_exporter.filter_quality_clips")
    @patch("app.services.batch_exporter.rank_clips")
    @patch("app.services.batch_exporter.analyze_transcript")
    def test_processes_videos_when_not_skipped(
        self,
        mock_analyze: MagicMock,
        mock_rank: MagicMock,
        mock_quality: MagicMock,
        mock_metadata: MagicMock,
        mock_cut: MagicMock,
        mock_crop: MagicMock,
        mock_subtitles: MagicMock,
        settings: Settings,
        segments: list[TranscriptSegment],
        video_file: Path,
        transcript_file: Path,
        tmp_path: Path,
    ) -> None:
        clip = _make_ranked_clip()
        mock_analyze.return_value = [clip]
        mock_rank.return_value = [clip]
        mock_quality.return_value = ([clip], MagicMock(rejected=[], total=1))
        mock_cut.return_value = [
            ExtractedClip(
                index=1,
                source_path=str(video_file),
                output_path=str(tmp_path / "clip1.mp4"),
                start="00:00:10",
                end="00:00:50",
                start_seconds=10.0,
                end_seconds=50.0,
                duration_seconds=40.0,
            )
        ]
        mock_crop.return_value = [
            VerticalClip(
                index=1,
                source_path=str(tmp_path / "clip1.mp4"),
                output_path=str(tmp_path / "clip1_vertical.mp4"),
                width=1080,
                height=1920,
                blurred_background=False,
                crop_mode="center_crop",
            )
        ]
        mock_subtitles.return_value = [
            SubtitleFile(
                index=1,
                clip_start="00:00:10",
                clip_end="00:00:50",
                srt_path=str(tmp_path / "clip1.srt"),
                cue_count=2,
            )
        ]
        mock_metadata.return_value = [
            ClipMetadata(
                index=1,
                clip_start="00:00:10",
                clip_end="00:00:50",
                title="Title",
                title_variations=["A", "B"],
                hook="Hook",
                description="Desc",
                hashtags=["#a", "#b", "#c"],
                call_to_action="CTA",
                seo_keywords=["k1", "k2", "k3"],
            )
        ]

        result = BatchExporter(settings=settings, client=MagicMock()).export(
            video_file,
            transcript_file,
            output_dir=tmp_path,
            segments=segments,
        )

        assert result.manifest.clips[0].video_path is not None
        assert result.manifest.clips[0].vertical_path is not None
        assert result.manifest.clips[0].srt_path is not None
        mock_cut.assert_called_once()
        mock_crop.assert_called_once()
        mock_subtitles.assert_called_once()
