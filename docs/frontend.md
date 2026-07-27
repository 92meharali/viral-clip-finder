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

Node.js is **not** installed system-wide on your machine. We use a local binary at `~/.local/node-v22.12.0-darwin-arm64/`.

### Option A — helper script (easiest)

```bash
# Terminal 1 — API
uv run viral-clip-api

# Terminal 2 — Website
./frontend/dev.sh
```

### Option B — manual

Add Node to your shell once (paste in Terminal):

```bash
echo 'export PATH="$HOME/.local/node-v22.12.0-darwin-arm64/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Then:

```bash
cd frontend
cp .env.example .env.local   # first time only
npm install                  # first time only
npm run dev
```

### If Node is missing from ~/.local

```bash
curl -fsSL https://nodejs.org/dist/v22.12.0/node-v22.12.0-darwin-arm64.tar.gz -o /tmp/node.tar.gz
mkdir -p ~/.local && tar -xzf /tmp/node.tar.gz -C ~/.local
```

Open [http://localhost:3000](http://localhost:3000) — **not** port 8000.

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
