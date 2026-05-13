from __future__ import annotations

from afc_network_narrative.features.graph_features import build_graph_features
from afc_network_narrative.schemas.graph_extraction_schema import validate_graph_extraction
from test_graph_features import edge, node


def test_pass_through_relay_motif() -> None:
    graph = validate_graph_extraction(
        {
            "case_id": "relay_case",
            "nodes": [
                node("a", "sender_a"),
                node("b", "sender_b"),
                node("relay", "relay_account", role="relay"),
                node("c", "recipient_c"),
                node("d", "recipient_d"),
            ],
            "edges": [
                edge("a", "relay", "$1.7k", 1700.0),
                edge("b", "relay", "$1.7k", 1700.0),
                edge("relay", "c", "$1.7k", 1700.0),
                edge("relay", "d", "$1.7k", 1700.0),
            ],
            "visual_signals": {},
            "extraction_uncertainties": [],
        }
    )
    features = build_graph_features(graph)
    assert "relay" in features.motifs.pass_through_relay
    assert len(features.motifs.two_hop_paths) >= 4
