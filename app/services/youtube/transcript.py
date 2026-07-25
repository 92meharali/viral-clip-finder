"""Convert YouTube subtitle payloads into transcript segments."""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from app.core.exceptions import TranscriptParseError, YouTubeTranscriptUnavailableError
from app.models.transcript import TranscriptSegment
from app.services.transcript_parser import parse_transcript
from app.utils.time_utils import format_timestamp

_SUPPORTED_FORMATS = {"vtt", "srv3", "json3", "ttml"}


def parse_subtitle_payload(content: str, subtitle_format: str) -> list[TranscriptSegment]:
    """Parse subtitle content into normalized transcript segments.

    Args:
        content: Raw subtitle text or JSON.
        subtitle_format: Subtitle extension such as ``vtt`` or ``json3``.

    Returns:
        Parsed transcript segments in chronological order.

    Raises:
        YouTubeTranscriptUnavailableError: If the payload cannot be parsed.
    """
    normalized_format = subtitle_format.lower().lstrip(".")
    if normalized_format not in _SUPPORTED_FORMATS:
        raise YouTubeTranscriptUnavailableError(
            f"Unsupported subtitle format: {subtitle_format!r}",
            subtitle_format=subtitle_format,
        )

    try:
        if normalized_format == "json3":
            return _parse_json3(content)
        return parse_transcript(content)
    except TranscriptParseError as exc:
        raise YouTubeTranscriptUnavailableError(
            f"Failed to parse {normalized_format} subtitles: {exc}",
            subtitle_format=normalized_format,
        ) from exc


def _parse_json3(content: str) -> list[TranscriptSegment]:
    """Parse YouTube JSON3 subtitle events."""
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise TranscriptParseError("Invalid JSON3 subtitle payload") from exc

    segments: list[TranscriptSegment] = []
    for event in payload.get("events", []):
        if not isinstance(event, dict):
            continue

        text = _join_json3_segments(event.get("segs", []))
        if not text:
            continue

        start_ms = float(event.get("tStartMs", 0))
        seconds = start_ms / 1000.0
        segments.append(
            TranscriptSegment(
                start=format_timestamp(seconds),
                seconds=seconds,
                text=text,
            )
        )

    if not segments:
        raise TranscriptParseError("JSON3 subtitle payload contained no dialogue")

    return segments


def _join_json3_segments(segs: Any) -> str:
    """Join JSON3 segment fragments into a single dialogue line."""
    if not isinstance(segs, list):
        return ""

    parts: list[str] = []
    for seg in segs:
        if not isinstance(seg, dict):
            continue
        fragment = str(seg.get("utf8", "")).strip()
        if fragment and fragment != "\n":
            parts.append(fragment)

    return " ".join(" ".join(parts).split())


def select_subtitle_track(
    info: dict[str, Any],
    *,
    preferred_languages: list[str],
    format_priority: tuple[str, ...] = ("vtt", "srv3", "json3", "ttml"),
) -> tuple[dict[str, Any], str, str]:
    """Select the best available subtitle track from yt-dlp metadata.

    Args:
        info: yt-dlp ``extract_info`` payload.
        preferred_languages: Ordered language preference list.
        format_priority: Preferred subtitle extensions in descending order.

    Returns:
        Tuple of (track dict, language code, source type ``manual`` or ``auto``).

    Raises:
        YouTubeTranscriptUnavailableError: If no suitable subtitles exist.
    """
    manual_tracks = info.get("subtitles") or {}
    auto_tracks = info.get("automatic_captions") or {}

    for source_name, tracks in (("manual", manual_tracks), ("auto", auto_tracks)):
        if not isinstance(tracks, dict):
            continue

        for language in _expand_language_preferences(preferred_languages, tracks):
            track = _pick_track_for_language(tracks.get(language), format_priority)
            if track is not None:
                return track, language, source_name

    raise YouTubeTranscriptUnavailableError(
        "No subtitles found for this video in the requested languages",
        video_id=str(info.get("id") or ""),
    )


def _expand_language_preferences(
    preferred_languages: list[str],
    available: dict[str, Any],
) -> list[str]:
    """Expand language preferences with prefix matches against available tracks."""
    resolved: list[str] = []
    seen: set[str] = set()

    for language in preferred_languages:
        normalized = language.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        resolved.append(normalized)

        prefix = normalized.split("-", 1)[0]
        for available_language in sorted(available):
            if available_language.startswith(prefix) and available_language not in seen:
                seen.add(available_language)
                resolved.append(available_language)

    for available_language in sorted(available):
        if available_language not in seen:
            seen.add(available_language)
            resolved.append(available_language)

    return resolved


def _pick_track_for_language(
    tracks: Any,
    format_priority: tuple[str, ...],
) -> dict[str, Any] | None:
    """Pick the highest-priority subtitle format for a language."""
    if not isinstance(tracks, list) or not tracks:
        return None

    by_ext: dict[str, dict[str, Any]] = {}
    for track in tracks:
        if not isinstance(track, dict):
            continue
        ext = str(track.get("ext") or "").lower()
        url = track.get("url")
        if ext and url:
            by_ext[ext] = track

    for ext in format_priority:
        if ext in by_ext:
            return by_ext[ext]

    logger.warning("No preferred subtitle format found; using first available track")
    first = tracks[0]
    return first if isinstance(first, dict) else None
