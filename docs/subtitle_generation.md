# Subtitle Generation

## Purpose

Generate SRT subtitle files from transcript timestamps aligned to clip windows, and optionally burn styled subtitles into vertical videos for social media upload.

## Modules

| Module | Responsibility |
|--------|----------------|
| `app/video/subtitles.py` | SRT generation from transcript + clip timing |
| `app/video/subtitle_burner.py` | FFmpeg burn-in with configurable styles |
| `app/utils/srt_utils.py` | SRT timestamp formatting and file writing |
| `app/models/subtitle.py` | `SubtitleCue`, `SubtitleStyle`, `SubtitleFile` |

## Inputs

- **Transcript segments**: Full parsed transcript from Phase 1
- **Timed clips**: `ExtractedClip`, `ViralClip`, or `RankedClip` with start/end seconds
- **Style** (burn-in): Font, size, outline, color, position

## Outputs

### SRT file (`clip1.srt`)

```srt
1
00:00:02,000 --> 00:00:07,000
Player A: I didn't kill him.

2
00:00:07,000 --> 00:00:14,000
Player B: You're lying.
```

### Subtitle metadata

```json
{
  "index": 1,
  "clip_start": "00:00:08",
  "clip_end": "00:00:30",
  "srt_path": "output/clip1.srt",
  "cue_count": 3,
  "burned_output_path": "output/clip1_vertical_subtitled.mp4"
}
```

## Example

```python
from app.services.transcript_parser import parse_transcript_file
from app.video.cutter import cut_clips
from app.video.cropper import crop_to_vertical
from app.video.subtitles import generate_subtitles
from app.video.subtitle_burner import burn_subtitles
from app.models.subtitle import SubtitleStyle, SubtitlePosition

segments = parse_transcript_file("transcript.txt")
extracted = cut_clips("game_night.mp4", ranked, output_dir="output")
vertical = crop_to_vertical(extracted, output_dir="output")

# Generate SRT files
subtitles = generate_subtitles(segments, extracted, output_dir="output")

# Optional: burn into vertical videos
style = SubtitleStyle(font="Arial", size=28, outline=2, color="white", position=SubtitlePosition.BOTTOM)
burned = burn_subtitles(vertical[0].output_path, subtitles[0].srt_path, style=style)
```

## Subtitle Style Options

| Property | Default | Description |
|----------|---------|-------------|
| `font` | `Arial` | Font family name |
| `size` | `24` | Font size in pixels |
| `outline` | `2` | Outline thickness |
| `color` | `white` | Named color or `#RRGGBB` hex |
| `position` | `bottom` | `top`, `center`, or `bottom` |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SUBTITLE_FONT` | `Arial` | Default burn-in font |
| `SUBTITLE_SIZE` | `24` | Default font size |
| `SUBTITLE_OUTLINE` | `2` | Default outline thickness |
| `SUBTITLE_COLOR` | `white` | Default text color |
| `SUBTITLE_POSITION` | `bottom` | Default position |

## Timing Logic

- Segments within `[clip_start, clip_end)` are included
- Cue start = segment time − clip start (clip-relative)
- Cue end = next segment start, or clip end for the last cue
- Minimum cue duration: 0.5 seconds

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `SubtitleError: empty transcript` | No segments | Parse transcript first |
| `SubtitleError: empty clip list` | No clips provided | Run cutting/ranking first |
| `SubtitleError: not found` | Missing SRT or video | Check file paths |
| `SubtitleError: Failed to burn` | FFmpeg filter error | Verify SRT encoding (UTF-8) |

## Tests

```bash
uv run pytest tests/test_srt_utils.py tests/test_subtitle_generator.py tests/test_subtitle_burner.py -v
```
