# Module 10 — FFmpeg Renderer

Module 10 executes the crop plan. It does not make composition decisions.

## Goals

- Render 9:16 vertical output
- Support 1080×1920 and configurable target sizes
- Optional blurred background mode
- Interpolate sparse crop keyframes to full render FPS

## Architecture

```
CropPlan
  +
Source video
  ↓
FFmpegReframeRenderer
  ├── interpolate crop keyframes
  ├── merge render segments
  └── ffmpeg crop + scale (+ optional blur)
  ↓
ReframeRenderResult
```

## Render strategy

1. Interpolate sparse crop keyframes to `REFRAME_RENDER_FPS`
2. Merge consecutive similar crops into segments
3. Render one or more ffmpeg segments
4. Concatenate multi-segment outputs when needed

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REFRAME_RENDERER` | `ffmpeg` | Renderer backend |
| `REFRAME_RENDER_FPS` | `30` | Interpolation FPS |
| `REFRAME_SEGMENT_MERGE_THRESHOLD` | `5.0` | Segment merge threshold |
| `REFRAME_RENDER_PRESET` | `fast` | x264 preset |
| `REFRAME_RENDER_CRF` | `23` | Output quality |
| `REFRAME_BLUR_BACKGROUND` | `false` | Blurred background mode |

## Full pipeline usage

```python
from app.reframe.pipeline import ReframePipelineService

service = ReframePipelineService()
try:
    result = service.render_video(
        "episode.mp4",
        "output/clip1_vertical.mp4",
        transcript_segments=segments,
    )
finally:
    service.close()
```

## Tradeoffs

- Segment-based rendering is robust and testable; highly dynamic single-pass expression crops are deferred.
- Multi-segment renders re-encode video for correctness across crop changes.
