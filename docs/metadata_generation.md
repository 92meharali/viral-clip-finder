# Metadata Generation

## Purpose

Generate platform-ready publishing metadata for each viral clip using OpenAI. Produces titles, hooks, descriptions, hashtags, CTAs, SEO keywords, and multiple title variations — exported as JSON.

## Modules

| Module | Responsibility |
|--------|----------------|
| `app/llm/metadata_generator.py` | LLM metadata generation and JSON export |
| `app/models/metadata.py` | `ClipMetadata`, `ClipMetadataBase` |
| `app/prompts/metadata_generation.md` | Prompt template for metadata generation |
| `app/llm/json_utils.py` | Shared LLM JSON parsing utilities |

## Inputs

- **Clips**: `ViralClip`, `RankedClip`, or any clip with timing and analysis fields
- **Transcript segments**: Full parsed transcript for clip-window dialogue
- **OpenAI API key**: Required in `.env`

## Outputs

```json
{
  "index": 1,
  "clip_start": "00:00:08",
  "clip_end": "00:00:30",
  "title": "He Trusted The Wrong Person...",
  "title_variations": [
    "The Biggest Betrayal In Mafia",
    "This Vote Changed Everything"
  ],
  "hook": "He thought they were allies.",
  "description": "The alliance shatters in seconds...",
  "hashtags": ["#mafia", "#betrayal", "#gaming", "#viral", "#shorts"],
  "call_to_action": "Who do you think is lying? Comment below.",
  "seo_keywords": ["mafia game", "betrayal moment", "viral gaming clip"],
  "json_path": "output/clip1_metadata.json"
}
```

## Example

```python
from app.services.transcript_parser import parse_transcript_file
from app.llm.analyzer import analyze_transcript
from app.services.clip_ranker import rank_clips
from app.llm.metadata_generator import generate_metadata

segments = parse_transcript_file("transcript.txt")
ranked = rank_clips(analyze_transcript(segments), segments, top_n=5)

metadata = generate_metadata(ranked, segments, output_dir="output")

for item in metadata:
    print(item.title)
    print(item.title_variations)
    print(item.json_path)
```

## Generated Fields

| Field | Description |
|-------|-------------|
| `title` | Primary video title (max ~80 chars) |
| `title_variations` | 2+ alternative title angles |
| `hook` | Scroll-stopping opening line |
| `description` | Post caption (2-4 sentences) |
| `hashtags` | 5+ hashtags (auto-prefixed with `#`) |
| `call_to_action` | Engagement prompt for viewers |
| `seo_keywords` | Search/discovery keywords |

## Prompt Design

The `metadata_generation.md` template receives clip context (timing, emotion, viral score, summary) and the clip-window transcript. Edit the prompt file to tune tone, hashtag strategy, or title style.

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `MetadataGenerationError: empty clip list` | No clips provided | Run analysis and ranking first |
| `MetadataGenerationError: empty transcript` | No segments | Parse transcript first |
| `MetadataGenerationError: API call failed` | OpenAI error | Check API key and connectivity |
| `MetadataGenerationError: invalid JSON` | Malformed LLM output | Retry or switch model |

## Tests

```bash
uv run pytest tests/test_metadata_generator.py tests/test_metadata_models.py -v
```

Tests mock the OpenAI API — no API key required.
