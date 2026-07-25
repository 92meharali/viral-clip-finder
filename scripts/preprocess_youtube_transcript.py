"""Convert YouTube copy-paste transcript format to inline timestamps."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from app.utils.time_utils import format_timestamp

SHORT_PATTERN = re.compile(r"^(\d+):(\d{2})\d{2} seconds(.*)$")
LONG_PATTERN = re.compile(r"^(\d+):(\d{2})\d+ minutes?, \d+ seconds(.*)$")
CHAPTER_PATTERN = re.compile(r"^Chapter \d+:")


def parse_line(line: str) -> tuple[float, str] | None:
    """Parse a single YouTube transcript line into seconds and text."""
    stripped = line.strip()
    if not stripped or CHAPTER_PATTERN.match(stripped):
        return None

    match = SHORT_PATTERN.match(stripped) or LONG_PATTERN.match(stripped)
    if not match:
        return None

    minutes = int(match.group(1))
    seconds = int(match.group(2))
    text = match.group(3).strip()
    if not text or text in {"[music]", "[laughter]"}:
        return None

    return minutes * 60 + seconds, text


def convert(raw_text: str) -> str:
    """Convert raw YouTube transcript text to inline timestamp format."""
    lines: list[str] = []
    for line in raw_text.splitlines():
        parsed = parse_line(line)
        if parsed is None:
            continue
        total_seconds, text = parsed
        lines.append(f"{format_timestamp(total_seconds)} {text}")
    return "\n".join(lines) + "\n"


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: preprocess_youtube_transcript.py <input> <output>")

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    output_path.write_text(convert(input_path.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
