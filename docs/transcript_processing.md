# Transcript Processing

## Purpose

Parse manually copied YouTube transcripts (and common subtitle formats) into structured `TranscriptSegment` objects that downstream phases use for LLM analysis, clip cutting, and caption generation.

## Modules

| Module | Responsibility |
|--------|----------------|
| `app/models/transcript.py` | `TranscriptSegment` Pydantic model |
| `app/utils/time_utils.py` | Timestamp parsing and formatting |
| `app/services/transcript_parser.py` | Multi-format detection and parsing |
| `app/core/exceptions.py` | `TranscriptParseError` |

## Inputs

- **Raw text**: A string copied from YouTube's transcript panel or exported from a subtitle file.
- **File path** (optional): A `.txt`, `.srt`, or `.vtt` file on disk.

## Outputs

A chronologically sorted list of `TranscriptSegment` objects:

```json
{
  "start": "00:00:13",
  "seconds": 13.0,
  "speaker": "Player A",
  "text": "I didn't kill him."
}
```

| Field | Type | Description |
|-------|------|-------------|
| `start` | `str` | Normalized `HH:MM:SS` timestamp |
| `seconds` | `float` | Start time as total seconds |
| `speaker` | `str \| None` | Speaker label when detected |
| `text` | `str` | Dialogue text (whitespace-normalized) |

## Supported Formats

### YouTube Multiline (default)

```
00:00:13

Player A:
I didn't kill him.

00:00:19

Player B:
You're lying.
```

### Inline Bracket

```
[00:00:13] Player A: I didn't kill him.
[00:00:19] Player B: You're lying.
```

### Inline Timestamp

```
00:00:13 Player A: I didn't kill him.
00:00:19 - You're lying.
```

### SRT

```
1
00:00:13,000 --> 00:00:19,000
Player A: I didn't kill him.
```

### VTT

```
WEBVTT

00:00:13.000 --> 00:00:19.000
Player A: I didn't kill him.
```

## Example

```python
from app.services.transcript_parser import parse_transcript

transcript = open("game_night.txt").read()
segments = parse_transcript(transcript)

print(f"Found {len(segments)} segments")
print(segments[0].model_dump_json(indent=2))
```

## Format Detection

The parser auto-detects format using these rules (in order):

1. `WEBVTT` header → VTT
2. `-->` cue lines with comma millis → SRT
3. Majority of lines start with `[` → inline bracket
4. Majority of lines start with a timestamp → inline timestamp
5. Otherwise → YouTube multiline

Override detection with an explicit hint:

```python
from app.services.transcript_parser import TranscriptFormat, parse_transcript

segments = parse_transcript(text, format_hint=TranscriptFormat.SRT)
```

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `TranscriptParseError: Transcript text is empty` | Blank input | Provide non-empty transcript text |
| `TranscriptParseError: No transcript segments found` | No recognizable timestamps | Verify format matches one of the supported types |
| `ValueError: Invalid timestamp format` | Malformed timestamp | Use `HH:MM:SS` or `MM:SS` format |
| `TranscriptParseError: Could not read file` | Missing or unreadable file | Check the file exists and path is correct |

## Tests

```bash
uv run pytest tests/test_transcript_parser.py -v
```

Fixture transcripts live in `tests/fixtures/`.
