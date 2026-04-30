import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from graphlens_agent.analytics import analyze_graph
from graphlens_agent.narrative import generate_narrative


SAMPLE_PATH = ROOT / "samples" / "fan_in_collector.json"


def load_sample():
    return json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))


def unknown_motif_graph():
    return {
        "metadata": {
            "schema_version": "1.0",
            "source_type": "synthetic",
            "directed": True,
            "extraction_confidence": 1.0,
        },
        "nodes": [
            {"id": "a", "label": "A", "confidence": 1.0},
            {"id": "b", "label": "B", "confidence": 1.0},
            {"id": "c", "label": "C", "confidence": 1.0},
            {"id": "d", "label": "D", "confidence": 1.0},
            {"id": "e", "label": "E", "confidence": 1.0},
        ],
        "edges": [
            {"id": "edge_ab", "source": "a", "target": "b", "confidence": 1.0},
            {"id": "edge_de", "source": "d", "target": "e", "confidence": 1.0},
        ],
        "warnings": [],
    }


def test_rule_based_narrative_for_fan_in_aggregation():
    graph = load_sample()
    analytics = analyze_graph(graph)

    narrative = generate_narrative(graph, analytics)

    assert narrative["Plain-Language Summary"].startswith("This graph shows a fan-in pattern")
    assert "Central Account (acct_collector)" in narrative["Plain-Language Summary"]
    assert "5 nodes and 4 edges" in narrative["Plain-Language Summary"]
    assert "1975" in narrative["Plain-Language Summary"]
    assert "collector node" in narrative["What Is Happening"]
    assert any("not proof of wrongdoing" in caveat for caveat in narrative["Caveats"])


def test_rule_based_narrative_unknown_motif_fallback():
    graph = unknown_motif_graph()
    analytics = analyze_graph(graph)

    narrative = generate_narrative(graph, analytics)

    assert analytics["summary"]["graph_motif"] == "unknown"
    assert "does not match one of the currently supported narrative patterns" in narrative["Plain-Language Summary"]
    assert any("No supported motif-specific narrative was matched" in caveat for caveat in narrative["Caveats"])
