# AI Provider Architecture

The AI layer is fully decoupled from the rest of the pipeline via the
`ClipAnalyzer` interface in `app/providers/base.py`. Application code never
imports OpenAI, Cursor, or any other model SDK directly.

## Providers

| Provider | Module | API required |
|----------|--------|--------------|
| `cursor` | `app/providers/cursor_manual.py` | No |
| `openai` | `app/providers/openai.py` | Yes (`OPENAI_API_KEY`) |
| `gemini` | `app/providers/gemini.py` | Yes (`GEMINI_API_KEY`) |

Configure the active provider in `.env`:

```bash
AI_PROVIDER=gemini
GEMINI_API_KEY=your-key-from-aistudio
GEMINI_MODEL=gemini-2.5-flash-lite
```

### Gemini quota troubleshooting

If you see `429 RESOURCE_EXHAUSTED` with `limit: 0`, your API key has **no free-tier
quota** for that model. Common fixes:

1. Create a key at [Google AI Studio](https://aistudio.google.com/apikey) (keys usually start with `AIza`)
2. Use `GEMINI_MODEL=gemini-2.5-flash-lite` (lighter model, better free-tier limits)
3. If quota is still zero, enable billing in AI Studio — free-tier limits still apply, but Google may require a billing account on the project

Transient rate limits (temporary 429s) are retried automatically.

## ClipAnalyzer interface

```python
from app.providers import get_clip_analyzer

analyzer = get_clip_analyzer()
clips = analyzer.analyze_transcript(segments)
ranked = analyzer.rank_candidates(clips, segments, top_n=5)
metadata = analyzer.generate_metadata_batch(ranked, segments, output_dir="output/")
```

Methods:

- `analyze_transcript()` — detect viral clip candidates
- `rank_candidates()` — deterministic composite ranking (default)
- `generate_metadata()` — publishing metadata for one clip
- `generate_metadata_batch()` — metadata for multiple clips

## Cursor manual workflow

Zero external APIs. The app exports a prompt; you run it in Cursor; you paste
the JSON response back.

### 1. Export prompt

```bash
uv run viral-reel ai export-prompt -t transcript.txt -o analysis_prompt.md
```

### 2. Run in Cursor

Paste `analysis_prompt.md` into Cursor. The prompt includes the transcript,
instructions, and the exact JSON schema to return.

### 3. Validate response

```bash
uv run viral-reel ai validate-response -r analysis_response.json
```

### 4. Continue export

```bash
uv run viral-reel export \
  -v video.mp4 \
  -t transcript.txt \
  --provider cursor \
  --analysis-response analysis_response.json
```

If no response file exists, export writes `output/analysis_prompt.md` and stops
with a clear error message.

## JSON formats

Clip analysis accepts:

```json
{
  "clips": [
    {
      "start": "00:12:31",
      "end": "00:13:08",
      "score": 9.8,
      "emotion": "betrayal",
      "hook": "He trusted the wrong player.",
      "reason": "Major alliance collapse."
    }
  ]
}
```

Or a top-level array with the same clip objects. The `score` field is an alias
for `viral_score`. If `summary` is omitted, `reason` is used.

Validation errors include field-level Pydantic details.

## Prompt templates

All prompts live in `app/prompts/`:

| File | Purpose |
|------|---------|
| `clip_analysis.md` | Viral moment detection |
| `metadata.md` | Publishing metadata |
| `ranking.md` | Ranking criteria documentation |

JSON schema examples live in `app/prompts/schemas/`.

Legacy names (`clip_selection`, `metadata_generation`) still resolve via
`app/utils/prompt_loader.py`.

## Adding a new provider

1. Create `app/providers/your_provider.py` implementing `ClipAnalyzer`
2. Register it in `app/providers/factory.py`
3. Add tests in `tests/test_your_provider.py`

The video pipeline (`app/video/`) and ranking service (`app/services/clip_ranker.py`)
remain independent of the AI provider.

## Future enrichment hooks

Interfaces for scene detection, audio analysis, emotion detection, frame
sampling, and face tracking are defined in `app/services/enrichment/base.py`.
These will plug into the candidate window generator in a future phase.
