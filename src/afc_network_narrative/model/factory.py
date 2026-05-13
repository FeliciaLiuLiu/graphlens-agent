from __future__ import annotations

from dataclasses import replace
from typing import Any

from afc_network_narrative.model.base import VLMAdapter, VLMAdapterError
from afc_network_narrative.model.config import VLMConfig
from afc_network_narrative.model.florence import Florence2Adapter
from afc_network_narrative.model.ollama import OllamaVLMAdapter
from afc_network_narrative.model.placeholders import (
    ApprovedEndpointVLMAdapter,
    ClaudeVLMAdapter,
    GeminiVLMAdapter,
    GraniteVisionAdapter,
    LlamaVisionAdapter,
    OpenAIVLMAdapter,
)
from afc_network_narrative.model.prompt_loader import load_extraction_prompt
from afc_network_narrative.model.qwen import QwenVLAdapter

SUPPORTED_BACKENDS = {
    "qwen",
    "ollama",
    "florence2",
    "approved_endpoint",
    "llama",
    "gemini",
    "openai",
    "claude",
    "granite",
}

UNIMPLEMENTED_BACKENDS = {
    "approved_endpoint": ApprovedEndpointVLMAdapter,
    "llama": LlamaVisionAdapter,
    "gemini": GeminiVLMAdapter,
    "openai": OpenAIVLMAdapter,
    "claude": ClaudeVLMAdapter,
    "granite": GraniteVisionAdapter,
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

    if selected_backend == "ollama":
        return OllamaVLMAdapter(config=ensure_extraction_prompt(resolved))
    if selected_backend == "qwen":
        return QwenVLAdapter(config=ensure_extraction_prompt(resolved))
    if selected_backend == "florence2":
        return Florence2Adapter(config=ensure_extraction_prompt(resolved))

    if selected_backend in UNIMPLEMENTED_BACKENDS:
        raise VLMAdapterError(
            f"VLM backend {selected_backend!r} is recognized but not implemented yet. "
            "Add a concrete adapter that returns GraphExtraction before selecting this backend."
        )

    raise VLMAdapterError(f"VLM backend {selected_backend!r} is not available.")


def ensure_extraction_prompt(config: VLMConfig) -> VLMConfig:
    if config.extraction_prompt is not None:
        return config
    prompt = load_extraction_prompt(config.extraction_prompt_path)
    return replace(config, extraction_prompt=prompt)


def normalize_backend_name(value: str) -> str:
    normalized = value.strip().lower()
    aliases = {
        "hf": "qwen",
        "huggingface": "qwen",
        "qwen2.5vl": "ollama",
        "qwen2.5vl:3b": "ollama",
        "ollama-qwen2.5vl": "ollama",
        "ollama-qwen2.5vl-3b": "ollama",
        "qwen2.5-vl": "qwen",
        "qwen2.5-vl-7b": "qwen",
        "qwen2_5_vl": "qwen",
        "florence": "florence2",
        "florence-2": "florence2",
        "florence_2": "florence2",
        "florence2-base-ft": "florence2",
        "florence-2-base-ft": "florence2",
        "approved": "approved_endpoint",
        "company": "approved_endpoint",
        "company_approved": "approved_endpoint",
        "llama_vision": "llama",
        "llama-vision": "llama",
        "vertex": "gemini",
        "vertex_ai": "gemini",
        "vertex-ai": "gemini",
        "ibm_granite": "granite",
        "granite_vision": "granite",
    }
    return aliases.get(normalized, normalized)
