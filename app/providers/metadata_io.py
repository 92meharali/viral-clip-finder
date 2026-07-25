"""Shared metadata export helpers for AI providers."""

from __future__ import annotations

import json
from pathlib import Path

from loguru import logger

from app.models.metadata import ClipMetadata


def save_metadata(metadata: ClipMetadata, output_dir: str | Path) -> ClipMetadata:
    """Export clip metadata to ``clip{N}_metadata.json``."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"clip{metadata.index}_metadata.json"
    path.write_text(
        json.dumps(metadata.model_dump(exclude={"json_path"}), indent=2),
        encoding="utf-8",
    )
    logger.debug("Exported metadata to {}", path.name)
    return metadata.model_copy(update={"json_path": str(path.resolve())})
