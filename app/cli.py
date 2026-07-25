"""Command-line interface for the viral reel generator."""

from __future__ import annotations

from pathlib import Path

import typer
from loguru import logger

from app.core.config import get_settings
from app.core.exceptions import LLMAnalysisError
from app.providers.cursor_manual import CursorManualClipAnalyzer
from app.providers.response_parser import parse_clip_analysis_response
from app.services.batch_exporter import BatchExportOptions, BatchExporter, run_batch_export
from app.services.transcript_parser import parse_transcript_file

app = typer.Typer(
    name="viral-reel",
    help="Convert long YouTube videos into viral short-form clips.",
    no_args_is_help=True,
)

ai_app = typer.Typer(help="AI provider utilities for manual Cursor workflows.")
app.add_typer(ai_app, name="ai")


@app.command()
def analyze(
    transcript: Path = typer.Argument(..., help="Path to transcript file"),
) -> None:
    """Parse a transcript and print segment count."""
    segments = parse_transcript_file(str(transcript))
    typer.echo(f"Parsed {len(segments)} segments from {transcript}")


@ai_app.command("export-prompt")
def export_prompt(
    transcript: Path = typer.Option(..., "--transcript", "-t", help="Transcript file"),
    output: Path = typer.Option(
        "analysis_prompt.md",
        "--output",
        "-o",
        help="Where to write the analysis prompt",
    ),
) -> None:
    """Export a Cursor-ready clip analysis prompt from a transcript."""
    settings = get_settings()
    segments = parse_transcript_file(str(transcript))
    analyzer = CursorManualClipAnalyzer(settings)
    path = analyzer.write_analysis_prompt(segments, output)
    typer.echo(f"Wrote analysis prompt to {path}")
    typer.echo("Paste this prompt into Cursor, then save the JSON response.")


@ai_app.command("validate-response")
def validate_response(
    response: Path = typer.Option(..., "--response", "-r", help="Clip analysis JSON file"),
) -> None:
    """Validate a manual clip analysis JSON response."""
    content = response.read_text(encoding="utf-8")
    try:
        clips = parse_clip_analysis_response(content)
    except LLMAnalysisError as exc:
        typer.secho(f"Validation failed: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Valid response with {len(clips)} clips")
    for clip in clips:
        typer.echo(f"  {clip.start}-{clip.end} score={clip.viral_score} emotion={clip.emotion}")


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
    structured: bool = typer.Option(
        False,
        "--structured",
        help="Use episode-style structured output directories",
    ),
    episode_name: str | None = typer.Option(
        None,
        "--episode-name",
        "-e",
        help="Episode folder name when using --structured",
    ),
    crop_mode: str | None = typer.Option(
        None,
        "--crop-mode",
        help="Vertical crop mode: reframe, center, or blur",
    ),
    provider: str | None = typer.Option(
        None,
        "--provider",
        help="AI provider: cursor or openai",
    ),
    analysis_response: Path | None = typer.Option(
        None,
        "--analysis-response",
        help="Path to manual clip analysis JSON (cursor provider)",
    ),
    metadata_response: Path | None = typer.Option(
        None,
        "--metadata-response",
        help="Path to manual metadata JSON (cursor provider)",
    ),
    no_candidate_windows: bool = typer.Option(
        False,
        "--no-candidate-windows",
        help="Skip candidate window generation",
    ),
) -> None:
    """Run the full batch export pipeline."""
    settings = get_settings()
    options = BatchExportOptions(
        top_n=top_n or settings.max_clips,
        blurred_background=blur,
        burn_subtitles=burn_subtitles,
        ai_provider=provider,
        analysis_response_path=str(analysis_response) if analysis_response else None,
        metadata_response_path=str(metadata_response) if metadata_response else None,
        structured_output=structured or settings.batch_structured_output,
        episode_name=episode_name,
        vertical_crop_mode=crop_mode,
        generate_candidate_windows=not no_candidate_windows,
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
