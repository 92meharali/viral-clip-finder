# AI Viral Clip Finder — Roadmap

This document maps the [master specification](../README.md) to the current codebase and defines the incremental delivery plan.

## Mission

**AI Video Intelligence Platform** — find viral moments, explain why they matter, optionally extract clips. Not a video editor.

## Current State (Baseline)

The repository began as **viral-reel-generator**, a CLI-first pipeline with heavy post-production features. Much of the analysis core is reusable; editing-centric modules are retained but deprioritized.

### Implemented and aligned with spec

| Spec area | Status | Location |
|-----------|--------|----------|
| Transcript parsing (SRT, VTT, plain text) | Done | `app/services/transcript_parser.py` |
| `TranscriptSegment` model | Done | `app/models/transcript.py` |
| Candidate window generation | Done (not wired to LLM) | `app/services/candidate_windows/` |
| AI provider abstraction (`ClipAnalyzer`) | Done | `app/providers/` |
| Viral clip + metadata models | Done | `app/models/clip.py`, `app/models/metadata.py` |
| Ranking & deduplication | Done | `app/services/clip_ranker.py` |
| Optional FFmpeg clip extraction (cut only) | Done | `app/video/cutter.py` |
| Structured logging | Partial | `loguru` via CLI |
| Configuration via env | Done | `app/core/config.py` |
| Unit/integration tests | Strong | `tests/` (~250+ tests) |

### Partially implemented

| Spec area | Gap | Notes |
|-----------|-----|-------|
| AI analysis at scale | Windows not fed to LLM | Generator exists; needs orchestration |
| Metadata export | CLI/batch only | JSON/MD export in batch exporter |
| FFmpeg extraction | CLI only | No `POST /extract` yet |
| Providers | cursor + openai | Gemini, Claude, Ollama, Manual stub pending |

### Not started

| Spec area | Priority |
|-----------|----------|
| FastAPI REST API | **P0** — in progress |
| YouTube URL → metadata + transcript (`yt-dlp`) | **Done** |
| Background job / async analysis | P0 |
| SQLAlchemy + Alembic (SQLite dev / Postgres prod) | P1 |
| Next.js dashboard | P1 |
| Interactive timeline, search, filters | P1 |
| Analytics charts | P2 |
| OpenTelemetry | P2 |

### Legacy / out of scope (retained, not extended)

These modules support the old "reel generator" mission. They remain in the repo for reference but are **not** part of the new product direction:

- `app/reframe/` — intelligent vertical reframing, pan, face tracking
- Subtitle burn-in (`app/video/subtitles.py` as default export step)
- Vertical crop as required pipeline stage
- Batch export with reframe integration (`app/services/batch_exporter.py` reframe path)

New exports should use **cut-only** FFmpeg extraction when clips are requested.

## Target architecture

```
YouTube URL
    → Ingestion (yt-dlp metadata + transcript)
    → Transcript parser
    → Candidate windows
    → ClipAnalyzer (provider abstraction)
    → Ranking & deduplication
    → Metadata generation
    → Optional FFmpeg extract
    → API + Dashboard
```

```
app/
  api/           # FastAPI routes, app factory
  schemas/       # API request/response models
  services/      # Pipeline orchestration
  providers/     # ClipAnalyzer implementations
  models/        # Domain models
  database/      # SQLAlchemy (future)
  config/        # (use app/core/config.py for now)
frontend/        # Next.js (future)
docs/
```

## Delivery phases

### Phase 1 — API foundation (current)

1. **FastAPI app + `/health`** — app factory, OpenAPI, tests, docs
2. **YouTube ingestion service** — metadata + transcript via `yt-dlp`
3. **`POST /analyze`** — accept URL, enqueue/run analysis, return job ID
4. **Analysis orchestration** — wire windows → provider → ranker
5. **Project persistence** — SQLite + Alembic models for jobs/projects/clips

### Phase 2 — Core API

6. `GET /projects`, `GET /projects/{id}`, `GET /clips`, `GET /report`
7. `POST /extract` — optional MP4 generation
8. Background worker interface (in-process first, queue-ready)
9. Export endpoints (`analysis.json`, `clips.json`, `report.md`, CSV)

### Phase 3 — Frontend

10. Next.js scaffold (Tailwind, shadcn/ui, TanStack Query)
11. Home page — URL input, recent projects
12. Project page — progress, timeline, clip cards
13. Search, filters, analytics
14. Video.js clip previews

### Phase 4 — Providers & polish

15. Gemini, Claude, Ollama providers
16. OpenTelemetry logging
17. PostgreSQL production config
18. Contributor docs, CI, coverage gates

## Incremental commit plan (next features)

| # | Feature | Conventional commit prefix |
|---|---------|---------------------------|
| 1 | FastAPI foundation + roadmap | `feat: add FastAPI foundation and roadmap` |
| 2 | YouTube ingestion service | `feat: add YouTube metadata and transcript ingestion` ✅ |
| 3 | Analysis job model + `POST /analyze` stub | `feat: add analysis job API` ✅ |
| 4 | Wire candidate windows to LLM pipeline | `feat: wire candidate windows to analysis` ✅ |
| 5 | Database models (projects, clips) | `feat: add project persistence` ✅ |
| 6 | `GET /projects` and `GET /clips` | `feat: add project and clip list endpoints` ✅ |
| 7 | Optional clip extraction API | `feat: add clip extraction endpoint` |
| 8 | Next.js frontend scaffold | `feat: add Next.js frontend scaffold` |

Each feature: implementation → tests → docs → single commit → wait for **continue**.

## Definition of done (release)

A user can open the website, paste a YouTube URL, click Analyze, wait for processing, browse an interactive timeline of ranked moments, preview clips, and download metadata/reports/optional MP4s for use in external editors.
