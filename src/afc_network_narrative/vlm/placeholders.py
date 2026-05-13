from __future__ import annotations

from typing import Any

from afc_network_narrative.schemas.graph_extraction_schema import GraphExtraction
from afc_network_narrative.vlm.base import VLMAdapter, VLMAdapterError
from afc_network_narrative.vlm.config import VLMConfig


class NotImplementedVLMAdapter(VLMAdapter):
    backend_name = "unknown"

    def __init__(self, config: VLMConfig | dict[str, Any] | None = None) -> None:
        self.config = VLMConfig.from_mapping(config)

    def extract_graph(self, image_path: str) -> GraphExtraction:
        raise VLMAdapterError(
            f"VLM backend {self.backend_name!r} is recognized but not implemented yet. "
            "Implement model-specific request, response parsing, and GraphExtraction normalization in its adapter."
        )


class ApprovedEndpointVLMAdapter(NotImplementedVLMAdapter):
    backend_name = "approved_endpoint"
    # TODO: Call a company-approved multimodal endpoint, parse its response locally,
    # and normalize the result into GraphExtraction.


class LlamaVisionAdapter(NotImplementedVLMAdapter):
    backend_name = "llama"
    # TODO: Add Llama Vision request/model-loading logic and normalize output into GraphExtraction.


class GeminiVLMAdapter(NotImplementedVLMAdapter):
    backend_name = "gemini"
    # TODO: Add Gemini or Vertex AI request logic and normalize output into GraphExtraction.


class OpenAIVLMAdapter(NotImplementedVLMAdapter):
    backend_name = "openai"
    # TODO: Add OpenAI vision endpoint request logic and normalize output into GraphExtraction.


class ClaudeVLMAdapter(NotImplementedVLMAdapter):
    backend_name = "claude"
    # TODO: Add Claude vision endpoint request logic and normalize output into GraphExtraction.


class GraniteVisionAdapter(NotImplementedVLMAdapter):
    backend_name = "granite"
    # TODO: Add IBM Granite Vision request/model-loading logic and normalize output into GraphExtraction.
