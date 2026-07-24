"""Command-line interface for the viral reel generator."""

from __future__ import annotations

from pathlib import Path

import typer
from loguru import logger

from app.core.config import get_settings
from app.services.batch_exporter import BatchExportOptions, BatchExporter, run_batch_export
from app.services.transcript_parser import parse_transcript_file

app = typer.Typer(
    name="viral-reel",
    help="Convert long YouTube videos into viral short-form clips.",
    no_args_is_help=True,
)


@app.command()
def analyze(
    transcript: Path = typer.Argument(..., help="Path to transcript file"),
) -> None:
    """Parse a transcript and print segment count."""
    segments = parse_transcript_file(str(transcript))
    typer.echo(f"Parsed {len(segments)} segments from {transcript}")


@app.command()
def export(
    video: Path = typer.Option(..., "--video", "-v", help="Source video file"),
    transcript: Path = typer.Option(..., "--transcript", "-t", help="Transcript file"),
    output: Path = typer.Option("output", "--output", "-o", help="Output directory"),
    top_n: int | None = typer.Option(None, "--top-n", help="Max clips to export"),
    blur: bool = typer.Option(False, "--blur", help="Use blurred background cropping"),
    burn_subtitles: bool = typer.Option(
        False,
        "--burn-subtitles",
        help="Burn subtitles into vertical videos",
    ),
) -> None:
    """Run the full batch export pipeline."""
    settings = get_settings()
    options = BatchExportOptions(
        top_n=top_n or settings.max_clips,
        blurred_background=blur,
        burn_subtitles=burn_subtitles,
    )

    logger.info("Exporting clips from {} with {}", video, transcript)
    result = run_batch_export(
        video,
        transcript,
        output_dir=output,
        settings=settings,
        options=options,
    )

    typer.echo(f"Exported {result.manifest.clips_exported} clips to {result.manifest.output_dir}")
    typer.echo(f"Manifest: {result.manifest.manifest_path}")


if __name__ == "__main__":
    app()
