# Viral Reel Generator

Convert long YouTube videos into viral short-form clips with AI-powered moment detection, automatic cutting, vertical cropping, captions, and export-ready metadata.

## Status

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Transcript processing | Done |
| 2 | LLM viral moment analysis | Done |
| 3 | Clip ranking | Done |
| 4 | Video cutting (FFmpeg) | Done |
| 5 | Vertical cropping | Done |
| 6 | Subtitle generation | Done |
| 7 | Metadata generation | Done |
| 8 | Quality checks | Done |
| 9 | Batch export mode | Done |

## Tech Stack

- **Python 3.12** with [uv](https://github.com/astral-sh/uv) for dependency management
- **FastAPI** + **Pydantic** for the API layer (coming soon)
- **OpenAI SDK** for viral moment detection (Phase 2)
- **FFmpeg** for video processing (Phase 4+)
- **Typer** for CLI
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

## Phase 2: LLM Viral Moment Analysis

The clip analyzer sends parsed transcript segments to OpenAI and returns ranked viral clip candidates with hooks, emotions, and scores.

### Usage

```python
from app.services.transcript_parser import parse_transcript_file
from app.llm.analyzer import analyze_transcript

segments = parse_transcript_file("transcript.txt")
clips = analyze_transcript(segments)

for clip in clips:
    print(clip.model_dump())
# {
#   'start': '00:00:13', 'end': '00:00:45',
#   'viral_score': 9.7, 'emotion': 'betrayal',
#   'hook': 'He trusted the wrong player.', ...
# }
```

### Configuration

Set your OpenAI API key in `.env`:

```bash
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o
MAX_CLIPS=10
```

Prompts are stored in `app/prompts/` and loaded at runtime — never hardcoded.

See [docs/llm_analysis.md](docs/llm_analysis.md) for full module documentation.

## Phase 3: Clip Ranking

The clip ranker scores, deduplicates, and selects the top N viral clips using emotion intensity, dialogue density, length fit, and variety.

### Usage

```python
from app.services.transcript_parser import parse_transcript_file
from app.llm.analyzer import analyze_transcript
from app.services.clip_ranker import rank_clips

segments = parse_transcript_file("transcript.txt")
clips = analyze_transcript(segments)
ranked = rank_clips(clips, segments, top_n=5)

for clip in ranked:
    print(f"[{clip.rank_score:.1f}] {clip.hook}")
```

See [docs/clip_ranking.md](docs/clip_ranking.md) for full module documentation.

## Phase 4: Video Cutting

Extract ranked clips from a source video using FFmpeg. Uses stream copy by default with automatic re-encode fallback.

### Prerequisites

```bash
brew install ffmpeg   # macOS
ffmpeg -version
```

### Usage

```python
from app.video.cutter import cut_clips

extracted = cut_clips("game_night.mp4", ranked, output_dir="output")

for clip in extracted:
    print(clip.output_path)  # output/clip1.mp4, output/clip2.mp4, ...
```

Supports **MP4**, **MOV**, and **MKV** source formats.

See [docs/video_cutting.md](docs/video_cutting.md) for full module documentation.

## Phase 5: Vertical Cropping

Convert clips to 1080×1920 vertical format for TikTok, Instagram Reels, and YouTube Shorts.

### Usage

```python
from app.video.cropper import crop_to_vertical

# Center crop (default) — best for landscape with centered action
vertical = crop_to_vertical(extracted, output_dir="output")

# Blurred background — keeps full frame visible with cinematic blur
vertical = crop_to_vertical(extracted, blurred_background=True)

for clip in vertical:
    print(clip.output_path)  # output/clip1_vertical.mp4, ...
```

See [docs/vertical_cropping.md](docs/vertical_cropping.md) for full module documentation.

## Phase 6: Subtitle Generation

Generate SRT caption files from transcript timestamps and optionally burn styled subtitles into videos.

### Usage

```python
from app.video.subtitles import generate_subtitles
from app.video.subtitle_burner import burn_subtitles
from app.models.subtitle import SubtitleStyle, SubtitlePosition

# Generate SRT files aligned to clip windows
subtitles = generate_subtitles(segments, extracted, output_dir="output")

# Burn subtitles into vertical video (optional)
style = SubtitleStyle(size=28, color="white", position=SubtitlePosition.BOTTOM)
burn_subtitles(vertical[0].output_path, subtitles[0].srt_path, style=style)
```

See [docs/subtitle_generation.md](docs/subtitle_generation.md) for full module documentation.

## Phase 7: Metadata Generation

Generate platform-ready titles, hooks, descriptions, hashtags, CTAs, and SEO keywords for each clip using OpenAI.

### Usage

```python
from app.llm.metadata_generator import generate_metadata

metadata = generate_metadata(ranked, segments, output_dir="output")

for item in metadata:
    print(item.title)
    print(item.title_variations)  # multiple title options
    print(item.json_path)         # output/clip1_metadata.json
```

See [docs/metadata_generation.md](docs/metadata_generation.md) for full module documentation.

## Phase 8: Quality Checks

Filter out clips that are too short, too long, too silent, low-confidence, or contain repeated dialogue before export.

### Usage

```python
from app.services.quality_checker import filter_quality_clips

passed, report = filter_quality_clips(ranked, segments)

print(f"{len(passed)}/{report.total} clips passed")
for rejection in report.rejected:
    print(rejection.index, [issue.code for issue in rejection.issues])
```

See [docs/quality_checks.md](docs/quality_checks.md) for full module documentation.

## Phase 9: Batch Export Mode

Run the complete pipeline with one command — from transcript to upload-ready folder.

### CLI

```bash
uv run viral-reel export \
  --video game_night.mp4 \
  --transcript transcript.txt \
  --output output/ \
  --top-n 5

# Optional flags
uv run viral-reel export -v game.mp4 -t transcript.txt --blur --burn-subtitles
```

### Python API

```python
from app.services.batch_exporter import BatchExportOptions, run_batch_export

result = run_batch_export(
    "game_night.mp4",
    "transcript.txt",
    output_dir="output",
    options=BatchExportOptions(top_n=5, blurred_background=True),
)

print(result.manifest.manifest_path)  # output/manifest.json
```

Output folder contains videos, SRT files, per-clip metadata JSON, and a master `manifest.json`.

See [docs/batch_export.md](docs/batch_export.md) for full module documentation.

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
