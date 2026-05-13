from __future__ import annotations

from dataclasses import replace
from typing import Any

from afc_network_narrative.model.base import VLMAdapter, VLMAdapterError
from afc_network_narrative.model.config import VLMConfig
from afc_network_narrative.model.pixtral import Pixtral12BAdapter
from afc_network_narrative.model.prompt_loader import load_extraction_prompt

SUPPORTED_BACKENDS = {
    "pixtral",
}


def create_vlm_adapter(
    backend: str | None = None,
    config: dict[str, Any] | VLMConfig | None = None,
) -> VLMAdapter:
    resolved = VLMConfig.from_mapping(config)
    selected_backend = normalize_backend_name(backend or resolved.backend)
    resolved = replace(resolved, backend=selected_backend)

    if selected_backend not in SUPPORTED_BACKENDS:
        raise VLMAdapterError(
            f"Unsupported VLM backend {selected_backend!r}. Supported backends: {', '.join(sorted(SUPPORTED_BACKENDS))}."
        )

    return Pixtral12BAdapter(config=ensure_extraction_prompt(resolved))


def ensure_extraction_prompt(config: VLMConfig) -> VLMConfig:
    if config.extraction_prompt is not None:
        return config
    prompt = load_extraction_prompt(config.extraction_prompt_path)
    return replace(config, extraction_prompt=prompt)


def normalize_backend_name(value: str) -> str:
    normalized = value.strip().lower()
    aliases = {
        "hf": "pixtral",
        "huggingface": "pixtral",
        "pixtral-12b": "pixtral",
        "pixtral12b": "pixtral",
        "mistral-community/pixtral-12b": "pixtral",
        "mistral-experimental/pixtral-12b": "pixtral",
    }
    return aliases.get(normalized, normalized)
