from __future__ import annotations

from pathlib import Path


def load_extraction_prompt(path: str) -> str:
    """Load the model-facing graph extraction prompt from a configured skill file."""
    prompt_path = resolve_prompt_path(path)
    if not prompt_path.exists():
        raise FileNotFoundError(f"Graph extraction prompt not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8").strip()


def resolve_prompt_path(path: str) -> Path:
    prompt_path = Path(path)
    if prompt_path.is_absolute() or prompt_path.exists():
        return prompt_path
    for parent in Path(__file__).resolve().parents:
        candidate = parent / path
        if candidate.exists():
            return candidate
    return prompt_path
