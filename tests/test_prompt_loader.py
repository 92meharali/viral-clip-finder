"""Tests for prompt template loading."""

import pytest

from app.core.exceptions import PromptLoadError
from app.utils.prompt_loader import load_prompt


class TestPromptLoader:
    def test_loads_clip_selection_prompt(self) -> None:
        prompt = load_prompt(
            "clip_selection",
            transcript="[00:00:13] Hello",
            max_clips="5",
            min_duration="20",
            max_duration="90",
            json_schema='{"clips": []}',
        )
        assert "[00:00:13] Hello" in prompt
        assert "5" in prompt
        assert "betrayals" in prompt.lower()

    def test_missing_prompt_raises(self) -> None:
        with pytest.raises(PromptLoadError, match="not found"):
            load_prompt("nonexistent_prompt")
