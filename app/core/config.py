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

    output_dir: str = Field(default="output", description="Default directory for extracted clips")
    ffmpeg_path: str = Field(default="ffmpeg", description="Path to the ffmpeg binary")
    ffprobe_path: str = Field(default="ffprobe", description="Path to the ffprobe binary")

    vertical_width: int = Field(default=1080, ge=1, description="Target vertical video width")
    vertical_height: int = Field(default=1920, ge=1, description="Target vertical video height")
    vertical_blur_strength: int = Field(
        default=20, ge=1, description="Box blur strength for blurred background mode"
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
