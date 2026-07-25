# Reframe Integration

## Batch export

The batch exporter now uses intelligent reframing by default.

```bash
uv run viral-reel export -v episode.mp4 -t transcript.txt -o output/
```

### Vertical crop modes

| Mode | Setting | Behavior |
|------|---------|----------|
| `reframe` | `VERTICAL_CROP_MODE=reframe` | Full AI reframe pipeline (default) |
| `center` | `VERTICAL_CROP_MODE=center` | Legacy center crop |
| `blur` | `VERTICAL_CROP_MODE=blur` | Blurred background crop |

Override per run:

```python
BatchExportOptions(vertical_crop_mode="center")
```

### Structured episode output

```bash
uv run viral-reel export \
  -v episode.mp4 \
  -t transcript.txt \
  -o output/ \
  --structured \
  --episode-name mafia-tech-legends \
  --crop-mode center
```

Produces:

```
output/mafia-tech-legends/
├── clips/              # horizontal source clips
├── reframe/            # vertical 9:16 clips + metrics JSON
├── metadata/
├── subtitles/
├── analysis.json       # candidate windows + segment count
├── report.md
├── logs/
└── manifest.json
```

Override per run:

```python
BatchExportOptions(structured_output=True, episode_name="mafia-tech-legends")
```

## Candidate windows

Generate ranked clip windows before LLM analysis:

```python
from app.services.candidate_windows import generate_candidate_windows

result = generate_candidate_windows(segments, video_path="episode.mp4")
for window in result.windows:
    print(window.start_seconds, window.end_seconds, window.score, window.labels)
```

Signals come from:

- Transcript dialogue scoring (`TranscriptEnrichment`)
- Scene anchors (`ReframeSceneEnrichment`)

## Evaluation metrics

Each reframed clip writes metrics to `reframe/clipN_metrics.json`:

```python
from app.reframe.metrics import evaluate_reframe

metrics = evaluate_reframe(
    tracking=tracking,
    crop_plan=crop_plan,
    camera_path=smoothed_path,
)
print(metrics.average_face_visibility, metrics.camera_jitter_score)
```

Metrics include:

- Average face visibility
- Clipped face percentage
- Average empty space ratio
- Camera movement distance
- Camera jitter score
- Unnecessary cut count
