from __future__ import annotations

import json
from dataclasses import replace
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


class Pixtral12BAdapter(VLMAdapter):
    """Local Pixtral 12B implementation of the VLMAdapter contract."""

    def __init__(
        self,
        config: VLMConfig | dict[str, Any] | None = None,
        *,
        model_path: str | Path | None = None,
        max_retries: int = 1,
        mock_json: dict[str, Any] | str | None = None,
    ) -> None:
        resolved = VLMConfig.from_mapping(config)
        if model_path is not None:
            resolved = replace(resolved, pixtral_model_path=str(model_path))
        self.config = resolved
        self.model_path = Path(resolved.pixtral_model_path)
        self.max_retries = max_retries
        self.mock_json = mock_json
        self._model = None
        self._processor = None

    def extract_graph(self, image_path: str) -> GraphExtraction:
        if self.mock_json is not None:
            return validate_graph_extraction(self.mock_json)

        image = Path(image_path)
        if not image.exists():
            raise VLMAdapterError(f"Image not found: {image}")
        if not self.model_path.exists():
            raise VLMAdapterError(
                f"Local Pixtral 12B model path does not exist: {self.model_path}. "
                "Set PIXTRAL_MODEL_PATH or run scripts/download_pixtral.py after approval."
            )

        last_error: Exception | None = None
        repair_instruction = ""
        for _attempt in range(self.max_retries + 1):
            prompt = self._extraction_prompt()
            if repair_instruction:
                prompt += "\n" + repair_instruction
            try:
                response_text = self._run_pixtral(image, prompt)
                return validate_graph_extraction(extract_json_text(response_text))
            except (GraphValidationError, json.JSONDecodeError, VLMAdapterError) as exc:
                last_error = exc
                repair_instruction = (
                    "Previous output was not valid JSON for the requested schema. "
                    f"Return corrected JSON only. Error: {exc}"
                )

        raise VLMAdapterError(f"Pixtral 12B graph extraction failed after retry: {last_error}")

    def _extraction_prompt(self) -> str:
        if self.config.extraction_prompt is not None:
            return self.config.extraction_prompt
        raise VLMAdapterError("Pixtral12BAdapter requires VLMConfig.extraction_prompt.")

    def _run_pixtral(self, image_path: Path, prompt: str) -> str:
        model, processor = self._load_model()
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "content": prompt},
                    {"type": "image", "url": str(image_path)},
                ],
            }
        ]

        try:
            inputs = processor.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
            ).to(model.device)
        except TypeError as exc:
            raise VLMAdapterError(
                "Installed transformers build does not support Pixtral chat-template processing. "
                "Use the repository requirements so Pixtral support is available."
            ) from exc

        output_ids = model.generate(**inputs, max_new_tokens=self.config.max_new_tokens)
        prompt_length = inputs["input_ids"].shape[-1]
        return processor.decode(
            output_ids[0][prompt_length:],
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )

    def _load_model(self):
        if self._model is not None and self._processor is not None:
            return self._model, self._processor

        try:
            from transformers import AutoModelForImageTextToText, AutoProcessor  # type: ignore
        except ImportError as exc:
            raise VLMAdapterError(
                "Pixtral dependencies are not installed. Install requirements and a compatible torch build first."
            ) from exc

        self._model = AutoModelForImageTextToText.from_pretrained(
            str(self.model_path),
            device_map="auto",
            torch_dtype="auto",
        )
        self._processor = AutoProcessor.from_pretrained(str(self.model_path))
        return self._model, self._processor
