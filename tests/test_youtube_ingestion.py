"""Tests for YouTube ingestion service."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.core.exceptions import YouTubeIngestionError, YouTubeTranscriptUnavailableError
from app.services.youtube.models import YouTubeVideoMetadata
from app.services.youtube.service import YouTubeIngestionService
from app.services.youtube.transcript import parse_subtitle_payload, select_subtitle_track
from app.services.youtube.urls import extract_video_id, normalize_watch_url

FIXTURES = Path(__file__).parent / "fixtures"


class FakeYouTubeClient:
    """In-memory YouTube client for tests."""

    def __init__(
        self,
        info: dict[str, Any],
        subtitles: dict[str, str],
    ) -> None:
        self.info = info
        self.subtitles = subtitles
        self.extracted_urls: list[str] = []
        self.fetched_urls: list[str] = []

    def extract_info(self, url: str) -> dict[str, Any]:
        self.extracted_urls.append(url)
        return self.info

    def fetch_text(self, url: str) -> str:
        self.fetched_urls.append(url)
        if url not in self.subtitles:
            raise YouTubeIngestionError(f"Missing subtitle fixture for {url}", url=url)
        return self.subtitles[url]


def _sample_info(*, with_manual: bool = True, with_auto: bool = False) -> dict[str, Any]:
    subtitles: dict[str, list[dict[str, str]]] = {}
    automatic_captions: dict[str, list[dict[str, str]]] = {}

    if with_manual:
        subtitles["en"] = [
            {"ext": "vtt", "url": "https://example.com/manual-en.vtt", "name": "English"},
            {"ext": "json3", "url": "https://example.com/manual-en.json3", "name": "English"},
        ]

    if with_auto:
        automatic_captions["en"] = [
            {"ext": "vtt", "url": "https://example.com/auto-en.vtt", "name": "English"},
        ]

    return {
        "id": "dQw4w9WgXcQ",
        "title": "Never Gonna Give You Up",
        "channel": "Rick Astley",
        "duration": 212,
        "view_count": 1_000_000,
        "upload_date": "20091025",
        "webpage_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "thumbnail": "https://example.com/thumb.jpg",
        "description": "Official video",
        "language": "en",
        "subtitles": subtitles,
        "automatic_captions": automatic_captions,
    }


class TestYouTubeUrls:
    def test_extract_video_id_from_watch_url(self) -> None:
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_extract_video_id_from_short_url(self) -> None:
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_extract_video_id_from_bare_id(self) -> None:
        assert extract_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_invalid_url_raises(self) -> None:
        with pytest.raises(YouTubeIngestionError, match="invalid"):
            extract_video_id("https://example.com/not-youtube")

    def test_normalize_watch_url(self) -> None:
        assert normalize_watch_url("dQw4w9WgXcQ") == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


class TestYouTubeMetadata:
    def test_from_ytdlp_builds_metadata(self) -> None:
        metadata = YouTubeVideoMetadata.from_ytdlp(_sample_info())

        assert metadata.video_id == "dQw4w9WgXcQ"
        assert metadata.title == "Never Gonna Give You Up"
        assert metadata.channel == "Rick Astley"
        assert metadata.duration_seconds == 212
        assert metadata.view_count == 1_000_000
        assert str(metadata.webpage_url).endswith("watch?v=dQw4w9WgXcQ")


class TestSubtitleParsing:
    def test_parse_vtt_subtitles(self) -> None:
        content = (FIXTURES / "youtube_subtitle.vtt").read_text(encoding="utf-8")
        segments = parse_subtitle_payload(content, "vtt")

        assert len(segments) == 2
        assert segments[0].seconds == 1.0
        assert segments[0].text == "Welcome to the show."
        assert segments[1].text == "Today we discuss viral moments."

    def test_parse_json3_subtitles(self) -> None:
        content = (FIXTURES / "youtube_subtitle.json3").read_text(encoding="utf-8")
        segments = parse_subtitle_payload(content, "json3")

        assert len(segments) == 2
        assert segments[1].seconds == 3.5


class TestSubtitleSelection:
    def test_prefers_manual_over_auto(self) -> None:
        info = _sample_info(with_manual=True, with_auto=True)
        track, language, source = select_subtitle_track(info, preferred_languages=["en"])

        assert language == "en"
        assert source == "manual"
        assert track["ext"] == "vtt"

    def test_falls_back_to_auto_when_manual_missing(self) -> None:
        info = _sample_info(with_manual=False, with_auto=True)
        track, language, source = select_subtitle_track(info, preferred_languages=["en"])

        assert source == "auto"
        assert track["url"].endswith("auto-en.vtt")

    def test_raises_when_no_subtitles(self) -> None:
        info = _sample_info(with_manual=False, with_auto=False)
        with pytest.raises(YouTubeTranscriptUnavailableError, match="No subtitles"):
            select_subtitle_track(info, preferred_languages=["en"])


class TestYouTubeIngestionService:
    def test_ingest_returns_metadata_and_segments(self) -> None:
        info = _sample_info(with_manual=True)
        client = FakeYouTubeClient(
            info=info,
            subtitles={
                "https://example.com/manual-en.vtt": (
                    FIXTURES / "youtube_subtitle.vtt"
                ).read_text(encoding="utf-8"),
            },
        )
        service = YouTubeIngestionService(client=client)

        result = service.ingest("https://youtu.be/dQw4w9WgXcQ")

        assert result.metadata.video_id == "dQw4w9WgXcQ"
        assert result.transcript_language == "en"
        assert result.transcript_source == "manual"
        assert result.subtitle_format == "vtt"
        assert len(result.segments) == 2
        assert client.extracted_urls == ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]

    def test_ingest_accepts_bare_video_id(self) -> None:
        info = _sample_info(with_manual=True)
        client = FakeYouTubeClient(
            info=info,
            subtitles={
                "https://example.com/manual-en.vtt": (
                    FIXTURES / "youtube_subtitle.vtt"
                ).read_text(encoding="utf-8"),
            },
        )
        service = YouTubeIngestionService(client=client)

        result = service.ingest("dQw4w9WgXcQ")

        assert result.metadata.video_id == "dQw4w9WgXcQ"
