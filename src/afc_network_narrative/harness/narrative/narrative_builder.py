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
        sar_red_flags=alert_boost.get("sar_red_flags", {}),
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
    alert_candidate = templates["alert_candidate"].format(
        priority_band=alert_boost["priority_band"],
        score=alert_boost["score"],
        explanation=alert_boost["explanation"],
    )
    observation = templates["network_observation"].format(
        node_count=graph_summary["node_count"],
        edge_count=graph_summary["edge_count"],
        fan_in_nodes=format_node_list(motifs["fan_in"], graph_summary, rendering["none_text"]),
        fan_out_nodes=format_node_list(motifs["fan_out"], graph_summary, rendering["none_text"]),
        pass_through_nodes=format_node_list(motifs["pass_through_relay"], graph_summary, rendering["none_text"]),
        key_entities=build_key_entity_summary(graph_summary, narrative_policy),
    )

    if matches:
        hypothesis_parts = []
        for match in matches:
            evidence_text = rendering["list_joiner"].join(
                format_evidence(item, narrative_policy, graph_summary) for item in match.matched_evidence[:3]
            )
            hypothesis_parts.append(
                templates["typology_hypothesis"].format(
                    typology_name=match.name,
                    afc_interpretation=match.afc_interpretation,
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
        sar_review=alert_boost.get("sar_review", {}).get(
            "summary",
            "This system does not make SAR or STR filing decisions.",
        ),
    )
    sar_red_flags = build_sar_red_flag_text(alert_boost.get("sar_red_flags", {}), narrative_policy)
    evidence = build_key_evidence(matches, narrative_policy, graph_summary)
    steps = rendering["list_joiner"].join(recommended_steps)
    limits = rendering["section_joiner"].join(limitations)
    return narrative_template.format(
        alert_candidate=alert_candidate,
        network_observation=observation,
        typology_hypothesis=hypothesis,
        alert_boost=boost,
        sar_red_flags=sar_red_flags,
        evidence=evidence,
        recommended_steps=steps,
        limitations=limits,
    )


def format_evidence(
    item: dict[str, Any],
    narrative_policy: dict[str, Any],
    graph_summary: dict[str, Any] | None = None,
) -> str:
    templates = narrative_policy["section_templates"]
    rendering = narrative_policy["rendering"]
    node = f" on node {format_node_reference(item['node_id'], graph_summary)}" if item.get("node_id") else ""
    value = item.get("value")
    rendered_value = format_node_list(value, graph_summary, rendering["none_text"]) if isinstance(value, list) else value
    if "amount_value" in item and item["amount_value"] is not None:
        return templates["evidence_item_with_amount"].format(
            metric=item.get("metric", "evidence"),
            value=rendered_value,
            amount_value=item["amount_value"],
            node_suffix=node,
        )
    return templates["evidence_item"].format(
        metric=item.get("metric", "evidence"),
        value=rendered_value,
        node_suffix=node,
    )


def build_sar_red_flag_text(sar_red_flags: dict[str, Any], narrative_policy: dict[str, Any]) -> str:
    templates = narrative_policy["section_templates"]
    rendering = narrative_policy["rendering"]
    signals = sar_red_flags.get("matched_review_signals", []) if sar_red_flags else []
    if not signals:
        return templates["sar_red_flag_no_match"]
    rendered = []
    for signal in signals:
        rendered.append(
            templates["sar_red_flag_match"].format(
                name=signal["name"],
                matched_text=signal["matched_text"],
                review_question=signal["review_question"],
                caution=signal["caution"],
            )
        )
    return rendering["section_joiner"].join(rendered)


def build_key_entity_summary(graph_summary: dict[str, Any], narrative_policy: dict[str, Any]) -> str:
    rendering = narrative_policy["rendering"]
    features = list(graph_summary["node_features"].values())
    ranked = sorted(
        features,
        key=lambda item: (
            int(item["in_degree"]) + int(item["out_degree"]),
            float(item["weighted_inbound_amount"]) + float(item["weighted_outbound_amount"]),
        ),
        reverse=True,
    )
    if not ranked:
        return rendering["none_text"]
    rendered = []
    for item in ranked[:5]:
        rendered.append(
            f"{item['label']} "
            f"(in-degree {item['in_degree']}, out-degree {item['out_degree']}, "
            f"weighted inbound {item['weighted_inbound_amount']}, weighted outbound {item['weighted_outbound_amount']})"
        )
    return rendering["list_joiner"].join(rendered)


def format_node_reference(node_id: Any, graph_summary: dict[str, Any] | None) -> str:
    if not graph_summary:
        return str(node_id)
    node = graph_summary.get("node_features", {}).get(str(node_id))
    if not node:
        return str(node_id)
    label = str(node.get("label", node_id))
    return f"{label} ({node_id})"


def format_node_list(values: list[Any], graph_summary: dict[str, Any] | None, none_text: str) -> str:
    if not values:
        return none_text
    return ", ".join(format_node_reference(value, graph_summary) for value in values)


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


def build_key_evidence(
    matches: list[TypologyMatch],
    narrative_policy: dict[str, Any],
    graph_summary: dict[str, Any] | None = None,
) -> str:
    templates = narrative_policy["section_templates"]
    rendering = narrative_policy["rendering"]
    if not matches:
        return templates["key_evidence_fallback"]

    rendered = []
    for match in matches:
        evidence = rendering["list_joiner"].join(
            format_evidence(item, narrative_policy, graph_summary) for item in match.matched_evidence[:3]
        )
        rendered.append(templates["key_evidence_match"].format(typology_name=match.name, evidence=evidence))
    return rendering["section_joiner"].join(rendered)


def format_list(values: list[Any], *, none_text: str) -> str:
    if not values:
        return none_text
    return ", ".join(str(value) for value in values)
