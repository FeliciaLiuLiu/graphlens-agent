from __future__ import annotations

import os
from dataclasses import dataclass, replace
from typing import Any

DEFAULT_BACKEND = "ollama"
DEFAULT_OLLAMA_MODEL = "qwen2.5vl:3b"
DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_TIMEOUT_SECONDS = 600
DEFAULT_QWEN_MODEL_PATH = "./models/Qwen2.5-VL-7B-Instruct"
DEFAULT_FLORENCE_MODEL_PATH = "./models/Florence-2-base-ft"
DEFAULT_EXTRACTION_PROMPT_PATH = "./skills/graph_image_extraction/extraction_prompt.md"
DEFAULT_MAX_NEW_TOKENS = 2048


@dataclass(frozen=True)
class VLMConfig:
    backend: str = DEFAULT_BACKEND
    ollama_model: str = DEFAULT_OLLAMA_MODEL
    ollama_host: str = DEFAULT_OLLAMA_HOST
    ollama_timeout_seconds: int = DEFAULT_OLLAMA_TIMEOUT_SECONDS
    qwen_model_path: str = DEFAULT_QWEN_MODEL_PATH
    florence_model_path: str = DEFAULT_FLORENCE_MODEL_PATH
    approved_endpoint_url: str | None = None
    endpoint_url: str | None = None
    api_key_env_var: str | None = None
    max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS
    extraction_prompt_path: str = DEFAULT_EXTRACTION_PROMPT_PATH
    extraction_prompt: str | None = None

    @classmethod
    def from_env(cls) -> "VLMConfig":
        return cls(
            backend=os.getenv("VLM_BACKEND", DEFAULT_BACKEND),
            ollama_model=os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL),
            ollama_host=os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST),
            ollama_timeout_seconds=parse_int_env("OLLAMA_TIMEOUT_SECONDS", DEFAULT_OLLAMA_TIMEOUT_SECONDS),
            qwen_model_path=os.getenv(
                "QWEN_MODEL_PATH",
                os.getenv("QWEN_LOCAL_MODEL_PATH", DEFAULT_QWEN_MODEL_PATH),
            ),
            florence_model_path=os.getenv(
                "FLORENCE_MODEL_PATH",
                os.getenv("FLORENCE_LOCAL_MODEL_PATH", DEFAULT_FLORENCE_MODEL_PATH),
            ),
            approved_endpoint_url=os.getenv("APPROVED_VLM_ENDPOINT_URL"),
            endpoint_url=os.getenv("VLM_ENDPOINT_URL"),
            api_key_env_var=os.getenv("VLM_API_KEY_ENV"),
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
        if "model_path" in config and "qwen_model_path" not in updates and config["model_path"] is not None:
            updates["qwen_model_path"] = config["model_path"]
        if "model_path" in config and "florence_model_path" not in updates and config["model_path"] is not None:
            updates["florence_model_path"] = config["model_path"]
        if "backend" in updates:
            updates["backend"] = str(updates["backend"])
        if "max_new_tokens" in updates:
            updates["max_new_tokens"] = int(updates["max_new_tokens"])
        if "ollama_timeout_seconds" in updates:
            updates["ollama_timeout_seconds"] = int(updates["ollama_timeout_seconds"])
        return replace(base, **updates)


def parse_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)
