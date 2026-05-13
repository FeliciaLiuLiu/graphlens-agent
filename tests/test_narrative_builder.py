from __future__ import annotations

from afc_network_narrative.app.pipeline import analyze_graph
from test_graph_features import fan_in_graph


def test_narrative_includes_limitations_and_cautious_language() -> None:
    output = analyze_graph(fan_in_graph()).to_dict()
    narrative = output["narrative"]
    lowered = narrative.lower()
    assert output["limitations"]
    assert "limitations and missing context" in lowered
    assert "confirmed money laundering" not in lowered
    assert "sar required" not in lowered
    assert "potential" in lowered or "consistent with" in lowered
