"""Clip metadata models for social media publishing."""

from pydantic import BaseModel, Field, field_validator


class ClipMetadataBase(BaseModel):
    """Publishing metadata for a single clip returned by the LLM."""

    title: str = Field(..., min_length=1, description="Primary video title")
    title_variations: list[str] = Field(
        ...,
        min_length=2,
        description="Alternative title options",
    )
    hook: str = Field(..., min_length=1, description="Scroll-stopping hook line")
    description: str = Field(..., min_length=1, description="Platform post description")
    hashtags: list[str] = Field(..., min_length=3, description="Relevant hashtags")
    call_to_action: str = Field(..., min_length=1, description="Call-to-action for viewers")
    seo_keywords: list[str] = Field(
        ...,
        min_length=3,
        description="SEO/search keywords",
    )

    @field_validator("hashtags")
    @classmethod
    def normalize_hashtags(cls, tags: list[str]) -> list[str]:
        """Ensure all hashtags start with #."""
        return [tag if tag.startswith("#") else f"#{tag.lstrip('#')}" for tag in tags]

    @field_validator("title_variations")
    @classmethod
    def strip_title_variations(cls, titles: list[str]) -> list[str]:
        """Strip whitespace from title variations."""
        return [title.strip() for title in titles if title.strip()]


class ClipMetadata(ClipMetadataBase):
    """Clip metadata enriched with clip identity and export path."""

    index: int = Field(..., ge=1, description="1-based clip number")
    clip_start: str = Field(..., description="Clip start timestamp")
    clip_end: str = Field(..., description="Clip end timestamp")
    json_path: str | None = Field(
        default=None,
        description="Path to exported JSON file, if saved",
    )

    model_config = {"frozen": True}
