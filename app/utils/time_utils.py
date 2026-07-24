"""Timestamp parsing and formatting utilities."""

import re
from loguru import logger

# Matches HH:MM:SS, MM:SS, with optional milliseconds (comma or dot).
TIMESTAMP_PATTERN = re.compile(
    r"(?P<hours>\d{1,2}):(?P<minutes>\d{2}):(?P<seconds>\d{2})"
    r"(?:[.,](?P<millis>\d{1,3}))?"
    r"|"
    r"(?P<short_minutes>\d{1,2}):(?P<short_seconds>\d{2})"
    r"(?:[.,](?P<short_millis>\d{1,3}))?"
)

TIMESTAMP_LINE_PATTERN = re.compile(
    r"^\[?(?P<ts>" r"(?:\d{1,2}:)?\d{1,2}:\d{2}(?:[.,]\d{1,3})?" r")\]?"
)


def parse_timestamp(timestamp: str) -> float:
    """Convert a timestamp string to total seconds.

    Supports HH:MM:SS, MM:SS, and optional millisecond suffixes
    using either comma (SRT) or dot (VTT) separators.

    Args:
        timestamp: Timestamp string such as ``00:01:23`` or ``01:23,500``.

    Returns:
        Total elapsed seconds as a float.

    Raises:
        ValueError: If the timestamp format is invalid.

    Example:
        >>> parse_timestamp("00:01:23")
        83.0
        >>> parse_timestamp("01:23,500")
        83.5
    """
    cleaned = timestamp.strip()
    match = TIMESTAMP_PATTERN.fullmatch(cleaned)
    if not match:
        logger.error("Invalid timestamp format: {}", cleaned)
        raise ValueError(f"Invalid timestamp format: {cleaned!r}")

    if match.group("hours") is not None:
        hours = int(match.group("hours"))
        minutes = int(match.group("minutes"))
        seconds = int(match.group("seconds"))
        millis = match.group("millis")
    else:
        hours = 0
        minutes = int(match.group("short_minutes"))
        seconds = int(match.group("short_seconds"))
        millis = match.group("short_millis")

    total = hours * 3600 + minutes * 60 + seconds
    if millis:
        total += int(millis.ljust(3, "0")[:3]) / 1000

    return float(total)


def format_timestamp(seconds: float) -> str:
    """Format seconds as an HH:MM:SS timestamp string.

    Args:
        seconds: Elapsed time in seconds (non-negative).

    Returns:
        Timestamp formatted as ``HH:MM:SS``.

    Example:
        >>> format_timestamp(83.0)
        '00:01:23'
    """
    if seconds < 0:
        raise ValueError(f"Seconds must be non-negative, got {seconds}")

    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def extract_timestamp_from_line(line: str) -> str | None:
    """Extract the first timestamp token from a line, if present.

    Args:
        line: A single line of transcript text.

    Returns:
        The timestamp string without brackets, or ``None``.
    """
    match = TIMESTAMP_LINE_PATTERN.match(line.strip())
    if not match:
        return None
    return match.group("ts")
