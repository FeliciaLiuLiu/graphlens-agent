import copy
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from graphlens_agent.api import app


SAMPLE_PATH = ROOT / "samples" / "fan_in_collector.json"


def load_sample():
    return json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_graph_endpoint_returns_analytics():
    response = client.post("/analyze-graph", json=load_sample())

    assert response.status_code == 200
    analysis = response.json()
    assert analysis["summary"]["graph_motif"] == "fan_in_aggregation"
    assert analysis["summary"]["collector_node"] == "acct_collector"
    assert analysis["summary"]["has_collector_behavior"] is True
    assert analysis["amount_patterns"]["repeated_amounts"] == {"500": 3}


def test_analyze_graph_endpoint_returns_validation_errors():
    payload = load_sample()
    invalid_edge = copy.deepcopy(payload["edges"][0])
    invalid_edge["id"] = "bad_missing_source"
    invalid_edge["source"] = "missing_source"
    payload["edges"].append(invalid_edge)

    response = client.post("/analyze-graph", json=payload)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any(issue["path"].endswith(".source") for issue in detail)
    assert any("unknown source node" in issue["message"] for issue in detail)
