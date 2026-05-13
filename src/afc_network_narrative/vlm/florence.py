from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from afc_network_narrative.schemas.graph_extraction_schema import (
    GraphExtraction,
    GraphValidationError,
    validate_graph_extraction,
)
from afc_network_narrative.vlm.base import VLMAdapter, VLMAdapterError
from afc_network_narrative.vlm.config import VLMConfig
from afc_network_narrative.vlm.json_utils import extract_json_text


class Florence2Adapter(VLMAdapter):
    """Florence-2 implementation of the generic VLMAdapter contract."""

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
            resolved = replace(resolved, florence_model_path=str(model_path))
        self.config = resolved
        self.model_path = Path(resolved.florence_model_path)
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
                f"Local Florence-2 model path does not exist: {self.model_path}. "
                "Set FLORENCE_MODEL_PATH or run scripts/download_florence.py after approval."
            )

        last_error: Exception | None = None
        repair_instruction = ""
        for _attempt in range(self.max_retries + 1):
            prompt = self._extraction_prompt()
            if repair_instruction:
                prompt += "\n" + repair_instruction
            try:
                response_text = self._run_florence(image, prompt)
                return validate_graph_extraction(extract_json_text(response_text))
            except (GraphValidationError, json.JSONDecodeError, VLMAdapterError) as exc:
                last_error = exc
                repair_instruction = (
                    "Previous output was not valid JSON for the requested schema. "
                    f"Return corrected JSON only. Error: {exc}"
                )

        raise VLMAdapterError(f"Florence-2 graph extraction failed after retry: {last_error}")

    def _extraction_prompt(self) -> str:
        if self.config.extraction_prompt is not None:
            return self.config.extraction_prompt
        raise VLMAdapterError("Florence2Adapter requires VLMConfig.extraction_prompt.")

    def _run_florence(self, image_path: Path, prompt: str) -> str:
        model, processor = self._load_model()
        try:
            from PIL import Image
        except ImportError as exc:
            raise VLMAdapterError("Florence2Adapter requires pillow.") from exc

        image = Image.open(image_path).convert("RGB")
        inputs = processor(text=prompt, images=image, return_tensors="pt")
        device = next(model.parameters()).device
        inputs = {
            key: value.to(device) if hasattr(value, "to") else value
            for key, value in inputs.items()
        }
        generated_ids = model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=self.config.max_new_tokens,
            num_beams=3,
            do_sample=False,
        )
        generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
        return str(generated_text)

    def _load_model(self):
        if self._model is not None and self._processor is not None:
            return self._model, self._processor

        try:
            import torch  # type: ignore
            from transformers import AutoModelForCausalLM, AutoProcessor  # type: ignore
        except ImportError as exc:
            raise VLMAdapterError(
                "Florence-2 dependencies are not installed. Install torch, transformers, timm, einops, and pillow first."
            ) from exc

        if torch.cuda.is_available():
            device = "cuda"
            torch_dtype = torch.float16
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            device = "mps"
            torch_dtype = torch.float32
        else:
            device = "cpu"
            torch_dtype = torch.float32
        self._model = AutoModelForCausalLM.from_pretrained(
            str(self.model_path),
            trust_remote_code=True,
            torch_dtype=torch_dtype,
        ).to(device)
        self._processor = AutoProcessor.from_pretrained(
            str(self.model_path),
            trust_remote_code=True,
        )
        return self._model, self._processor
