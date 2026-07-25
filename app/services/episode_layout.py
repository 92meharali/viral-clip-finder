"""Structured episode export layout helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.models.candidate_window import CandidateWindowResult
from app.models.transcript import TranscriptSegment
from app.utils.clip_segments import format_timestamp


@dataclass(frozen=True)
class EpisodeExportLayout:
    """Directory layout for a structured episode export."""

    root: Path
    clips: Path
    metadata: Path
    subtitles: Path
    analysis: Path
    report: Path
    logs: Path
    reframe: Path

    def ensure(self) -> None:
        """Create all export directories."""
        for path in (
            self.root,
            self.clips,
            self.metadata,
            self.subtitles,
            self.logs,
            self.reframe,
        ):
            path.mkdir(parents=True, exist_ok=True)


def build_episode_layout(output_dir: str | Path, episode_name: str) -> EpisodeExportLayout:
    """Build the structured episode export layout."""
    root = Path(output_dir).resolve() / episode_name
    return EpisodeExportLayout(
        root=root,
        clips=root / "clips",
        metadata=root / "metadata",
        subtitles=root / "subtitles",
        analysis=root / "analysis.json",
        report=root / "report.md",
        logs=root / "logs",
        reframe=root / "reframe",
    )


def write_analysis_artifact(
    layout: EpisodeExportLayout,
    *,
    segments: list[TranscriptSegment],
    candidate_windows: CandidateWindowResult | None = None,
) -> None:
    """Write analysis.json for an episode export."""
    layout.ensure()
    payload = {
        "segment_count": len(segments),
        "candidate_windows": (
            [window.model_dump() for window in candidate_windows.windows]
            if candidate_windows is not None
            else []
        ),
    }
    layout.analysis.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_report_artifact(
    layout: EpisodeExportLayout,
    *,
    source_video: str,
    transcript_source: str,
    clips_exported: int,
    candidate_windows: CandidateWindowResult | None = None,
) -> None:
    """Write a human-readable report.md summary."""
    layout.ensure()
    lines = [
        "# Episode Export Report",
        "",
        f"- Source video: `{source_video}`",
        f"- Transcript: `{transcript_source}`",
        f"- Clips exported: {clips_exported}",
        "",
    ]
    if candidate_windows is not None:
        lines.append("## Candidate Windows")
        lines.append("")
        for window in candidate_windows.windows:
            start = format_timestamp(window.start_seconds)
            end = format_timestamp(window.end_seconds)
            labels = ", ".join(window.labels) if window.labels else "candidate"
            lines.append(
                f"- `{start}` → `{end}` score {window.score:.1f} ({labels})"
            )
        lines.append("")

    layout.report.write_text("\n".join(lines), encoding="utf-8")
