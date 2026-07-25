"""Load and render prompt templates from the prompts directory."""

from pathlib import Path

from loguru import logger

from app.core.exceptions import PromptLoadError

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
SCHEMAS_DIR = PROMPTS_DIR / "schemas"

_LEGACY_PROMPT_NAMES = {
    "clip_selection": "clip_analysis",
    "metadata_generation": "metadata",
}


def _resolve_prompt_name(name: str) -> str:
    """Map legacy prompt names to current template names."""
    return _LEGACY_PROMPT_NAMES.get(name, name)


def load_prompt(name: str, **variables: str) -> str:
    """Load a prompt template and substitute ``{{variable}}`` placeholders.

    Args:
        name: Prompt file name without extension (e.g. ``clip_analysis``).
        **variables: Key-value pairs to replace in the template.

    Returns:
        Rendered prompt string.

    Raises:
        PromptLoadError: If the prompt file is missing or cannot be read.

    Example:
        >>> load_prompt("clip_analysis", transcript="[00:00:01] Hello")
    """
    resolved_name = _resolve_prompt_name(name)
    path = PROMPTS_DIR / f"{resolved_name}.md"
    if not path.exists():
        logger.error("Prompt template not found: {}", path)
        raise PromptLoadError(f"Prompt template not found: {name}")

    try:
        template = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.error("Failed to read prompt template {}: {}", path, exc)
        raise PromptLoadError(f"Could not read prompt: {name}") from exc

    rendered = template
    for key, value in variables.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)

    logger.debug("Loaded prompt template: {}", resolved_name)
    return rendered


def load_prompt_schema(name: str) -> str:
    """Load a JSON schema example for inclusion in manual AI prompts.

    Args:
        name: Schema file name without extension (e.g. ``clip_analysis``).

    Returns:
        Schema JSON as a formatted string.
    """
    resolved_name = _resolve_prompt_name(name)
    path = SCHEMAS_DIR / f"{resolved_name}.json"
    if not path.exists():
        logger.error("Prompt schema not found: {}", path)
        raise PromptLoadError(f"Prompt schema not found: {name}")

    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        logger.error("Failed to read prompt schema {}: {}", path, exc)
        raise PromptLoadError(f"Could not read prompt schema: {name}") from exc
