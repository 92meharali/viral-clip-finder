# LLM Transcript Windowing

Long transcripts must never be sent to the LLM in a single request. The windowing layer splits transcripts into overlapping time ranges, analyzes each window independently, and merges the results before ranking.

## Flow

```
Full transcript
    → generate_transcript_windows()
    → analyze each window with ClipAnalyzer
    → merge_window_clips()
    → rank_clips()
```

Segment boundaries are always preserved — dialogue lines are never split mid-sentence.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_WINDOW_ENABLED` | `true` | Enable windowed analysis for long transcripts |
| `LLM_WINDOW_SIZE_SECONDS` | `600` | Maximum window size sent to the LLM (10 minutes) |
| `LLM_WINDOW_OVERLAP_SECONDS` | `60` | Overlap between consecutive windows |

When the transcript duration is less than or equal to `LLM_WINDOW_SIZE_SECONDS`, a single window is used and behavior matches the previous full-transcript analysis.

## Usage

```python
from app.providers.factory import get_clip_analyzer
from app.services.transcript_windows import analyze_transcript_with_windows

analyzer = get_clip_analyzer()
clips, window_count = analyze_transcript_with_windows(
    analyzer,
    segments,
    total_duration_seconds=3600.0,
)

print(f"Analyzed {window_count} windows, found {len(clips)} clips")
```

## Integration points

| Module | Usage |
|--------|-------|
| `app/services/analysis/pipeline.py` | API analysis jobs |
| `app/services/batch_exporter.py` | CLI batch export |

## Overlap and deduplication

Windows overlap so moments near boundaries are not missed. Exact duplicate clips (same start/end) are removed during merge. Near-duplicate overlap is handled later by the ranking service's deduplication pass.

## Testing

```bash
uv run pytest tests/test_transcript_windows.py -q
```
