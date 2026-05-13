from __future__ import annotations

import os
from dataclasses import dataclass, replace
from typing import Any

DEFAULT_BACKEND = "pixtral"
DEFAULT_PIXTRAL_MODEL_PATH = "./models/mistral-community-pixtral-12b"
DEFAULT_EXTRACTION_PROMPT_PATH = "./skills/graph_image_extraction/extraction_prompt.md"
DEFAULT_MAX_NEW_TOKENS = 2048


@dataclass(frozen=True)
class VLMConfig:
    backend: str = DEFAULT_BACKEND
    pixtral_model_path: str = DEFAULT_PIXTRAL_MODEL_PATH
    max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS
    extraction_prompt_path: str = DEFAULT_EXTRACTION_PROMPT_PATH
    extraction_prompt: str | None = None

    @classmethod
    def from_env(cls) -> "VLMConfig":
        return cls(
            backend=os.getenv("VLM_BACKEND", DEFAULT_BACKEND),
            pixtral_model_path=os.getenv(
                "PIXTRAL_MODEL_PATH",
                os.getenv("PIXTRAL_LOCAL_MODEL_PATH", DEFAULT_PIXTRAL_MODEL_PATH),
            ),
            max_new_tokens=parse_int_env("VLM_MAX_NEW_TOKENS", DEFAULT_MAX_NEW_TOKENS),
            extraction_prompt_path=os.getenv("GRAPH_EXTRACTION_PROMPT_PATH", DEFAULT_EXTRACTION_PROMPT_PATH),
        )

    @classmethod
    def from_mapping(cls, config: dict[str, Any] | "VLMConfig" | None = None) -> "VLMConfig":
        if isinstance(config, VLMConfig):
            return config
        base = cls.from_env()
        if not config:
            return base
        allowed = set(cls.__dataclass_fields__)
        updates = {key: value for key, value in config.items() if key in allowed and value is not None}
        if "model_path" in config and "pixtral_model_path" not in updates and config["model_path"] is not None:
            updates["pixtral_model_path"] = config["model_path"]
        if "backend" in updates:
            updates["backend"] = str(updates["backend"])
        if "max_new_tokens" in updates:
            updates["max_new_tokens"] = int(updates["max_new_tokens"])
        return replace(base, **updates)


def parse_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)
