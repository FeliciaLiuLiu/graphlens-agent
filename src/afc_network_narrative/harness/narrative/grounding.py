from __future__ import annotations

from typing import Any

from afc_network_narrative.harness.rules.rule_engine import TypologyMatch
from afc_network_narrative.harness.schemas.graph_extraction_schema import GraphExtraction


def build_evidence(graph: GraphExtraction, matches: list[TypologyMatch]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for index, edge in enumerate(graph.edges):
        evidence.append(
            {
                "type": "edge",
                "source_registry_id": "visible_graph_image",
                "edge_index": index,
                "source": edge.source,
                "target": edge.target,
                "amount_text": edge.amount_text,
                "amount_value": edge.amount_value,
                "currency": edge.currency,
                "direction_confidence": edge.direction_confidence,
                "amount_confidence": edge.amount_confidence,
            }
        )
    for match in matches:
        for item in match.matched_evidence:
            evidence.append({"type": "rule_evidence", **item})
    return evidence


def assert_no_prohibited_claims(text: str, prohibited_claims: list[str]) -> None:
    lowered = text.lower()
    for claim in prohibited_claims:
        if claim.lower() in lowered:
            raise ValueError(f"Narrative contains prohibited claim: {claim}")
