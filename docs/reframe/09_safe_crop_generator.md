# Module 9 — Safe Crop Generator

Module 9 converts smoothed camera states into final crop rectangles that stay inside the source frame and protect faces.

## Goals

- Stay inside source video bounds
- Preserve target aspect ratio
- Avoid clipping tracked faces
- Produce render-ready segments

## Architecture

```
Smoothed CameraPath
  +
TrackingResult
  ↓
SafeCropGenerator
  ↓
CropPlan
  ├── CropFrame[]
  └── CropSegment[]
```

## Safety rules

- Clamp crop rectangles to source dimensions
- Expand or shift crops to include face bounding boxes plus padding
- Merge similar consecutive crops into ffmpeg render segments

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CROP_GENERATOR` | `safe` | Crop generator backend |
| `CROP_FACE_SAFETY_PADDING` | `20` | Face padding in pixels |
| `CROP_MIN_FACE_VISIBILITY` | `0.95` | Minimum visible face area ratio |
| `REFRAME_SEGMENT_MERGE_THRESHOLD` | `5.0` | Segment merge threshold in pixels |

## Usage

```python
from app.reframe import generate_crop_plan, smooth_camera_path

crop_plan = generate_crop_plan(smoothed_path, tracking)
```
