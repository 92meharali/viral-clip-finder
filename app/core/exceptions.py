"""Application-wide exceptions."""


class ViralReelError(Exception):
    """Base exception for all application errors."""


class TranscriptParseError(ViralReelError):
    """Raised when transcript text cannot be parsed."""

    def __init__(self, message: str, *, format_hint: str | None = None) -> None:
        self.format_hint = format_hint
        super().__init__(message)


class PromptLoadError(ViralReelError):
    """Raised when a prompt template cannot be loaded."""


class LLMAnalysisError(ViralReelError):
    """Raised when LLM clip analysis fails."""

    def __init__(self, message: str, *, model: str | None = None) -> None:
        self.model = model
        super().__init__(message)


class ClipRankingError(ViralReelError):
    """Raised when clip ranking fails."""


class VideoCutError(ViralReelError):
    """Raised when video cutting fails."""

    def __init__(self, message: str, *, source_path: str | None = None) -> None:
        self.source_path = source_path
        super().__init__(message)


class VerticalCropError(ViralReelError):
    """Raised when vertical cropping fails."""

    def __init__(self, message: str, *, source_path: str | None = None) -> None:
        self.source_path = source_path
        super().__init__(message)


class SubtitleError(ViralReelError):
    """Raised when subtitle generation or burning fails."""
