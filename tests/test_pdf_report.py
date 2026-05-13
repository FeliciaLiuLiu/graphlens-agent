from __future__ import annotations

from afc_network_narrative.harness.app.pipeline import analyze_graph
from afc_network_narrative.harness.reporting.pdf_report import build_report_pdf_bytes
from test_graph_features import fan_in_graph


def test_pdf_report_generation_contains_expected_text() -> None:
    output = analyze_graph(fan_in_graph())
    pdf_bytes = build_report_pdf_bytes(output, input_name="fan_in_test.png")
    assert pdf_bytes.startswith(b"%PDF-")
    assert b"AFC Network Narrative Report" in pdf_bytes
    assert b"Human-Readable Narrative" in pdf_bytes
    assert b"fan-in collection" in pdf_bytes
    assert b"Input reference: fan_in_test.png" in pdf_bytes
