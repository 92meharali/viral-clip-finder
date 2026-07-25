"""yt-dlp client wrapper for testability."""

from __future__ import annotations

from typing import Any, Protocol

import yt_dlp
from loguru import logger

from app.core.config import Settings, get_settings
from app.core.exceptions import YouTubeIngestionError


class YouTubeClient(Protocol):
    """Protocol for fetching YouTube metadata and subtitle payloads."""

    def extract_info(self, url: str) -> dict[str, Any]:
        """Return yt-dlp metadata for a video URL."""

    def fetch_text(self, url: str) -> str:
        """Download text content from a subtitle or metadata URL."""


class YtDlpClient:
    """Production client backed by yt-dlp."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def extract_info(self, url: str) -> dict[str, Any]:
        """Fetch video metadata without downloading media."""
        options = {
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
        except yt_dlp.utils.DownloadError as exc:
            raise YouTubeIngestionError(str(exc), url=url) from exc

        if info is None:
            raise YouTubeIngestionError("yt-dlp returned no metadata", url=url)

        return info

    def fetch_text(self, url: str) -> str:
        """Download subtitle text using yt-dlp's HTTP layer."""
        try:
            with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
                response = ydl.urlopen(url)
                payload = response.read()
        except Exception as exc:  # noqa: BLE001 - surface network/HTTP failures uniformly
            raise YouTubeIngestionError(f"Failed to download subtitle: {exc}", url=url) from exc

        encoding = getattr(response, "headers", {}).get("Content-Type", "")
        if "charset=" in encoding:
            charset = encoding.split("charset=", 1)[1].split(";", 1)[0].strip()
        else:
            charset = "utf-8"

        logger.debug("Downloaded subtitle payload ({bytes} bytes)", bytes=len(payload))
        return payload.decode(charset, errors="replace")
