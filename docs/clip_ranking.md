# Clip Ranking

## Purpose

Rank and filter LLM-detected viral clips to return the best top N moments. Considers emotion intensity, dialogue density, clip length, and emotional variety while removing duplicates.

## Modules

| Module | Responsibility |
|--------|----------------|
| `app/services/clip_ranker.py` | Scoring, deduplication, and top-N selection |
| `app/models/clip.py` | `RankedClip` model with ranking metadata |
| `app/prompts/ranking.md` | Human-readable ranking criteria reference |

## Inputs

- **Clips**: `list[ViralClip]` from Phase 2 LLM analysis
- **Segments**: `list[TranscriptSegment]` from Phase 1 (for dialogue density)
- **top_n**: Maximum clips to return (defaults to `MAX_CLIPS` from config)

## Outputs

A list of `RankedClip` objects with composite scores:

```json
{
  "start": "00:00:13",
  "end": "00:00:45",
  "viral_score": 9.7,
  "rank_score": 8.42,
  "emotion": "betrayal",
  "emotion_intensity": 1.0,
  "dialogue_density": 12.5,
  "length_score": 1.0,
  "hook": "He trusted the wrong player.",
  "summary": "Alliance breaks down."
}
```

## Scoring Formula

| Factor | Weight | Source |
|--------|--------|--------|
| Viral score | 40% | LLM-assigned score (0-10) |
| Emotion intensity | 25% | Keyword-matched emotion weights |
| Dialogue density | 20% | Characters per second in clip window |
| Length fit | 15% | Proximity to ideal 30-60s range |

## Selection Pipeline

1. **Score** — Compute composite `rank_score` for every clip
2. **Deduplicate** — Remove clips with ≥50% temporal overlap (keep higher score)
3. **Variety select** — Greedily pick top N, boosting unseen emotions

## Example

```python
from app.services.transcript_parser import parse_transcript_file
from app.llm.analyzer import analyze_transcript
from app.services.clip_ranker import rank_clips

segments = parse_transcript_file("transcript.txt")
clips = analyze_transcript(segments)
ranked = rank_clips(clips, segments, top_n=5)

for clip in ranked:
    print(f"[{clip.rank_score:.1f}] {clip.hook} ({clip.emotion})")
```

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `ClipRankingError: empty clip list` | No clips to rank | Run LLM analysis first |
| Too few clips returned | Heavy overlap between candidates | Normal — dedup removed similar moments |
| Low `length_score` | Clip outside 20-90s or far from 30-60s ideal | Adjust clip boundaries in LLM prompt |

## Tests

```bash
uv run pytest tests/test_clip_ranker.py -v
```
