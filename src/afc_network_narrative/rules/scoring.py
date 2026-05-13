from __future__ import annotations

from pathlib import Path
from typing import Any

from afc_network_narrative.app.skill_loader import load_scoring_policy
from afc_network_narrative.features.graph_features import GraphFeatures
from afc_network_narrative.rules.rule_engine import TypologyMatch
from afc_network_narrative.schemas.graph_extraction_schema import GraphExtraction


def score_alert(
    graph: GraphExtraction,
    features: GraphFeatures,
    matches: list[TypologyMatch],
    policy_path: str | Path | None = None,
) -> dict[str, Any]:
    policy = load_scoring_policy(policy_path)
    score = 0
    reason_codes: list[dict[str, Any]] = []
    typology_points = policy["typology_points"]
    reason_templates = policy["reason_templates"]

    for match in matches:
        points = int(typology_points[match.typology_id])
        if points:
            score += points
            reason_codes.append(
                {
                    "code": f"typology:{match.typology_id}",
                    "points": points,
                    "reason": reason_templates["typology_match"].format(typology_name=match.name),
                }
            )

    boosts = policy["boosts"]
    if features.repeated_amount_score >= float(policy["repeated_amount_min_score"]):
        points = int(boosts["repeated_amount"])
        score += points
        reason_codes.append(
            {
                "code": "boost:repeated_amount",
                "points": points,
                "reason": reason_templates["repeated_amount"],
            }
        )

    if features.distinct_counterparty_count >= int(policy["distinct_counterparty_threshold"]):
        points = int(boosts["distinct_counterparties"])
        score += points
        reason_codes.append(
            {
                "code": "boost:distinct_counterparties",
                "points": points,
                "reason": reason_templates["distinct_counterparties"],
            }
        )

    if has_supported_role_label(graph, matches, policy["supported_role_labels"]):
        points = int(boosts["supported_role_label"])
        score += points
        reason_codes.append(
            {
                "code": "boost:supported_role_label",
                "points": points,
                "reason": reason_templates["supported_role_label"],
            }
        )

    if features.overall_extraction_confidence < float(policy["low_confidence_threshold"]):
        points = int(policy["deductions"]["low_extraction_confidence"])
        score += points
        reason_codes.append(
            {
                "code": "deduction:low_extraction_confidence",
                "points": points,
                "reason": reason_templates["low_extraction_confidence"],
            }
        )

    score = max(0, min(100, score))
    band = priority_band(score, policy["priority_bands"])
    return {
        "score": score,
        "priority_band": band,
        "reason_codes": reason_codes,
        "explanation": build_explanation(
            score,
            band,
            reason_codes,
            policy["explanation_template"],
            policy["empty_reason_codes_text"],
        ),
    }


def has_supported_role_label(
    graph: GraphExtraction,
    matches: list[TypologyMatch],
    supported_role_labels: list[str],
) -> bool:
    node_lookup = graph.node_by_id()
    matched_node_ids = {
        evidence.get("node_id")
        for match in matches
        for evidence in match.matched_evidence
        if evidence.get("node_id")
    }
    supported = {str(label).strip().lower() for label in supported_role_labels}
    for node_id in matched_node_ids:
        node = node_lookup.get(str(node_id))
        if node and node.role_hint_from_label and node.role_hint_from_label.lower() in supported:
            return True
    return False


def priority_band(score: int, bands: dict[str, list[int]]) -> str:
    for band, bounds in bands.items():
        if int(bounds[0]) <= score <= int(bounds[1]):
            return band
    sorted_bands = sorted(bands.items(), key=lambda item: int(item[1][1]))
    if not sorted_bands:
        raise ValueError("priority_bands must not be empty.")
    return sorted_bands[-1][0] if score > int(sorted_bands[-1][1][1]) else sorted_bands[0][0]


def build_explanation(
    score: int,
    band: str,
    reason_codes: list[dict[str, Any]],
    template: str,
    empty_reason_codes_text: str,
) -> str:
    codes = ", ".join(item["code"] for item in reason_codes) or empty_reason_codes_text
    return template.format(priority_band=band, score=score, reason_codes=codes)
