from __future__ import annotations

from afc_network_narrative.harness.features.graph_features import build_graph_features
from afc_network_narrative.harness.schemas.graph_extraction_schema import validate_graph_extraction


def test_graph_features_fan_in() -> None:
    graph = validate_graph_extraction(fan_in_graph())
    features = build_graph_features(graph)
    assert features.node_features["fund_collector"].in_degree == 5
    assert "fund_collector" in features.motifs.fan_in
    assert features.repeated_amount_score == 1.0
    assert features.missing_context_flags["timestamps_absent"] is True
    assert features.missing_context_flags["kyc_device_ip_absent"] is True


def test_graph_features_fan_out() -> None:
    graph = validate_graph_extraction(fan_out_graph())
    features = build_graph_features(graph)
    assert features.node_features["fund_distributor"].out_degree == 4
    assert "fund_distributor" in features.motifs.fan_out


def fan_in_graph() -> dict:
    nodes = [
        node("src_1", "sender_1"),
        node("src_2", "sender_2"),
        node("src_3", "sender_3"),
        node("src_4", "sender_4"),
        node("src_5", "sender_5"),
        node("fund_collector", "fund_collector", role="collector"),
    ]
    return {
        "case_id": "fan_in_case",
        "nodes": nodes,
        "edges": [edge(f"src_{index}", "fund_collector", "$10.0k", 10000.0) for index in range(1, 6)],
        "visual_signals": {},
        "extraction_uncertainties": [],
    }


def fan_out_graph() -> dict:
    nodes = [
        node("fund_distributor", "fund_distributor", role="distributor"),
        node("dst_1", "recipient_1"),
        node("dst_2", "recipient_2"),
        node("dst_3", "recipient_3"),
        node("dst_4", "recipient_4"),
    ]
    return {
        "case_id": "fan_out_case",
        "nodes": nodes,
        "edges": [edge("fund_distributor", f"dst_{index}", "$10.0k", 10000.0) for index in range(1, 5)],
        "visual_signals": {},
        "extraction_uncertainties": [],
    }


def node(node_id: str, label: str, role: str | None = None) -> dict:
    return {
        "id": node_id,
        "label": label,
        "visible_color": None,
        "role_hint_from_label": role,
        "confidence": 0.95,
    }


def edge(source: str, target: str, amount_text: str, amount_value: float) -> dict:
    return {
        "source": source,
        "target": target,
        "amount_text": amount_text,
        "amount_value": amount_value,
        "currency": "USD",
        "visible_color": None,
        "direction_confidence": 0.95,
        "amount_confidence": 0.95,
    }
