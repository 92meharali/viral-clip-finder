"""Multi-format transcript parsing service."""

from __future__ import annotations

import re
from enum import Enum

from loguru import logger

from app.core.exceptions import TranscriptParseError
from app.models.transcript import TranscriptSegment
from app.utils.time_utils import extract_timestamp_from_line, format_timestamp, parse_timestamp

SPEAKER_LINE_PATTERN = re.compile(r"^(?P<speaker>[^:]+):\s*(?P<text>.*)$")
SRT_CUE_PATTERN = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(?P<end>\d{2}:\d{2}:\d{2},\d{3})"
)
VTT_CUE_PATTERN = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(?P<end>\d{2}:\d{2}:\d{2}\.\d{3})"
)
INLINE_TIMESTAMP_PATTERN = re.compile(
    r"^\[?(?P<ts>(?:\d{1,2}:)?\d{1,2}:\d{2}(?:[.,]\d{1,3})?)\]?\s*" r"(?:-\s*)?" r"(?P<rest>.+)$"
)


class TranscriptFormat(str, Enum):
    """Supported transcript input formats."""

    YOUTUBE_MULTILINE = "youtube_multiline"
    INLINE_BRACKET = "inline_bracket"
    INLINE_TIMESTAMP = "inline_timestamp"
    SRT = "srt"
    VTT = "vtt"


def _build_segment(timestamp: str, text: str, speaker: str | None = None) -> TranscriptSegment:
    """Create a validated TranscriptSegment from parsed fields."""
    normalized_ts = timestamp.replace(",", ".")
    seconds = parse_timestamp(normalized_ts)
    return TranscriptSegment(
        start=format_timestamp(seconds),
        seconds=seconds,
        speaker=speaker,
        text=text.strip(),
    )


def _split_speaker_and_text(line: str) -> tuple[str | None, str]:
    """Attempt to split a line into speaker label and dialogue."""
    match = SPEAKER_LINE_PATTERN.match(line.strip())
    if not match:
        return None, line.strip()

    speaker = match.group("speaker").strip()
    text = match.group("text").strip()

    # Avoid treating timestamps as speakers (e.g. "00:00:13:").
    if re.fullmatch(r"(?:\d{1,2}:)?\d{1,2}:\d{2}(?:[.,]\d{1,3})?", speaker):
        return None, line.strip()

    if not text:
        return speaker, ""

    return speaker, text


def detect_format(text: str) -> TranscriptFormat:
    """Detect the most likely transcript format from raw text.

    Args:
        text: Raw transcript content.

    Returns:
        The detected :class:`TranscriptFormat`.
    """
    stripped = text.strip()
    if not stripped:
        raise TranscriptParseError("Transcript text is empty")

    if stripped.upper().startswith("WEBVTT"):
        logger.debug("Detected VTT transcript format")
        return TranscriptFormat.VTT

    if SRT_CUE_PATTERN.search(stripped):
        logger.debug("Detected SRT transcript format")
        return TranscriptFormat.SRT

    lines = [line for line in stripped.splitlines() if line.strip()]
    bracket_lines = sum(1 for line in lines if line.strip().startswith("["))
    if lines and bracket_lines / len(lines) >= 0.5:
        logger.debug("Detected inline bracket transcript format")
        return TranscriptFormat.INLINE_BRACKET

    inline_count = sum(1 for line in lines if INLINE_TIMESTAMP_PATTERN.match(line.strip()))
    if lines and inline_count / len(lines) >= 0.5:
        logger.debug("Detected inline timestamp transcript format")
        return TranscriptFormat.INLINE_TIMESTAMP

    logger.debug("Detected YouTube multiline transcript format")
    return TranscriptFormat.YOUTUBE_MULTILINE


def _parse_youtube_multiline(text: str) -> list[TranscriptSegment]:
    """Parse YouTube-style multiline transcripts with optional speakers."""
    segments: list[TranscriptSegment] = []
    lines = text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        timestamp = extract_timestamp_from_line(line)
        if timestamp is None:
            i += 1
            continue

        i += 1
        speaker: str | None = None
        dialogue_lines: list[str] = []

        while i < len(lines):
            candidate = lines[i].strip()
            if not candidate:
                i += 1
                continue
            if extract_timestamp_from_line(candidate) is not None:
                break

            maybe_speaker, maybe_text = _split_speaker_and_text(candidate)
            if maybe_speaker and not dialogue_lines and not maybe_text:
                speaker = maybe_speaker
                i += 1
                continue
            if maybe_speaker and not dialogue_lines and maybe_text:
                speaker = maybe_speaker
                dialogue_lines.append(maybe_text)
                i += 1
                continue

            dialogue_lines.append(candidate)
            i += 1

        if not dialogue_lines:
            logger.warning("Skipping timestamp {} with no dialogue", timestamp)
            continue

        segments.append(_build_segment(timestamp, " ".join(dialogue_lines), speaker))

    return segments


