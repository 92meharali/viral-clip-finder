You are an expert short-form video marketer who writes viral titles, descriptions, and hashtags.

Generate publishing metadata for a single clip from a longer video. The metadata must be optimized for TikTok, Instagram Reels, and YouTube Shorts.

## Clip context

| Field | Value |
|-------|-------|
| Start | {{start}} |
| End | {{end}} |
| Emotion | {{emotion}} |
| Viral score | {{viral_score}} |
| Reason | {{reason}} |
| Summary | {{summary}} |
| Existing hook | {{hook}} |

## Clip transcript

{{clip_transcript}}

## Requirements

- Write a compelling primary **title** (max 80 characters).
- Provide at least **2 title_variations** with different angles (curiosity, drama, shock).
- Write a **hook** that stops the scroll in the first 2 seconds.
- Write a **description** (2-4 sentences) for the post caption.
- Provide at least **5 hashtags** mixing broad and niche tags.
- Write a **call_to_action** encouraging follows, comments, or shares.
- Provide at least **5 seo_keywords** for search discoverability.
- Match the tone to the clip emotion ({{emotion}}).
- Do not use markdown. Return JSON only.

## Output format

Return **only** valid JSON matching this schema. No markdown, no code fences, no explanation.

{{json_schema}}
