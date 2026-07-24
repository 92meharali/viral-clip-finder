"""Load and render prompt templates from the prompts directory."""

from pathlib import Path

from loguru import logger

from app.core.exceptions import PromptLoadError

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(name: str, **variables: str) -> str:
    """Load a prompt template and substitute ``{{variable}}`` placeholders.

    Args:
        name: Prompt file name without extension (e.g. ``clip_selection``).
        **variables: Key-value pairs to replace in the template.

    Returns:
        Rendered prompt string.

    Raises:
        PromptLoadError: If the prompt file is missing or cannot be read.

    Example:
        >>> load_prompt("clip_selection", transcript="[00:00:01] Hello")
    """
    path = PROMPTS_DIR / f"{name}.md"
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

    logger.debug("Loaded prompt template: {}", name)
    return rendered
