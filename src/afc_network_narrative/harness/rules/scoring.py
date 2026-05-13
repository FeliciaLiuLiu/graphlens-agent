from __future__ import annotations

from pathlib import Path
from typing import Any

from afc_network_narrative.harness.app.skill_loader import load_sar_red_flags, load_scoring_policy, load_typology_skill
from afc_network_narrative.harness.features.graph_features import GraphFeatures
from afc_network_narrative.harness.rules.rule_engine import TypologyMatch
from afc_network_narrative.harness.schemas.graph_extraction_schema import GraphExtraction


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

    for match in scoreable_typology_matches(matches, typology_points, policy.get("typology_scoring", {})):
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
        "sar_review": build_sar_review(band, policy.get("sar_review_policy", {})),
        "sar_red_flags": build_sar_red_flags(matches),
        "scenario_coverage": build_scenario_coverage(matches),
    }


def scoreable_typology_matches(
    matches: list[TypologyMatch],
    typology_points: dict[str, int],
    typology_scoring: dict[str, Any],
) -> list[TypologyMatch]:
    mode = typology_scoring.get("mode", "additive")
    if mode != "max_per_risk_family":
        return matches

    selected: dict[str, TypologyMatch] = {}
    for match in matches:
        family = match.risk_family or match.typology_id
        current = selected.get(family)
        if current is None or int(typology_points[match.typology_id]) > int(typology_points[current.typology_id]):
            selected[family] = match
    return list(selected.values())


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


def build_sar_review(priority_band_name: str, policy: dict[str, Any]) -> dict[str, Any]:
    if not policy:
        return {
            "decision": "not_determined_by_system",
            "summary": "This system does not make SAR or STR filing decisions.",
            "required_context": [],
            "not_assessed_from_graph_only": [],
        }
    review_text = policy["review_text_by_priority_band"].get(
        priority_band_name,
        policy["review_text_by_priority_band"].get("default", ""),
    )
    summary = f"{policy['boundary_text']} {review_text}".strip()
    return {
        "decision": policy["decision_value"],
        "summary": summary,
        "required_context": list(policy["required_context"]),
        "not_assessed_from_graph_only": list(policy["not_assessed_from_graph_only"]),
    }


def build_sar_red_flags(matches: list[TypologyMatch]) -> dict[str, Any]:
    skill = load_sar_red_flags()
    boundary = skill["decision_boundary"]
    matches_by_typology = {match.typology_id: match for match in matches}
    matched_review_signals = []

    for red_flag in skill.get("red_flags", []):
        related_typologies = [str(item) for item in red_flag["related_typologies"]]
        supporting_matches = [
            matches_by_typology[typology_id]
            for typology_id in related_typologies
            if typology_id in matches_by_typology
        ]
        if not supporting_matches:
            continue
        matched_review_signals.append(
            {
                "red_flag_id": red_flag["id"],
                "name": red_flag["name"],
                "status": boundary["matched_signal_status"],
                "matched_text": red_flag["matched_text"],
                "review_question": red_flag["review_question"],
                "caution": red_flag["caution"],
                "recommended_checks": list(red_flag["recommended_checks"]),
                "requires_context": list(red_flag.get("requires_context", [])),
                "source_registry_ids": list(red_flag["source_registry_ids"]),
                "supporting_typologies": [
                    {
                        "typology_id": match.typology_id,
                        "name": match.name,
                        "confidence": match.confidence,
                        "matched_evidence": match.matched_evidence[:3],
                    }
                    for match in supporting_matches
                ],
            }
        )

    return {
        "decision": boundary["decision_value"],
        "summary": boundary["summary"],
        "matched_review_signals": matched_review_signals,
        "context_required_red_flags_not_assessed_from_graph_only": [
            {
                "red_flag_id": red_flag["id"],
                "name": red_flag["name"],
                "status": boundary["context_only_status"],
                "description": red_flag["description"],
                "required_context": list(red_flag["required_context"]),
                "review_guidance": red_flag["review_guidance"],
                "caution": red_flag["caution"],
                "source_registry_ids": list(red_flag["source_registry_ids"]),
            }
            for red_flag in skill.get("context_required_red_flags", [])
        ],
    }


def build_scenario_coverage(matches: list[TypologyMatch]) -> dict[str, Any]:
    skill = load_typology_skill()
    return {
        "graph_supported_matches": [
            {
                "typology_id": match.typology_id,
                "name": match.name,
                "risk_family": match.risk_family,
                "scenario_type": match.scenario_type,
            }
            for match in matches
        ],
        "context_required_scenarios_not_assessed_from_graph_only": [
            {
                "scenario_id": scenario["id"],
                "name": scenario["name"],
                "required_context": list(scenario["required_context"]),
                "caution": scenario["caution"],
            }
            for scenario in skill.get("context_required_scenarios", [])
        ],
    }
