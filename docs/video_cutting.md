# Video Cutting

## Purpose

Extract ranked viral clips from a source video using FFmpeg. Produces numbered output files (`clip1.mp4`, `clip2.mp4`, ...) with stream copy by default and automatic re-encode fallback.

## Modules

| Module | Responsibility |
|--------|----------------|
| `app/video/ffmpeg.py` | FFmpeg/FFprobe wrappers, validation |
| `app/video/cutter.py` | Clip extraction orchestration |
| `app/models/export.py` | `ExtractedClip` output metadata |

## Inputs

- **Source video**: MP4, MOV, or MKV file
- **Clips**: `list[ViralClip]` or `list[RankedClip]` with start/end timestamps
- **Output directory**: Where to write extracted files (default: `output/`)

## Outputs

A list of `ExtractedClip` objects:

```json
{
  "index": 1,
  "source_path": "/videos/game_night.mp4",
  "output_path": "output/clip1.mp4",
  "start": "00:00:13",
  "end": "00:00:45",
  "start_seconds": 13.0,
  "end_seconds": 45.0,
  "duration_seconds": 32.0,
  "reencoded": false
}
```

## FFmpeg Strategy

1. **Stream copy** (default) — `-c copy` for fast, lossless extraction
2. **Re-encode fallback** — H.264 + AAC if stream copy fails (e.g. non-keyframe cut)

Clips whose end timestamp exceeds the source video duration are skipped with a warning.

## Example

```python
from app.services.transcript_parser import parse_transcript_file
from app.llm.analyzer import analyze_transcript
from app.services.clip_ranker import rank_clips
from app.video.cutter import cut_clips

segments = parse_transcript_file("transcript.txt")
clips = analyze_transcript(segments)
ranked = rank_clips(clips, segments, top_n=5)
extracted = cut_clips("game_night.mp4", ranked, output_dir="output")

for clip in extracted:
    print(f"{clip.output_path} ({'re-encoded' if clip.reencoded else 'stream copy'})")
```

## Prerequisites

FFmpeg must be installed and available on PATH:

```bash
# macOS
brew install ffmpeg

# Verify
ffmpeg -version
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OUTPUT_DIR` | `output` | Default output directory |
| `FFMPEG_PATH` | `ffmpeg` | Path to ffmpeg binary |
| `FFPROBE_PATH` | `ffprobe` | Path to ffprobe binary |

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `ffmpeg not found` | FFmpeg not installed | Install ffmpeg and add to PATH |
| `Source video not found` | Invalid file path | Check the source video path |
| `Unsupported video format` | Not MP4/MOV/MKV | Convert source or use supported format |
| `No clips were extracted` | All timestamps exceed video length | Verify timestamps match the video |
| `ffmpeg command failed` | Corrupt video or invalid timestamps | Check source file integrity |

## Tests

```bash
uv run pytest tests/test_video_cutter.py -v
```

Tests mock subprocess calls — no FFmpeg installation required to run the test suite.
