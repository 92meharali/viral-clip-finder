"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the viral reel generator.

    Values are read from environment variables or a ``.env`` file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    ai_provider: str = Field(
        default="cursor",
        description="AI provider: cursor (manual) or openai",
    )
    ai_analysis_response_path: str = Field(
        default="analysis_response.json",
        description="Path to manual clip analysis JSON for the cursor provider",
    )
    ai_metadata_response_path: str = Field(
        default="metadata_response.json",
        description="Path to manual metadata JSON for the cursor provider",
    )

    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o", description="OpenAI model name")
    openai_temperature: float = Field(default=0.7, ge=0, le=2, description="LLM temperature")

    max_clips: int = Field(default=10, ge=1, description="Maximum clips to detect per analysis")
    min_clip_duration_seconds: int = Field(
        default=20, ge=1, description="Minimum clip duration in seconds"
    )
    max_clip_duration_seconds: int = Field(
        default=90, ge=1, description="Maximum clip duration in seconds"
    )

    log_level: str = Field(default="INFO", description="Logging level")

    api_host: str = Field(default="0.0.0.0", description="API server bind address")
    api_port: int = Field(default=8000, ge=1, le=65535, description="API server bind port")
    api_reload: bool = Field(default=False, description="Enable uvicorn auto-reload for development")

    youtube_preferred_languages: str = Field(
        default="en,en-US,en-GB",
        description="Comma-separated subtitle language preference list",
    )
    youtube_subtitle_format_priority: str = Field(
        default="vtt,srv3,json3,ttml",
        description="Comma-separated subtitle format preference list",
    )

    database_url: str = Field(
        default="sqlite:///./data/viral_clip_finder.db",
        description="SQLAlchemy database URL (SQLite dev, PostgreSQL prod)",
    )
    database_echo: bool = Field(default=False, description="Log SQL statements")
    database_auto_create: bool = Field(
        default=True,
        description="Create database tables automatically on API startup",
    )

    output_dir: str = Field(default="output", description="Default directory for extracted clips")
    ffmpeg_path: str = Field(default="ffmpeg", description="Path to the ffmpeg binary")
    ffprobe_path: str = Field(default="ffprobe", description="Path to the ffprobe binary")

    vertical_width: int = Field(default=1080, ge=1, description="Target vertical video width")
    vertical_height: int = Field(default=1920, ge=1, description="Target vertical video height")
    vertical_blur_strength: int = Field(
        default=20, ge=1, description="Box blur strength for blurred background mode"
    )

    face_detector: str = Field(
        default="mediapipe",
        description="Face detector backend: mediapipe",
    )
    face_detection_min_confidence: float = Field(
        default=0.5,
        ge=0,
        le=1,
        description="Minimum face detection confidence threshold",
    )
    face_extraction_fps: float = Field(
        default=2.0,
        gt=0,
        description="Frames per second to sample for face analysis",
    )
    minimum_face_size: int = Field(
        default=40,
        ge=1,
        description="Minimum face bounding box size in pixels",
    )

    face_tracker: str = Field(
        default="iou",
        description="Face tracker backend: iou",
    )
    tracking_iou_threshold: float = Field(
        default=0.3,
        ge=0,
        le=1,
        description="Minimum IoU to associate a detection with an existing track",
    )
    tracking_max_center_distance: float = Field(
        default=250.0,
        gt=0,
        description="Maximum center distance in pixels for track association",
    )
    tracking_max_age: int = Field(
        default=5,
        ge=1,
        description="Frames a track can survive without a matching detection",
    )

    scene_detector: str = Field(
        default="ffmpeg",
        description="Scene detector backend: ffmpeg or histogram",
    )
    scene_detection_threshold: float = Field(
        default=0.35,
        ge=0,
        le=1,
        description="Scene change sensitivity threshold",
    )
    scene_min_gap_seconds: float = Field(
        default=0.5,
        gt=0,
        description="Minimum seconds between distinct scene boundaries",
    )
    scene_extraction_fps: float = Field(
        default=4.0,
        gt=0,
        description="Frame sample rate for histogram scene detection",
    )

    speaker_estimator: str = Field(
        default="fusion",
        description="Active speaker estimator backend: fusion",
    )
    speaker_weight_transcript: float = Field(
        default=0.20,
        ge=0,
        description="Weight for transcript timing signal",
    )
    speaker_weight_mouth: float = Field(
        default=0.40,
        ge=0,
        description="Weight for mouth movement signal",
    )
    speaker_weight_orientation: float = Field(
        default=0.20,
        ge=0,
        description="Weight for face orientation signal",
    )
    speaker_weight_audio: float = Field(
        default=0.20,
        ge=0,
        description="Weight for audio energy signal",
    )
    speaker_min_confidence: float = Field(
        default=0.4,
        ge=0,
        le=1,
        description="Minimum fused confidence to label a track as speaking",
    )
    speaker_min_segment_seconds: float = Field(
        default=0.3,
        gt=0,
        description="Minimum duration for an active speaker segment",
    )
    speaker_audio_window_seconds: float = Field(
        default=0.25,
        gt=0,
        description="Audio RMS window size for speaker estimation",
    )

    importance_scorer: str = Field(
        default="fusion",
        description="Importance scorer backend: fusion",
    )
    importance_weight_speaking: float = Field(
        default=0.45,
        ge=0,
        description="Weight for currently speaking factor",
    )
    importance_weight_expression: float = Field(
        default=0.15,
        ge=0,
        description="Weight for facial expression factor",
    )
    importance_weight_detection: float = Field(
        default=0.10,
        ge=0,
        description="Weight for detection confidence factor",
    )
    importance_weight_center: float = Field(
        default=0.10,
        ge=0,
        description="Weight for frame-center factor",
    )
    importance_weight_presence: float = Field(
        default=0.15,
        ge=0,
        description="Weight for screen presence factor",
    )
    importance_weight_recent_speaker: float = Field(
        default=0.10,
        ge=0,
        description="Weight for recent speaker factor",
    )
    importance_weight_reaction: float = Field(
        default=0.10,
        ge=0,
        description="Weight for reaction-target factor",
    )
    importance_recent_speaker_decay_seconds: float = Field(
        default=3.0,
        gt=0,
        description="Decay window for recent speaker attention",
    )

    composition_planner: str = Field(
        default="heuristic",
        description="Shot composition planner backend: heuristic",
    )
    composition_min_padding: int = Field(
        default=40,
        ge=0,
        description="Minimum padding around subjects in pixels",
    )
    composition_forehead_padding_ratio: float = Field(
        default=0.35,
        ge=0,
        description="Extra top padding as a fraction of face height",
    )
    composition_rule_of_thirds_offset: float = Field(
        default=0.08,
        ge=0,
        le=0.5,
        description="Vertical eye-line offset using rule of thirds",
    )
    composition_conversation_importance_gap: float = Field(
        default=0.15,
        ge=0,
        le=1,
        description="Max score gap to treat two participants as a conversation",
    )
    composition_secondary_importance_min: float = Field(
        default=0.45,
        ge=0,
        le=1,
        description="Minimum secondary importance to keep a two-shot",
    )
    composition_group_face_threshold: int = Field(
        default=3,
        ge=2,
        description="Visible faces required for group reaction framing",
    )
    composition_vote_reveal_face_threshold: int = Field(
        default=4,
        ge=3,
        description="Visible faces required for vote reveal framing",
    )
    composition_group_importance_min: float = Field(
        default=0.35,
        ge=0,
        le=1,
        description="Minimum importance to include a face in group framing",
    )
    composition_rapid_discussion_seconds: float = Field(
        default=2.0,
        gt=0,
        description="Window for detecting rapid speaker changes",
    )
    composition_rapid_speaker_changes: int = Field(
        default=3,
        ge=2,
        description="Speaker changes required to trigger conversation framing",
    )
    composition_zoom_single_speaker: float = Field(
        default=1.0,
        ge=1.0,
        description="Zoom multiplier for single-speaker shots",
    )
    composition_zoom_conversation: float = Field(
        default=1.25,
        ge=1.0,
        description="Zoom multiplier for two-person conversation shots",
    )
    composition_zoom_group_reaction: float = Field(
        default=1.45,
        ge=1.0,
        description="Zoom multiplier for group reaction shots",
    )
    composition_zoom_vote_reveal: float = Field(
        default=1.7,
        ge=1.0,
        description="Zoom multiplier for vote reveal / wide table shots",
    )

    camera_planner: str = Field(
        default="pursuit",
        description="Virtual camera planner backend: pursuit",
    )
    camera_max_pan_speed: float = Field(
        default=280.0,
        gt=0,
        description="Maximum camera pan speed in pixels per second",
    )
    camera_max_zoom_speed: float = Field(
        default=500.0,
        gt=0,
        description="Maximum crop-width change per second in pixels",
    )
    camera_smoothing: float = Field(
        default=0.35,
        gt=0,
        le=1,
        description="Per-frame interpolation factor toward composition targets",
    )
    camera_scene_reset: bool = Field(
        default=True,
        description="Reset camera state at scene boundaries",
    )
    camera_scene_boundary_tolerance: float = Field(
        default=0.15,
        ge=0,
        description="Seconds around a scene boundary to trigger camera reset",
    )

    temporal_smoother: str = Field(
        default="ema",
        description="Temporal smoothing backend: ema",
    )
    smoothing_strength: float = Field(
        default=0.12,
        gt=0,
        le=1,
        description="EMA smoothing factor toward new camera samples",
    )
    smoothing_max_jerk: float = Field(
        default=800.0,
        gt=0,
        description="Maximum allowed velocity change per second",
    )
    smoothing_zoom_oscillation_damping: float = Field(
        default=0.5,
        gt=0,
        le=1,
        description="Damping applied when zoom velocity oscillates",
    )
    smoothing_scene_boundary_tolerance: float = Field(
        default=0.15,
        ge=0,
        description="Scene boundary tolerance for smoothing segmentation",
    )

    crop_generator: str = Field(
        default="safe",
        description="Crop generator backend: safe",
    )
    crop_face_safety_padding: int = Field(
        default=20,
        ge=0,
        description="Padding around faces when enforcing crop safety",
    )
    crop_min_face_visibility: float = Field(
        default=0.95,
        ge=0,
        le=1,
        description="Minimum required visible face area inside the crop",
    )

    reframe_renderer: str = Field(
        default="ffmpeg",
        description="Reframe renderer backend: ffmpeg",
    )
    reframe_render_fps: float = Field(
        default=30.0,
        gt=0,
        description="Interpolation frame rate for crop plan rendering",
    )
    reframe_segment_merge_threshold: float = Field(
        default=20.0,
        ge=0,
        description="Merge render segments when crop position changes are below this threshold (pixels)",
    )
    reframe_render_preset: str = Field(
        default="fast",
        description="ffmpeg x264 preset for reframe renders",
    )
    reframe_render_crf: int = Field(
        default=23,
        ge=0,
        le=51,
        description="ffmpeg CRF quality for reframe renders",
    )
    reframe_blur_background: bool = Field(
        default=False,
        description="Use blurred background mode for reframe renders",
    )
    reframe_pan_only: bool = Field(
        default=True,
        description="Use a fixed 9:16 crop window and pan only (no per-frame stretching)",
    )
    reframe_pan_smoothing_strength: float = Field(
        default=0.10,
        gt=0,
        le=1,
        description="EMA smoothing for pan-only crop motion (lower = smoother)",
    )
    reframe_pan_speaker_switch_smoothing: float = Field(
        default=0.22,
        gt=0,
        le=1,
        description="EMA smoothing when the active speaker changes",
    )
    reframe_pan_deadband_pixels: float = Field(
        default=4.0,
        ge=0,
        description="Ignore pan updates smaller than this many pixels",
    )

    vertical_crop_mode: str = Field(
        default="reframe",
        description="Vertical crop mode: reframe, center, or blur",
    )
    batch_structured_output: bool = Field(
        default=False,
        description="Use episode-style structured output directories",
    )
    candidate_window_min_duration: float = Field(
        default=20.0,
        gt=0,
        description="Minimum candidate window duration in seconds",
    )
    candidate_window_max_duration: float = Field(
        default=90.0,
        gt=0,
        description="Maximum candidate window duration in seconds",
    )
    candidate_window_merge_gap: float = Field(
        default=3.0,
        ge=0,
        description="Merge enrichment signals within this gap in seconds",
    )

    llm_window_enabled: bool = Field(
        default=True,
        description="Split long transcripts into overlapping windows for LLM analysis",
    )
    llm_window_size_seconds: float = Field(
        default=600.0,
        gt=0,
        description="Maximum transcript window size sent to the LLM in seconds",
    )
    llm_window_overlap_seconds: float = Field(
        default=60.0,
        ge=0,
        description="Overlap between consecutive LLM transcript windows in seconds",
    )

    subtitle_font: str = Field(default="Arial", description="Subtitle font for burn-in")
    subtitle_size: int = Field(default=24, ge=8, le=96, description="Subtitle font size")
    subtitle_outline: int = Field(default=2, ge=0, le=10, description="Subtitle outline thickness")
    subtitle_color: str = Field(default="white", description="Subtitle text color")
    subtitle_position: str = Field(
        default="bottom", description="Subtitle position: top, center, or bottom"
    )

    min_viral_score: float = Field(
        default=5.0, ge=0, le=10, description="Minimum viral score to pass quality checks"
    )
    max_silence_ratio: float = Field(
        default=0.6,
        ge=0,
        le=1,
        description="Maximum allowed silence ratio in a clip",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
