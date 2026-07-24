"""Format transcript segments for LLM consumption."""

from app.models.transcript import TranscriptSegment


def format_transcript_for_llm(segments: list[TranscriptSegment]) -> str:
    """Convert parsed transcript segments into a compact LLM-readable format.

    Each line includes a timestamp, optional speaker, and dialogue text.

    Args:
        segments: Parsed transcript segments in chronological order.

    Returns:
        Multi-line string suitable for prompt injection.

    Example:
        >>> from app.models.transcript import TranscriptSegment
        >>> segments = [
        ...     TranscriptSegment(start="00:00:13", seconds=13.0, speaker="Player A", text="Hello."),
        ... ]
        >>> format_transcript_for_llm(segments)
        '[00:00:13] Player A: Hello.'
    """
    lines: list[str] = []
    for segment in segments:
        prefix = f"[{segment.start}]"
        if segment.speaker:
            lines.append(f"{prefix} {segment.speaker}: {segment.text}")
        else:
            lines.append(f"{prefix} {segment.text}")
    return "\n".join(lines)
