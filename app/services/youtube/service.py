"""YouTube ingestion orchestration service."""

from __future__ import annotations

from loguru import logger

from app.core.config import Settings, get_settings
from app.core.exceptions import YouTubeIngestionError, YouTubeTranscriptUnavailableError
from app.services.youtube.client import YouTubeClient, YtDlpClient
from app.services.youtube.models import YouTubeIngestionResult, YouTubeVideoMetadata
from app.services.youtube.transcript import parse_subtitle_payload, select_subtitle_track
from app.services.youtube.urls import extract_video_id, normalize_watch_url


class YouTubeIngestionService:
    """Fetch YouTube metadata and transcripts for analysis."""

    def __init__(
        self,
        client: YouTubeClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._client = client or YtDlpClient(self.settings)

    def ingest(self, url: str) -> YouTubeIngestionResult:
        """Retrieve metadata and transcript segments for a YouTube URL.

        Args:
            url: YouTube watch URL, short URL, or video ID.

        Returns:
            Metadata and normalized transcript segments.

        Raises:
            YouTubeIngestionError: If metadata retrieval fails.
            YouTubeTranscriptUnavailableError: If no usable subtitles exist.
        """
        video_id = extract_video_id(url)
        watch_url = normalize_watch_url(video_id)
        logger.info("Ingesting YouTube video {video_id}", video_id=video_id)

        info = self._client.extract_info(watch_url)
        if str(info.get("id") or "") != video_id:
            logger.warning(
                "Resolved video id {resolved} differs from requested {requested}",
                resolved=info.get("id"),
                requested=video_id,
            )

        try:
            metadata = YouTubeVideoMetadata.from_ytdlp(info)
        except ValueError as exc:
            raise YouTubeIngestionError(str(exc), url=watch_url, video_id=video_id) from exc

        preferred_languages = self._preferred_languages()
        track, language, source = select_subtitle_track(
            info,
            preferred_languages=preferred_languages,
            format_priority=self._subtitle_format_priority(),
        )
        subtitle_url = str(track.get("url") or "")
        if not subtitle_url:
            raise YouTubeTranscriptUnavailableError(
                "Selected subtitle track is missing a download URL",
                video_id=video_id,
                language=language,
            )

        subtitle_format = str(track.get("ext") or "vtt")
        logger.info(
            "Fetching {source} subtitles ({language}, {format}) for {video_id}",
            source=source,
            language=language,
            format=subtitle_format,
            video_id=video_id,
        )

        subtitle_content = self._client.fetch_text(subtitle_url)
        segments = parse_subtitle_payload(subtitle_content, subtitle_format)
        logger.info(
            "Ingested {count} transcript segments for {video_id}",
            count=len(segments),
            video_id=video_id,
        )

        return YouTubeIngestionResult(
            metadata=metadata,
            segments=segments,
            transcript_language=language,
            transcript_source=source,
            subtitle_format=subtitle_format,
        )

    def _preferred_languages(self) -> list[str]:
        raw = self.settings.youtube_preferred_languages
        return [language.strip() for language in raw.split(",") if language.strip()]

    def _subtitle_format_priority(self) -> tuple[str, ...]:
        raw = self.settings.youtube_subtitle_format_priority
        formats = tuple(fmt.strip().lower() for fmt in raw.split(",") if fmt.strip())
        return formats or ("vtt", "srv3", "json3", "ttml")


def ingest_youtube_url(
    url: str,
    *,
    client: YouTubeClient | None = None,
    settings: Settings | None = None,
) -> YouTubeIngestionResult:
    """Convenience wrapper around :class:`YouTubeIngestionService`."""
    return YouTubeIngestionService(client=client, settings=settings).ingest(url)
