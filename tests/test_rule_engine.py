from __future__ import annotations

from afc_network_narrative.features.graph_features import build_graph_features
from afc_network_narrative.rules.rule_engine import RuleEngine
from afc_network_narrative.schemas.graph_extraction_schema import validate_graph_extraction
from test_graph_features import edge, fan_in_graph, fan_out_graph, node


def match_ids(payload: dict) -> set[str]:
    graph = validate_graph_extraction(payload)
    features = build_graph_features(graph)
    return {match.typology_id for match in RuleEngine().match(graph, features)}


def test_sample_fan_in_matches_fan_in_collection() -> None:
    assert "fan_in_collection" in match_ids(fan_in_graph())


def test_sample_fan_out_matches_fan_out_distribution() -> None:
    assert "fan_out_distribution" in match_ids(fan_out_graph())


def test_repeated_amounts_match_equal_amount_coordination() -> None:
    payload = {
        "case_id": "equal_amount_case",
        "nodes": [node("a", "a"), node("b", "b"), node("c", "c")],
        "edges": [
            edge("a", "b", "$2.7k", 2700.0),
            edge("b", "c", "$2.7k", 2700.0),
            edge("a", "c", "$2.7k", 2700.0),
        ],
        "visual_signals": {},
        "extraction_uncertainties": [],
    }
    assert "equal_amount_coordination" in match_ids(payload)
