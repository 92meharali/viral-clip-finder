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


class MetadataGenerationError(ViralReelError):
    """Raised when LLM metadata generation fails."""

    def __init__(self, message: str, *, model: str | None = None) -> None:
        self.model = model
        super().__init__(message)


class QualityCheckError(ViralReelError):
    """Raised when quality checking cannot be performed."""


class BatchExportError(ViralReelError):
    """Raised when batch export fails."""


class ReframeError(ViralReelError):
    """Base exception for intelligent reframing pipeline errors."""


class FaceDetectionError(ReframeError):
    """Raised when face detection fails."""


class FrameExtractionError(ReframeError):
    """Raised when video frame extraction fails."""


class UnknownFaceDetectorError(ReframeError):
    """Raised when an unsupported face detector is requested."""


class UnknownFaceTrackerError(ReframeError):
    """Raised when an unsupported face tracker is requested."""


class SceneDetectionError(ReframeError):
    """Raised when scene detection fails."""


class UnknownSceneDetectorError(ReframeError):
    """Raised when an unsupported scene detector is requested."""


class SpeakerEstimationError(ReframeError):
    """Raised when active speaker estimation fails."""


class UnknownSpeakerEstimatorError(ReframeError):
    """Raised when an unsupported speaker estimator is requested."""


class ImportanceScoringError(ReframeError):
    """Raised when importance scoring fails."""


class UnknownImportanceScorerError(ReframeError):
    """Raised when an unsupported importance scorer is requested."""


class CompositionError(ReframeError):
    """Raised when shot composition planning fails."""


class UnknownCompositionPlannerError(ReframeError):
    """Raised when an unsupported composition planner is requested."""


class CameraPlanningError(ReframeError):
    """Raised when virtual camera planning fails."""


class UnknownCameraPlannerError(ReframeError):
    """Raised when an unsupported camera planner is requested."""


class TemporalSmoothingError(ReframeError):
    """Raised when temporal smoothing fails."""


class UnknownTemporalSmootherError(ReframeError):
    """Raised when an unsupported temporal smoother is requested."""


class SafeCropError(ReframeError):
    """Raised when safe crop generation fails."""


class UnknownCropGeneratorError(ReframeError):
    """Raised when an unsupported crop generator is requested."""


class ReframeRenderError(ReframeError):
    """Raised when reframe rendering fails."""


class UnknownReframeRendererError(ReframeError):
    """Raised when an unsupported reframe renderer is requested."""


class UnknownProviderError(ViralReelError):
    """Raised when an unsupported AI provider is requested."""


class ManualAnalysisRequiredError(LLMAnalysisError):
    """Raised when the Cursor manual provider needs a JSON response."""

    def __init__(self, message: str, *, prompt_path: str | None = None) -> None:
        self.prompt_path = prompt_path
        super().__init__(message)
