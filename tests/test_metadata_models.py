"""Tests for metadata models."""

import pytest
from pydantic import ValidationError

from app.models.metadata import ClipMetadata, ClipMetadataBase


class TestClipMetadataBase:
    def test_normalizes_hashtags(self) -> None:
        meta = ClipMetadataBase(
            title="Test Title",
            title_variations=["Alt 1", "Alt 2"],
            hook="Hook line",
            description="Description text",
            hashtags=["mafia", "#betrayal", "gaming"],
            call_to_action="Follow for more",
            seo_keywords=["one", "two", "three"],
        )
        assert meta.hashtags[0] == "#mafia"
        assert meta.hashtags[1] == "#betrayal"

    def test_requires_minimum_hashtags(self) -> None:
        with pytest.raises(ValidationError):
            ClipMetadataBase(
                title="Test",
                title_variations=["A", "B"],
                hook="Hook",
                description="Desc",
                hashtags=["#one"],
                call_to_action="CTA",
                seo_keywords=["a", "b", "c"],
            )


class TestClipMetadata:
    def test_creates_with_clip_fields(self) -> None:
        meta = ClipMetadata(
            index=1,
            clip_start="00:00:10",
            clip_end="00:00:40",
            title="Test Title",
            title_variations=["Alt 1", "Alt 2"],
            hook="Hook",
            description="Desc",
            hashtags=["#a", "#b", "#c"],
            call_to_action="CTA",
            seo_keywords=["k1", "k2", "k3"],
        )
        assert meta.index == 1
        assert meta.json_path is None
