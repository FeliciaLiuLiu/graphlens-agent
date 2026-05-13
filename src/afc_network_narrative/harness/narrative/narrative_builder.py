from __future__ import annotations

from pathlib import Path
from typing import Any

from afc_network_narrative.harness.app.skill_loader import (
    load_investigation_playbooks,
    load_narrative_policy,
    load_narrative_template,
    load_prohibited_claims,
)
from afc_network_narrative.harness.features.graph_features import GraphFeatures
from afc_network_narrative.harness.narrative.grounding import assert_no_prohibited_claims, build_evidence
from afc_network_narrative.harness.rules.rule_engine import TypologyMatch, missing_context_limitations
from afc_network_narrative.harness.schemas.afc_output_schema import AFCNarrativeOutput
from afc_network_narrative.harness.schemas.graph_extraction_schema import GraphExtraction


def build_narrative_output(
    graph: GraphExtraction,
    features: GraphFeatures,
    matches: list[TypologyMatch],
    alert_boost: dict[str, Any],
) -> AFCNarrativeOutput:
    playbooks = load_investigation_playbooks()
    prohibited = load_prohibited_claims()
    narrative_policy = load_narrative_policy()
    narrative_template = load_narrative_template()

    limitations = build_limitations(features, matches, narrative_policy)
    recommended_steps = build_recommended_steps(matches, playbooks)
    graph_summary = build_graph_summary(graph, features)
    narrative = compose_narrative(
        graph_summary,
        matches,
        alert_boost,
        recommended_steps,
        limitations,
        narrative_policy,
        narrative_template,
    )
    assert_no_prohibited_claims(narrative, prohibited)
    return AFCNarrativeOutput(
        graph_summary=graph_summary,
        detected_typologies=[match.to_dict() for match in matches],
        alert_boost=alert_boost,
        recommended_investigation_steps=recommended_steps,
        narrative=narrative,
        limitations=limitations,
        evidence=build_evidence(graph, matches),
    )


def build_graph_summary(graph: GraphExtraction, features: GraphFeatures) -> dict[str, Any]:
    return {
        "case_id": graph.case_id,
        "node_count": len(graph.nodes),
        "edge_count": len(graph.edges),
        "repeated_amount_score": features.repeated_amount_score,
        "repeated_amount_value": features.repeated_amount_value,
        "motifs": features.motifs.to_dict(),
        "missing_context_flags": features.missing_context_flags,
        "overall_extraction_confidence": features.overall_extraction_confidence,
        "node_features": {node_id: feature.to_dict() for node_id, feature in features.node_features.items()},
    }


def compose_narrative(
    graph_summary: dict[str, Any],
    matches: list[TypologyMatch],
    alert_boost: dict[str, Any],
    recommended_steps: list[str],
    limitations: list[str],
    narrative_policy: dict[str, Any],
    narrative_template: str,
) -> str:
    templates = narrative_policy["section_templates"]
    rendering = narrative_policy["rendering"]
    motifs = graph_summary["motifs"]
    observation = templates["network_observation"].format(
        node_count=graph_summary["node_count"],
        edge_count=graph_summary["edge_count"],
        fan_in_nodes=format_list(motifs["fan_in"], none_text=rendering["none_text"]),
        fan_out_nodes=format_list(motifs["fan_out"], none_text=rendering["none_text"]),
        pass_through_nodes=format_list(motifs["pass_through_relay"], none_text=rendering["none_text"]),
    )

    if matches:
        hypothesis_parts = []
        for match in matches:
            evidence_text = rendering["list_joiner"].join(
                format_evidence(item, narrative_policy) for item in match.matched_evidence[:3]
            )
            hypothesis_parts.append(
                templates["typology_hypothesis"].format(
                    typology_name=match.name,
                    confidence=match.confidence,
                    evidence=evidence_text,
                    caution=match.caution,
                )
            )
        hypothesis = rendering["section_joiner"].join(hypothesis_parts)
    else:
        hypothesis = templates["no_match_hypothesis"]

    boost = templates["alert_boost"].format(
        priority_band=alert_boost["priority_band"],
        score=alert_boost["score"],
        explanation=alert_boost["explanation"],
    )
    evidence = build_key_evidence(matches, narrative_policy)
    steps = rendering["list_joiner"].join(recommended_steps)
    limits = rendering["section_joiner"].join(limitations)
    return narrative_template.format(
        network_observation=observation,
        typology_hypothesis=hypothesis,
        alert_boost=boost,
        evidence=evidence,
        recommended_steps=steps,
        limitations=limits,
    )


def format_evidence(item: dict[str, Any], narrative_policy: dict[str, Any]) -> str:
    templates = narrative_policy["section_templates"]
    node = f" on node {item['node_id']}" if item.get("node_id") else ""
    value = item.get("value")
    if "amount_value" in item and item["amount_value"] is not None:
        return templates["evidence_item_with_amount"].format(
            metric=item.get("metric", "evidence"),
            value=value,
            amount_value=item["amount_value"],
            node_suffix=node,
        )
    return templates["evidence_item"].format(
        metric=item.get("metric", "evidence"),
        value=value,
        node_suffix=node,
    )


def build_limitations(
    features: GraphFeatures,
    matches: list[TypologyMatch],
    narrative_policy: dict[str, Any],
) -> list[str]:
    limitations = []
    for match in matches:
        limitations.extend(match.limitations)
    limitations.extend(missing_context_limitations(features))
    limitations.extend(narrative_policy.get("static_limitations", []))
    return dedupe(limitations)


def build_recommended_steps(matches: list[TypologyMatch], playbooks: dict[str, Any]) -> list[str]:
    steps = list(playbooks.get("default_steps", []))
    for match in matches:
        steps.extend(playbooks.get("typology_steps", {}).get(match.typology_id, []))
    return dedupe(steps)


def dedupe(items: list[str]) -> list[str]:
    seen = set()
    output = []
    for item in items:
        if item not in seen:
            output.append(item)
            seen.add(item)
    return output


def build_key_evidence(matches: list[TypologyMatch], narrative_policy: dict[str, Any]) -> str:
    templates = narrative_policy["section_templates"]
    rendering = narrative_policy["rendering"]
    if not matches:
        return templates["key_evidence_fallback"]

    rendered = []
    for match in matches:
        evidence = rendering["list_joiner"].join(
            format_evidence(item, narrative_policy) for item in match.matched_evidence[:3]
        )
        rendered.append(templates["key_evidence_match"].format(typology_name=match.name, evidence=evidence))
    return rendering["section_joiner"].join(rendered)


def format_list(values: list[Any], *, none_text: str) -> str:
    if not values:
        return none_text
    return ", ".join(str(value) for value in values)
