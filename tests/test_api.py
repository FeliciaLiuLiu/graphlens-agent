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


def test_explain_graph_endpoint_returns_analytics_and_narrative():
    response = client.post("/explain-graph", json=load_sample())

    assert response.status_code == 200
    result = response.json()
    assert result["analytics"]["summary"]["graph_motif"] == "fan_in_aggregation"
    assert result["analytics"]["summary"]["collector_node"] == "acct_collector"
    narrative = result["narrative"]
    assert "Plain-Language Summary" in narrative
    assert "Central Account (acct_collector)" in narrative["Plain-Language Summary"]
    assert "not proof of wrongdoing" in " ".join(narrative["Caveats"])


def test_extract_graph_accepts_valid_png_upload():
    response = client.post(
        "/extract-graph",
        files={"file": ("graph.png", b"fake image bytes", "image/png")},
    )

    assert response.status_code == 200
    graph = response.json()
    assert graph["metadata"]["schema_version"] == "1.0"
    assert graph["metadata"]["source_type"] == "screenshot"


def test_extract_graph_rejects_invalid_file_type():
    response = client.post(
        "/extract-graph",
        files={"file": ("graph.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_extract_graph_returns_successful_mock_graph_json_response():
    response = client.post(
        "/extract-graph",
        files={"file": ("network.jpeg", b"fake image bytes", "image/jpeg")},
    )

    assert response.status_code == 200
    graph = response.json()
    assert len(graph["nodes"]) == 5
    assert len(graph["edges"]) == 4
    assert graph["nodes"][-1]["id"] == "acct_collector"
    assert any("Mock extraction result" in warning for warning in graph["warnings"])


def test_extract_graph_invalid_provider_name_returns_clear_error(monkeypatch):
    monkeypatch.setenv("GRAPH_EXTRACTION_PROVIDER", "unsupported")

    response = client.post(
        "/extract-graph",
        files={"file": ("network.png", b"fake image bytes", "image/png")},
    )

    assert response.status_code == 500
    assert "Unsupported GRAPH_EXTRACTION_PROVIDER" in response.json()["detail"]
    assert "mock, local_cv" in response.json()["detail"]


def test_extract_graph_local_cv_returns_501(monkeypatch):
    monkeypatch.setenv("GRAPH_EXTRACTION_PROVIDER", "local_cv")

    response = client.post(
        "/extract-graph",
        files={"file": ("network.png", b"fake image bytes", "image/png")},
    )

    assert response.status_code == 501
    assert "Local OCR/OpenCV screenshot extraction is planned but not implemented yet" in response.json()["detail"]


def test_screenshot_to_narrative_pipeline_successful_mock(monkeypatch):
    monkeypatch.delenv("GRAPH_EXTRACTION_PROVIDER", raising=False)

    response = client.post(
        "/pipeline/screenshot-to-narrative",
        files={"file": ("graph.png", b"fake image bytes", "image/png")},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["provider_used"] == "MockScreenshotExtractionProvider"
    assert result["graph"]["metadata"]["schema_version"] == "1.0"
    assert result["analytics"]["summary"]["graph_motif"] == "fan_in_aggregation"
    assert "Central Account (acct_collector)" in result["narrative"]["Plain-Language Summary"]
    assert any("Mock extraction result" in warning for warning in result["warnings"])


def test_screenshot_to_narrative_pipeline_rejects_invalid_file_type():
    response = client.post(
        "/pipeline/screenshot-to-narrative",
        files={"file": ("graph.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_screenshot_to_narrative_pipeline_local_cv_returns_501(monkeypatch):
    monkeypatch.setenv("GRAPH_EXTRACTION_PROVIDER", "local_cv")

    response = client.post(
        "/pipeline/screenshot-to-narrative",
        files={"file": ("graph.png", b"fake image bytes", "image/png")},
    )

    assert response.status_code == 501
    assert "Local OCR/OpenCV screenshot extraction is planned but not implemented yet" in response.json()["detail"]
