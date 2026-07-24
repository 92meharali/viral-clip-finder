# Clip Ranking Criteria

This file documents the ranking criteria used by the clip ranker.
Weights and thresholds are applied in `app/services/clip_ranker.py`.

## Scoring factors

| Factor | Weight | Description |
|--------|--------|-------------|
| Viral score | 40% | LLM-assigned viral potential (0-10) |
| Emotion intensity | 25% | High-impact emotions score higher |
| Dialogue density | 20% | More dialogue per second ranks higher |
| Length fit | 15% | Clips near 30-60s score highest |

## High-intensity emotions

betrayal, shock, accusation, anger, reveal, suspense, cliffhanger, laughter, humor, drama, voting, strategy, argument, lie, emotional

## Selection rules

- Remove clips with more than 50% temporal overlap (keep higher rank score).
- Prefer emotional variety when selecting the final top N (unseen emotions receive a +1.0 selection bonus).
- Clips outside min/max duration receive a length score of 0.
