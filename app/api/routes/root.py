"""API root endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["meta"])


@router.get("/")
def api_root() -> dict[str, str]:
    """Point visitors to the docs and web frontend."""
    return {
        "service": "viral-clip-finder",
        "message": "This is the API server. Use /docs for the REST API.",
        "docs": "/docs",
        "health": "/health",
        "web_ui": "http://localhost:3000",
        "hint": "Run the Next.js frontend separately: cd frontend && npm run dev",
    }
