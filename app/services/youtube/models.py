"""Pydantic models for YouTube ingestion."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, HttpUrl

from app.models.transcript import TranscriptSegment


class YouTubeVideoMetadata(BaseModel):
    """Normalized metadata for a YouTube video."""

    video_id: str = Field(..., min_length=1, description="YouTube video ID")
    title: str = Field(..., min_length=1, description="Video title")
    channel: str | None = Field(default=None, description="Uploader or channel name")
    duration_seconds: float = Field(..., ge=0, description="Video duration in seconds")
    view_count: int | None = Field(default=None, ge=0, description="View count when available")
    upload_date: str | None = Field(
        default=None,
        description="Upload date in YYYYMMDD format when available",
    )
    webpage_url: HttpUrl = Field(..., description="Canonical watch URL")
    thumbnail_url: HttpUrl | None = Field(default=None, description="Primary thumbnail URL")
    description: str | None = Field(default=None, description="Video description")
    language: str | None = Field(default=None, description="Primary language code")

    @classmethod
    def from_ytdlp(cls, info: dict[str, Any]) -> YouTubeVideoMetadata:
        """Build metadata from a yt-dlp ``extract_info`` payload."""
        video_id = str(info.get("id") or "")
        if not video_id:
            raise ValueError("yt-dlp info payload is missing video id")

        title = str(info.get("title") or "").strip()
        if not title:
            raise ValueError("yt-dlp info payload is missing title")

        duration = float(info.get("duration") or 0)
        webpage_url = str(info.get("webpage_url") or info.get("original_url") or "")
        if not webpage_url:
            webpage_url = f"https://www.youtube.com/watch?v={video_id}"

        thumbnail = info.get("thumbnail")
        if thumbnail is None and info.get("thumbnails"):
            thumbnails = info["thumbnails"]
            if isinstance(thumbnails, list) and thumbnails:
                thumbnail = thumbnails[-1].get("url")

        return cls(
            video_id=video_id,
            title=title,
            channel=info.get("channel") or info.get("uploader"),
            duration_seconds=duration,
            view_count=info.get("view_count"),
            upload_date=info.get("upload_date"),
            webpage_url=webpage_url,  # type: ignore[arg-type]
            thumbnail_url=thumbnail,  # type: ignore[arg-type]
            description=info.get("description"),
            language=info.get("language"),
        )


class YouTubeIngestionResult(BaseModel):
    """Combined metadata and transcript for a YouTube video."""

    metadata: YouTubeVideoMetadata
    segments: list[TranscriptSegment]
    transcript_language: str = Field(..., description="Resolved subtitle language code")
    transcript_source: str = Field(
        ...,
        description="Whether subtitles were manual or auto-generated",
    )
    subtitle_format: str = Field(..., description="Subtitle format used (vtt, json3, etc.)")

    model_config = {"frozen": True}
