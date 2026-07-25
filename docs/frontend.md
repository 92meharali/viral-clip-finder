# Frontend (Next.js)

The web dashboard for Viral Clip Finder.

## Stack

- **Next.js 15** (App Router)
- **TypeScript**
- **Tailwind CSS** + shadcn-style UI primitives
- **TanStack Query** for API data fetching

## Prerequisites

- Node.js 20+
- API server running at `http://localhost:8000`

## Setup

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Pages

| Route | Description |
|-------|-------------|
| `/` | Paste YouTube URL, start analysis, recent projects |
| `/jobs/{id}` | Live analysis progress + ranked clips |
| `/projects/{id}` | Persisted project detail + clips |

## API integration

The frontend calls the FastAPI backend via `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).

CORS is enabled on the API for `http://localhost:3000` by default (`CORS_ORIGINS`).

## Development workflow

Run both services in separate terminals:

```bash
# Terminal 1 — API
uv run viral-clip-api

# Terminal 2 — Frontend
cd frontend && npm run dev
```

## Project structure

```
frontend/
  app/              # Next.js routes
  components/       # UI and feature components
  lib/api.ts        # API client
  types/api.ts      # Shared TypeScript types
```

## Next steps

- Interactive timeline visualization
- Search and emotion filters
- Video.js clip previews
- Analytics charts
