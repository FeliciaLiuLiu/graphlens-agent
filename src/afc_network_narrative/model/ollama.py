from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from afc_network_narrative.harness.schemas.graph_extraction_schema import (
    GraphExtraction,
    GraphValidationError,
    validate_graph_extraction,
)
from afc_network_narrative.model.base import VLMAdapter, VLMAdapterError
from afc_network_narrative.model.config import VLMConfig
from afc_network_narrative.model.json_utils import extract_json_text


class OllamaVLMAdapter(VLMAdapter):
    """Ollama implementation of the generic VLMAdapter contract."""

    def __init__(
        self,
        config: VLMConfig | dict[str, Any] | None = None,
        *,
        max_retries: int = 1,
        mock_json: dict[str, Any] | str | None = None,
    ) -> None:
        self.config = VLMConfig.from_mapping(config)
        self.max_retries = max_retries
        self.mock_json = mock_json

    def extract_graph(self, image_path: str) -> GraphExtraction:
        if self.mock_json is not None:
            return validate_graph_extraction(self.mock_json)

        image = Path(image_path)
        if not image.exists():
            raise VLMAdapterError(f"Image not found: {image}")

        last_error: Exception | None = None
        repair_instruction = ""
        for _attempt in range(self.max_retries + 1):
            prompt = self._extraction_prompt()
            if repair_instruction:
                prompt += "\n" + repair_instruction
            try:
                response_text = self._run_ollama(image, prompt)
                return validate_graph_extraction(extract_json_text(response_text))
            except (GraphValidationError, json.JSONDecodeError, VLMAdapterError) as exc:
                last_error = exc
                repair_instruction = (
                    "Previous output was not valid JSON for the requested schema. "
                    f"Return corrected JSON only. Error: {exc}"
                )

        raise VLMAdapterError(f"Ollama graph extraction failed after retry: {last_error}")

    def _extraction_prompt(self) -> str:
        if self.config.extraction_prompt is not None:
            return self.config.extraction_prompt
        raise VLMAdapterError("OllamaVLMAdapter requires VLMConfig.extraction_prompt.")

    def _run_ollama(self, image_path: Path, prompt: str) -> str:
        endpoint = f"{self.config.ollama_host.rstrip('/')}/api/chat"
        payload = {
            "model": self.config.ollama_model,
            "stream": False,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [base64.b64encode(image_path.read_bytes()).decode("ascii")],
                }
            ],
            "options": {
                "temperature": 0,
                "num_predict": self.config.max_new_tokens,
            },
        }
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.config.ollama_timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise VLMAdapterError(
                f"Ollama request failed with HTTP {exc.code}: {details}. "
                f"Confirm model {self.config.ollama_model!r} is pulled and Ollama is running."
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise VLMAdapterError(
                "Ollama is not reachable. Start Ollama and pull the configured model first. "
                f"Host: {self.config.ollama_host}; model: {self.config.ollama_model}."
            ) from exc

        try:
            data = json.loads(raw)
            return str(data["message"]["content"])
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise VLMAdapterError(f"Ollama returned an unexpected response: {raw[:500]}") from exc
