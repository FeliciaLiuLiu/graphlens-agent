from __future__ import annotations

from afc_network_narrative.harness.app.pipeline import analyze_graph
from test_graph_features import fan_in_graph


def test_narrative_includes_limitations_and_cautious_language() -> None:
    output = analyze_graph(fan_in_graph()).to_dict()
    narrative = output["narrative"]
    lowered = narrative.lower()
    assert output["limitations"]
    assert output["sar_red_flags"]["decision"] == "not_determined_by_system"
    assert output["sar_red_flags"]["matched_review_signals"]
    assert "alert-review candidate assessment" in lowered
    assert "what the graph shows" in lowered
    assert "afc pattern meaning" in lowered
    assert "why this graph should be reviewed" in lowered
    assert "next analyst checks" in lowered
    assert "fund_collector" in lowered
    assert "limitations and missing context" in lowered
    assert "red flag review signals" in lowered
    assert "confirmed money laundering" not in lowered
    assert "sar required" not in lowered
    assert "potential" in lowered or "consistent with" in lowered
