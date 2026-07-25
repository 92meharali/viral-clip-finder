"""YouTube URL parsing helpers."""

from __future__ import annotations

import re

from app.core.exceptions import YouTubeIngestionError

_VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
_URL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?(?:[^#\s]*&)?v=(?P<id>[A-Za-z0-9_-]{11})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:https?://)?(?:www\.)?youtube\.com/shorts/(?P<id>[A-Za-z0-9_-]{11})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:https?://)?(?:www\.)?youtube\.com/live/(?P<id>[A-Za-z0-9_-]{11})",
        re.IGNORECASE,
    ),
    re.compile(r"(?:https?://)?youtu\.be/(?P<id>[A-Za-z0-9_-]{11})", re.IGNORECASE),
    re.compile(
        r"(?:https?://)?(?:www\.)?youtube\.com/embed/(?P<id>[A-Za-z0-9_-]{11})",
        re.IGNORECASE,
    ),
)


def extract_video_id(url: str) -> str:
    """Extract a YouTube video ID from a supported URL or bare ID.

    Args:
        url: YouTube watch URL, short URL, or an 11-character video ID.

    Returns:
        Normalized video ID.

    Raises:
        YouTubeIngestionError: If the URL or ID is invalid.
    """
    candidate = url.strip()
    if not candidate:
        raise YouTubeIngestionError("YouTube URL is empty")

    if _VIDEO_ID_PATTERN.fullmatch(candidate):
        return candidate

    for pattern in _URL_PATTERNS:
        match = pattern.search(candidate)
        if match is not None:
            return match.group("id")

    raise YouTubeIngestionError(f"Unsupported or invalid YouTube URL: {candidate!r}", url=candidate)


def normalize_watch_url(video_id: str) -> str:
    """Return the canonical watch URL for a video ID."""
    return f"https://www.youtube.com/watch?v={video_id}"