def _parse_inline_lines(text: str, *, bracketed: bool) -> list[TranscriptSegment]:
    """Parse single-line timestamp formats."""
    segments: list[TranscriptSegment] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if bracketed and not stripped.startswith("["):
            continue

        match = INLINE_TIMESTAMP_PATTERN.match(stripped)
        if not match:
            continue

        timestamp = match.group("ts")
        rest = match.group("rest").strip()
        speaker, dialogue = _split_speaker_and_text(rest)

        if not dialogue:
            logger.warning("Skipping inline timestamp {} with no dialogue", timestamp)
            continue

        segments.append(_build_segment(timestamp, dialogue, speaker))

    return segments


def _parse_cue_based(text: str, *, is_vtt: bool) -> list[TranscriptSegment]:
    """Parse SRT or VTT cue-based transcripts."""
    pattern = VTT_CUE_PATTERN if is_vtt else SRT_CUE_PATTERN
    segments: list[TranscriptSegment] = []
    lines = text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if not line or line.upper() == "WEBVTT" or line.isdigit():
            i += 1
            continue

        match = pattern.match(line)
        if not match:
            i += 1
            continue

        timestamp = match.group("start")
        i += 1
        dialogue_lines: list[str] = []

        while i < len(lines):
            candidate = lines[i].strip()
            if not candidate:
                i += 1
                break
            if pattern.match(candidate) or candidate.isdigit():
                break
            dialogue_lines.append(candidate)
            i += 1

        if not dialogue_lines:
            continue

        combined = " ".join(dialogue_lines)
        speaker, dialogue = _split_speaker_and_text(combined)
        segments.append(_build_segment(timestamp, dialogue or combined, speaker))

    return segments


def parse_transcript(
    text: str, *, format_hint: TranscriptFormat | None = None
) -> list[TranscriptSegment]:
    """Parse raw transcript text into structured segments.

    Automatically detects the input format unless a hint is provided.
    Supported formats: YouTube multiline, inline bracket, inline timestamp,
    SRT, and VTT.

    Args:
        text: Raw transcript content copied from YouTube or subtitle files.
        format_hint: Optional format override for ambiguous inputs.

    Returns:
        Chronologically ordered list of :class:`TranscriptSegment` objects.

    Raises:
        TranscriptParseError: If parsing fails or no segments are found.

    Example:
        >>> raw = "00:00:13\\n\\nPlayer A:\\nI didn't kill him."
        >>> segments = parse_transcript(raw)
        >>> segments[0].speaker
        'Player A'
    """
    if not text or not text.strip():
        raise TranscriptParseError("Transcript text is empty")

    detected = format_hint or detect_format(text)
    logger.info("Parsing transcript using format: {}", detected.value)

    try:
        if detected == TranscriptFormat.VTT:
            segments = _parse_cue_based(text, is_vtt=True)
        elif detected == TranscriptFormat.SRT:
            segments = _parse_cue_based(text, is_vtt=False)
        elif detected == TranscriptFormat.INLINE_BRACKET:
            segments = _parse_inline_lines(text, bracketed=True)
        elif detected == TranscriptFormat.INLINE_TIMESTAMP:
            segments = _parse_inline_lines(text, bracketed=False)
        else:
            segments = _parse_youtube_multiline(text)
    except ValueError as exc:
        logger.exception("Failed to parse transcript timestamps")
        raise TranscriptParseError(str(exc), format_hint=detected.value) from exc

    if not segments:
        raise TranscriptParseError(
            "No transcript segments found. Check the format and content.",
            format_hint=detected.value,
        )

    segments.sort(key=lambda segment: segment.seconds)
    logger.info("Parsed {} transcript segments", len(segments))
    return segments


def parse_transcript_file(
    path: str, *, format_hint: TranscriptFormat | None = None
) -> list[TranscriptSegment]:
    """Read and parse a transcript from a file path.

    Args:
        path: Filesystem path to a plain-text transcript file.
        format_hint: Optional format override.

    Returns:
        Parsed transcript segments.

    Raises:
        TranscriptParseError: If the file cannot be read or parsed.
    """
    logger.info("Reading transcript file: {}", path)
    try:
        with open(path, encoding="utf-8") as handle:
            content = handle.read()
    except OSError as exc:
        logger.error("Failed to read transcript file {}: {}", path, exc)
        raise TranscriptParseError(f"Could not read file: {path}") from exc

    return parse_transcript(content, format_hint=format_hint)
