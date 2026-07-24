# Batch Export Mode

## Purpose

Orchestrate the full viral reel pipeline in a single command: transcript → clips → videos → subtitles → metadata → upload-ready folder with `manifest.json`.

## Modules

| Module | Responsibility |
|--------|----------------|
| `app/services/batch_exporter.py` | Full pipeline orchestration |
| `app/models/batch.py` | `BatchExportManifest`, `ExportedClipBundle` |
| `app/cli.py` | Typer CLI (`viral-reel export`) |

## Pipeline

```
Transcript file
    ↓ parse
LLM clip analysis
    ↓ rank (top N)
Quality filter
    ↓ cut (FFmpeg)
Vertical crop (1080×1920)
    ↓ subtitles (SRT)
Metadata generation (LLM)
    ↓
manifest.json + clip artifacts
```

## Output Folder

```
output/
├── manifest.json
├── clip1.mp4
├── clip1_vertical.mp4
├── clip1.srt
├── clip1_metadata.json
├── clip2.mp4
├── clip2_vertical.mp4
...
```

## CLI Usage

```bash
# Full batch export
uv run viral-reel export \
  --video game_night.mp4 \
  --transcript transcript.txt \
  --output output/ \
  --top-n 5

# With blurred background and burned subtitles
uv run viral-reel export -v game.mp4 -t transcript.txt -o output/ --blur --burn-subtitles

# Parse transcript only
uv run viral-reel analyze transcript.txt
```

## Python API

```python
from app.services.batch_exporter import BatchExportOptions, run_batch_export

result = run_batch_export(
    "game_night.mp4",
    "transcript.txt",
    output_dir="output",
    options=BatchExportOptions(top_n=5, blurred_background=True),
)

print(result.manifest.manifest_path)
print(f"Exported {result.manifest.clips_exported} clips")
```

## Manifest Format

```json
{
  "source_video": "/path/to/game_night.mp4",
  "transcript_source": "/path/to/transcript.txt",
  "output_dir": "output",
  "clips_analyzed": 12,
  "clips_ranked": 5,
  "clips_exported": 4,
  "clips_rejected_quality": 1,
  "quality_rejections": [],
  "clips": [
    {
      "index": 1,
      "clip_start": "00:00:10",
      "clip_end": "00:00:50",
      "viral_score": 9.5,
      "emotion": "betrayal",
      "video_path": "output/clip1.mp4",
      "vertical_path": "output/clip1_vertical.mp4",
      "srt_path": "output/clip1.srt",
      "metadata_path": "output/clip1_metadata.json",
      "title": "He Trusted The Wrong Person...",
      "hook": "He thought they were allies.",
      "hashtags": ["#mafia", "#betrayal"]
    }
  ],
  "manifest_path": "output/manifest.json",
  "created_at": "2026-07-25T03:00:00Z"
}
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `top_n` | `MAX_CLIPS` | Max clips to rank and export |
| `blurred_background` | `false` | Blurred background vertical crop |
| `burn_subtitles` | `false` | Burn SRT into vertical videos |
| `include_speaker_in_subtitles` | `true` | Speaker labels in SRT |
| `skip_video_processing` | `false` | Skip FFmpeg (testing only) |

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `BatchExportError: video not found` | Invalid video path | Check source video |
| `BatchExportError: no clips` | LLM found nothing | Review transcript |
| `BatchExportError: No clips passed quality` | All clips rejected | Adjust quality thresholds |
| OpenAI errors | Missing API key | Set `OPENAI_API_KEY` in `.env` |

## Tests

```bash
uv run pytest tests/test_batch_exporter.py -v
```
