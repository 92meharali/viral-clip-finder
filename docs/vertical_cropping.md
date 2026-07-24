# Vertical Cropping

## Purpose

Convert extracted horizontal clips into 9:16 vertical videos (1080×1920) ready for TikTok, Instagram Reels, and YouTube Shorts. Supports center crop and blurred-background modes.

## Modules

| Module | Responsibility |
|--------|----------------|
| `app/video/filters.py` | FFmpeg filter string builders |
| `app/video/cropper.py` | Vertical crop orchestration |
| `app/video/ffmpeg.py` | `probe_dimensions()` for source size detection |
| `app/models/export.py` | `VerticalClip` output metadata |

## Inputs

- **Clips**: File paths or `ExtractedClip` objects from Phase 4
- **Mode**: Center crop (default) or blurred background
- **Dimensions**: 1080×1920 by default (configurable)

## Outputs

```json
{
  "index": 1,
  "source_path": "output/clip1.mp4",
  "output_path": "output/clip1_vertical.mp4",
  "width": 1080,
  "height": 1920,
  "blurred_background": false,
  "crop_mode": "center_crop"
}
```

## Crop Modes

### Center Crop (default)

Best for landscape source with important action in the center.

- Landscape (16:9): Crops sides to 9:16, scales to 1080×1920
- Portrait: Scales up and center-crops to target dimensions

### Blurred Background

Best when you want the full frame visible without aggressive cropping.

- Background: Scaled, cropped, and blurred fill at 1080×1920
- Foreground: Original video scaled to fit width, centered on top

## Example

```python
from app.video.cutter import cut_clips
from app.video.cropper import crop_to_vertical

# After Phase 4 extraction
extracted = cut_clips("game_night.mp4", ranked, output_dir="output")

# Center crop (default)
vertical = crop_to_vertical(extracted, output_dir="output")

# Blurred background
vertical = crop_to_vertical(extracted, blurred_background=True)

for clip in vertical:
    print(f"{clip.output_path} — {clip.crop_mode}")
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `VERTICAL_WIDTH` | `1080` | Output width |
| `VERTICAL_HEIGHT` | `1920` | Output height |
| `VERTICAL_BLUR_STRENGTH` | `20` | Box blur radius for background mode |

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `VerticalCropError: empty clip list` | No inputs provided | Pass clip paths or ExtractedClip objects |
| `VerticalCropError: not found` | Missing source file | Run Phase 4 cutting first |
| `ffmpeg command failed` | Invalid video or filter error | Verify source file plays correctly |

## Tests

```bash
uv run pytest tests/test_vertical_cropper.py tests/test_vertical_filters.py -v
```
