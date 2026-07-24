"""Application-wide exceptions."""


class ViralReelError(Exception):
    """Base exception for all application errors."""


class TranscriptParseError(ViralReelError):
    """Raised when transcript text cannot be parsed."""

    def __init__(self, message: str, *, format_hint: str | None = None) -> None:
        self.format_hint = format_hint
        super().__init__(message)
