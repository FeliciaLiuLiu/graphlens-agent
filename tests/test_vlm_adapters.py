from __future__ import annotations

import pytest

from afc_network_narrative.harness.app.pipeline import analyze_image_file
from afc_network_narrative.harness.schemas.graph_extraction_schema import GraphExtraction, validate_graph_extraction
from afc_network_narrative.model import (
    Pixtral12BAdapter,
    VLMAdapter,
    VLMAdapterError,
    create_vlm_adapter,
)
from afc_network_narrative.model.json_utils import extract_json_text


def minimal_graph() -> dict:
    return {
        "case_id": "adapter_case",
        "nodes": [
            {
                "id": "source",
                "label": "SOURCE",
                "visible_color": None,
                "role_hint_from_label": None,
                "confidence": 0.9,
            },
            {
                "id": "target",
                "label": "TARGET",
                "visible_color": None,
                "role_hint_from_label": None,
                "confidence": 0.9,
            },
        ],
        "edges": [
            {
                "source": "source",
                "target": "target",
                "amount_text": "$1.2k",
                "amount_value": 1200.0,
                "currency": "USD",
                "visible_color": None,
                "direction_confidence": 0.9,
                "amount_confidence": 0.9,
            }
        ],
        "visual_signals": {},
        "extraction_uncertainties": [],
    }


class FakeVLMAdapter(VLMAdapter):
    def __init__(self) -> None:
        self.called_with: str | None = None

    def extract_graph(self, image_path: str) -> GraphExtraction:
        self.called_with = image_path
        return validate_graph_extraction(minimal_graph())


def test_vlm_adapter_interface_exists() -> None:
    assert hasattr(VLMAdapter, "extract_graph")


def test_pixtral_adapter_conforms_to_vlm_adapter() -> None:
    adapter = Pixtral12BAdapter(config={"extraction_prompt": "prompt"}, mock_json=minimal_graph())
    assert isinstance(adapter, VLMAdapter)
    graph = adapter.extract_graph("unused.png")
    assert graph.case_id == "adapter_case"


def test_default_adapter_is_pixtral(monkeypatch) -> None:
    monkeypatch.delenv("VLM_BACKEND", raising=False)
    adapter = create_vlm_adapter(config={"extraction_prompt": "prompt"})
    assert isinstance(adapter, Pixtral12BAdapter)
    assert adapter.config.pixtral_model_path == "./models/mistral-community-pixtral-12b"


def test_create_vlm_adapter_pixtral_returns_pixtral_adapter() -> None:
    adapter = create_vlm_adapter("pixtral", config={"extraction_prompt": "prompt"})
    assert isinstance(adapter, Pixtral12BAdapter)


def test_create_vlm_adapter_pixtral_alias_returns_pixtral_adapter() -> None:
    adapter = create_vlm_adapter("mistral-community/pixtral-12b", config={"extraction_prompt": "prompt"})
    assert isinstance(adapter, Pixtral12BAdapter)


def test_unsupported_backend_raises_clear_error() -> None:
    with pytest.raises(VLMAdapterError, match="Unsupported VLM backend"):
        create_vlm_adapter("unknown", config={"extraction_prompt": "prompt"})


def test_pipeline_calls_adapter_extract_graph(tmp_path) -> None:
    image = tmp_path / "graph.png"
    image.write_bytes(b"fake image")
    adapter = FakeVLMAdapter()

    output = analyze_image_file(str(image), adapter)

    assert adapter.called_with == str(image)
    assert output.graph_summary["case_id"] == "adapter_case"
    assert output.graph_summary["edge_count"] == 1


def test_downstream_pipeline_accepts_model_independent_graph_extraction(tmp_path) -> None:
    image = tmp_path / "graph.png"
    image.write_bytes(b"fake image")

    output = analyze_image_file(str(image), FakeVLMAdapter())

    assert output.narrative
    assert "confirmed money laundering" not in output.narrative.lower()


def test_extract_json_text_from_fenced_response() -> None:
    response = 'extra\n```json\n{"ok": true}\n```\nmore'
    assert extract_json_text(response) == '{"ok": true}'
