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


class QwenVLAdapter(VLMAdapter):
    """Qwen2.5-VL implementation of the generic VLMAdapter contract."""

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
            resolved = replace(resolved, qwen_model_path=str(model_path))
        self.config = resolved
        self.model_path = Path(resolved.qwen_model_path)
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
                f"Local Qwen2.5-VL model path does not exist: {self.model_path}. "
                "Set QWEN_MODEL_PATH or run scripts/download_qwen.py after approval."
            )

        last_error: Exception | None = None
        repair_instruction = ""
        for _attempt in range(self.max_retries + 1):
            prompt = self._extraction_prompt()
            if repair_instruction:
                prompt += "\n" + repair_instruction
            try:
                response_text = self._run_qwen(image, prompt)
                return validate_graph_extraction(extract_json_text(response_text))
            except (GraphValidationError, json.JSONDecodeError, VLMAdapterError) as exc:
                last_error = exc
                repair_instruction = (
                    "Previous output was not valid JSON for the requested schema. "
                    f"Return corrected JSON only. Error: {exc}"
                )

        raise VLMAdapterError(f"Qwen graph extraction failed after retry: {last_error}")

    def extract_graph_json(self, image_path: str) -> GraphExtraction:
        return self.extract_graph(image_path)

    def _extraction_prompt(self) -> str:
        if self.config.extraction_prompt is not None:
            return self.config.extraction_prompt
        raise VLMAdapterError("QwenVLAdapter requires VLMConfig.extraction_prompt.")

    def _run_qwen(self, image_path: Path, prompt: str) -> str:
        model, processor, process_vision_info = self._load_model()
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": str(image_path)},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        inputs = inputs.to(model.device)
        generated_ids = model.generate(**inputs, max_new_tokens=self.config.max_new_tokens)
        generated_ids_trimmed = [
            output_ids[len(input_ids) :]
            for input_ids, output_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = processor.batch_decode(
            generated_ids_trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )
        return output_text[0]

    def _load_model(self):
        if self._model is not None and self._processor is not None:
            from qwen_vl_utils import process_vision_info  # type: ignore

            return self._model, self._processor, process_vision_info

        try:
            from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration  # type: ignore
            from qwen_vl_utils import process_vision_info  # type: ignore
        except ImportError as exc:
            raise VLMAdapterError(
                "Qwen dependencies are not installed. Install requirements and a compatible torch build first."
            ) from exc

        self._model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            str(self.model_path),
            torch_dtype="auto",
            device_map="auto",
        )
        self._processor = AutoProcessor.from_pretrained(str(self.model_path))
        return self._model, self._processor, process_vision_info
