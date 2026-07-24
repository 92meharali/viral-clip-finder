# Quality Checks

## Purpose

Validate viral clips before export by rejecting clips that are too short, too long, too silent, low-confidence, or contain repeated dialogue.

## Modules

| Module | Responsibility |
|--------|----------------|
| `app/services/quality_checker.py` | Quality validation and filtering |
| `app/models/quality.py` | `ClipQualityResult`, `QualityFilterResult`, `QualityIssue` |

## Checks Performed

| Check | Code | Default threshold |
|-------|------|-------------------|
| Too short | `too_short` | < 20 seconds |
| Too long | `too_long` | > 90 seconds |
| Too much silence | `too_much_silence` | > 60% estimated silence |
| Low confidence | `low_confidence` | viral score < 5.0 |
| Repeated dialogue | `repeated_dialogue` | Duplicate lines within clip or across batch |

## Inputs

- **Clips**: `ViralClip` or `RankedClip` objects with timing and scores
- **Segments**: Full parsed transcript for silence and dialogue analysis

## Outputs

```json
{
  "passed": [1, 3],
  "rejected": [
    {
      "index": 2,
      "clip_start": "00:00:10",
      "clip_end": "00:00:25",
      "viral_score": 8.0,
      "passed": false,
      "issues": [
        {
          "code": "too_short",
          "message": "Clip duration 15.0s is below minimum 20s"
        }
      ]
    }
  ],
  "total": 3
}
```

## Example

```python
from app.services.quality_checker import filter_quality_clips

passed, report = filter_quality_clips(ranked, segments)

print(f"{len(passed)}/{report.total} clips passed quality checks")
for rejection in report.rejected:
    for issue in rejection.issues:
        print(f"  Clip {rejection.index}: {issue.code} — {issue.message}")
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_CLIP_DURATION_SECONDS` | `20` | Minimum clip length |
| `MAX_CLIP_DURATION_SECONDS` | `90` | Maximum clip length |
| `MIN_VIRAL_SCORE` | `5.0` | Minimum LLM viral score |
| `MAX_SILENCE_RATIO` | `0.6` | Maximum allowed silence fraction |

## Silence Detection

Silence is estimated from transcript segment spacing within the clip window. Gaps between dialogue lines and leading/trailing silence are summed and divided by clip duration. Clips with no dialogue in the window are treated as 100% silent.

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `QualityCheckError: empty clip list` | No clips to check | Run ranking first |
| All clips rejected | Thresholds too strict | Adjust `.env` thresholds |
| Unexpected rejections | Sparse transcript | Verify transcript covers the clip window |

## Tests

```bash
uv run pytest tests/test_quality_checker.py -v
```
