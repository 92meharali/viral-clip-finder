# Viral Reel Generator

Convert long YouTube videos into viral short-form clips with AI-powered moment detection, automatic cutting, vertical cropping, captions, and export-ready metadata.

## Status

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Transcript processing | Done |
| 2 | LLM viral moment analysis | Planned |
| 3 | Clip ranking | Planned |
| 4 | Video cutting (FFmpeg) | Planned |
| 5 | Vertical cropping | Planned |
| 6 | Subtitle generation | Planned |
| 7 | Metadata generation | Planned |
| 8 | Quality checks | Planned |
| 9 | Batch export mode | Planned |

## Tech Stack

- **Python 3.12** with [uv](https://github.com/astral-sh/uv) for dependency management
- **FastAPI** + **Pydantic** for the API layer (coming soon)
- **OpenAI SDK** for viral moment detection (Phase 2)
- **FFmpeg** for video processing (Phase 4+)
- **Typer** for CLI (coming soon)
- **pytest** for testing, **ruff** / **black** / **mypy** for code quality

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) installed

### Setup

```bash
# Clone and enter the project
cd viral-reel-generator

# Install dependencies
uv sync --dev

# Copy environment template
cp .env.example .env
```

### Run Tests

```bash
uv run pytest -v
```

## Phase 1: Transcript Processing

The transcript parser accepts manually copied YouTube transcripts and converts them into structured `TranscriptSegment` objects.

### Supported Formats

| Format | Example |
|--------|---------|
| YouTube multiline | Timestamp on its own line, optional speaker, then dialogue |
| Inline bracket | `[00:00:13] Player A: Hello` |
| Inline timestamp | `00:00:13 Player A: Hello` |
| SRT | Standard subtitle file with `-->` cues |
| VTT | WebVTT with `.` millisecond separators |

### Usage

```python
from app.services.transcript_parser import parse_transcript, parse_transcript_file

# Parse raw text
raw = """00:00:13

Player A:
I didn't kill him."""
segments = parse_transcript(raw)

for segment in segments:
    print(segment.model_dump())
# {'start': '00:00:13', 'seconds': 13.0, 'speaker': 'Player A', 'text': "I didn't kill him."}

# Parse from file
segments = parse_transcript_file("transcript.txt")
```

See [docs/transcript_processing.md](docs/transcript_processing.md) for full module documentation.

## Project Structure

```
app/
├── api/           # REST endpoints (Phase 2+)
├── core/          # Exceptions, config
├── llm/           # LLM integration (Phase 2)
├── models/        # Data models
├── prompts/       # Prompt templates (Phase 2)
├── schemas/       # API schemas
├── services/      # Business logic
├── storage/       # Persistence (SQLite)
├── utils/         # Shared utilities
└── video/         # FFmpeg operations (Phase 4+)
docs/              # Module documentation
tests/             # Test suite
scripts/           # Utility scripts
```

## Development

```bash
# Format and lint
uv run black app tests
uv run ruff check app tests

# Type check
uv run mypy app
```

## License

MIT
