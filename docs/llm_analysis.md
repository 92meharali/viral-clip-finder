# LLM Clip Analysis

## Purpose

Analyze parsed transcript segments with OpenAI to detect viral short-form clip moments. Returns structured JSON with timestamps, scores, emotions, hooks, and summaries.

## Modules

| Module | Responsibility |
|--------|----------------|
| `app/core/config.py` | Environment-based settings (API key, model, clip limits) |
| `app/models/clip.py` | `ViralClip`, `ViralClipBase`, `ClipAnalysisResponse` |
| `app/prompts/clip_selection.md` | Prompt template for viral moment detection |
| `app/utils/prompt_loader.py` | Load and render prompt templates |
| `app/llm/transcript_formatter.py` | Format segments for LLM input |
| `app/llm/client.py` | OpenAI client factory |
| `app/llm/analyzer.py` | Core analysis service |

## Inputs

- **Transcript segments**: Output from Phase 1 (`list[TranscriptSegment]`)
- **Configuration**: `.env` file with OpenAI credentials and clip settings

## Outputs

A list of `ViralClip` objects sorted by `viral_score` (highest first):

```json
{
  "start": "00:00:13",
  "end": "00:00:45",
  "start_seconds": 13.0,
  "end_seconds": 45.0,
  "duration_seconds": 32.0,
  "reason": "A major alliance falls apart.",
  "viral_score": 9.7,
  "emotion": "betrayal",
  "hook": "He trusted the wrong player.",
  "summary": "One player turns on their ally during a heated vote."
}
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | OpenAI API key (required) |
| `OPENAI_MODEL` | `gpt-4o` | Model to use for analysis |
| `OPENAI_TEMPERATURE` | `0.7` | Sampling temperature |
| `MAX_CLIPS` | `10` | Max clips to return per analysis |
| `MIN_CLIP_DURATION_SECONDS` | `20` | Minimum clip length |
| `MAX_CLIP_DURATION_SECONDS` | `90` | Maximum clip length |

## Example

```python
from app.services.transcript_parser import parse_transcript_file
from app.llm.analyzer import analyze_transcript

segments = parse_transcript_file("transcript.txt")
clips = analyze_transcript(segments)

for clip in clips:
    print(f"[{clip.viral_score}] {clip.hook} ({clip.start} → {clip.end})")
```

## Prompt Design

Prompts live in `app/prompts/` as Markdown files and are never hardcoded in Python. The `clip_selection.md` template uses `{{variable}}` placeholders for:

- `transcript` — formatted dialogue with timestamps
- `max_clips` — clip count limit
- `min_duration` / `max_duration` — duration constraints

To customize detection behavior, edit the prompt file rather than the Python code.

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `LLMAnalysisError: API key is not configured` | Missing `OPENAI_API_KEY` | Add key to `.env` |
| `LLMAnalysisError: empty transcript` | No segments provided | Parse transcript first (Phase 1) |
| `LLMAnalysisError: invalid JSON` | Model returned malformed output | Retry or switch model |
| `LLMAnalysisError: API call failed` | Network or API error | Check connectivity and API status |
| `PromptLoadError` | Missing prompt template | Ensure `app/prompts/clip_selection.md` exists |

## Tests

```bash
uv run pytest tests/test_clip_analyzer.py tests/test_clip_models.py -v
```

Tests mock the OpenAI API — no API key required to run the test suite.
