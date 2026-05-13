from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from afc_network_narrative.app.skill_loader import load_typology_skill
from afc_network_narrative.features.graph_features import GraphFeatures, NodeFeature
from afc_network_narrative.schemas.graph_extraction_schema import GraphExtraction


@dataclass
class TypologyMatch:
    typology_id: str
    name: str
    confidence: float
    afc_interpretation: str
    caution: str
    investigation_boost: str
    matched_evidence: list[dict[str, Any]]
    limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "typology_id": self.typology_id,
            "name": self.name,
            "confidence": self.confidence,
            "afc_interpretation": self.afc_interpretation,
            "caution": self.caution,
            "investigation_boost": self.investigation_boost,
            "matched_evidence": self.matched_evidence,
            "limitations": self.limitations,
        }


class RuleEngine:
    def __init__(self, rules_path: str | Path | None = None) -> None:
        self.skill = load_typology_skill(rules_path)
        self.rules = self.skill.get("typologies", [])
        self.confidence_policy = self.skill.get("confidence_policy", {})
        self.context_limitations = self.skill.get("context_limitations", {})

    def match(self, graph: GraphExtraction, features: GraphFeatures) -> list[TypologyMatch]:
        matches: list[TypologyMatch] = []
        for rule in self.rules:
            matches.extend(self._match_rule(rule, graph, features))

        matches.sort(key=lambda match: match.confidence, reverse=True)
        return matches

    def _match_rule(self, rule: dict[str, Any], graph: GraphExtraction, features: GraphFeatures) -> list[TypologyMatch]:
        scope = str(rule["match_scope"])
        if scope == "node":
            return self._match_node_rule(rule, graph, features)
        if scope == "graph":
            return self._match_graph_rule(rule, graph, features)
        raise ValueError(f"Unsupported match_scope {scope!r} for typology rule {rule.get('id')}.")

    def _match_node_rule(
        self,
        rule: dict[str, Any],
        graph: GraphExtraction,
        features: GraphFeatures,
    ) -> list[TypologyMatch]:
        conditions = rule.get("conditions", {})
        motif_name = str(conditions.get("motif", "")).strip()
        node_ids = motif_values(features, motif_name)
        matches = []
        for node_id in node_ids:
            node_feature = features.node_features[node_id]
            if not node_conditions_met(node_feature, conditions):
                continue
            evidence = build_evidence_fields(rule.get("evidence_fields", []), features, node_feature=node_feature)
            matches.append(self._build_match(rule, evidence, features, graph, node_feature=node_feature))
        return matches

    def _match_graph_rule(
        self,
        rule: dict[str, Any],
        graph: GraphExtraction,
        features: GraphFeatures,
    ) -> list[TypologyMatch]:
        conditions = rule.get("conditions", {})
        if not graph_conditions_met(features, conditions):
            return []
        evidence = build_evidence_fields(rule.get("evidence_fields", []), features)
        return [self._build_match(rule, evidence, features, graph)]

    def _build_match(
        self,
        rule: dict[str, Any],
        evidence: list[dict[str, Any]],
        features: GraphFeatures,
        graph: GraphExtraction,
        node_feature: NodeFeature | None = None,
    ) -> TypologyMatch:
        confidence = compute_match_confidence(rule, features, self.confidence_policy, node_feature=node_feature)
        limitations = list(rule.get("limitations", [])) + missing_context_limitations(features, self.context_limitations)
        return TypologyMatch(
            typology_id=rule["id"],
            name=rule["name"],
            confidence=confidence,
            afc_interpretation=rule["afc_interpretation"],
            caution=rule["caution"],
            investigation_boost=rule["investigation_boost"],
            matched_evidence=[
                {
                    **item,
                    "source_registry_id": "internal_graph_features",
                    "rule_id": rule["id"],
                }
                for item in evidence
            ],
            limitations=dedupe(limitations),
        )


def build_evidence_fields(
    evidence_fields: list[str],
    features: GraphFeatures,
    node_feature: NodeFeature | None = None,
) -> list[dict[str, Any]]:
    evidence = []
    for field in evidence_fields:
        evidence_item = evidence_for_field(str(field), features, node_feature=node_feature)
        if evidence_item is not None:
            evidence.append(evidence_item)
    return evidence


def evidence_for_field(
    field: str,
    features: GraphFeatures,
    node_feature: NodeFeature | None = None,
) -> dict[str, Any] | None:
    if field == "in_degree":
        require_node_feature(field, node_feature)
        return {"metric": "in_degree", "node_id": node_feature.node_id, "value": node_feature.in_degree}
    if field == "out_degree":
        require_node_feature(field, node_feature)
        return {"metric": "out_degree", "node_id": node_feature.node_id, "value": node_feature.out_degree}
    if field == "weighted_inbound_amount":
        require_node_feature(field, node_feature)
        return {
            "metric": "weighted_inbound_amount",
            "node_id": node_feature.node_id,
            "value": round(node_feature.weighted_inbound_amount, 2),
        }
    if field == "weighted_outbound_amount":
        require_node_feature(field, node_feature)
        return {
            "metric": "weighted_outbound_amount",
            "node_id": node_feature.node_id,
            "value": round(node_feature.weighted_outbound_amount, 2),
        }
    if field == "weighted_flow_amount":
        require_node_feature(field, node_feature)
        return {
            "metric": "weighted_flow_amount",
            "node_id": node_feature.node_id,
            "value": round(node_feature.weighted_inbound_amount + node_feature.weighted_outbound_amount, 2),
        }
    if field == "repeated_amount_score":
        return {
            "metric": "repeated_amount_score",
            "value": features.repeated_amount_score,
            "amount_value": features.repeated_amount_value,
        }
    if field == "repeated_amount_value":
        return {"metric": "repeated_amount_value", "value": features.repeated_amount_value}
    if field == "fan_out_nodes":
        return {"metric": "fan_out_nodes", "value": features.motifs.fan_out}
    if field == "fan_in_nodes":
        return {"metric": "fan_in_nodes", "value": features.motifs.fan_in}
    if field == "cycle_count":
        return {"metric": "cycle_count", "value": len(features.motifs.cycle_or_circular_flow)}
    if field == "many_to_many_groups":
        return {"metric": "many_to_many_groups", "value": len(features.motifs.bipartite_many_to_many)}
    raise ValueError(f"Unsupported evidence field {field!r} in typology skill.")


def node_conditions_met(node_feature: NodeFeature, conditions: dict[str, Any]) -> bool:
    min_in_degree = conditions.get("min_in_degree")
    if min_in_degree is not None and node_feature.in_degree < int(min_in_degree):
        return False
    min_out_degree = conditions.get("min_out_degree")
    if min_out_degree is not None and node_feature.out_degree < int(min_out_degree):
        return False
    return True


def graph_conditions_met(features: GraphFeatures, conditions: dict[str, Any]) -> bool:
    required_motifs = conditions.get("required_motifs")
    if isinstance(required_motifs, dict):
        for motif_name, min_count in required_motifs.items():
            if len(motif_values(features, str(motif_name))) < int(min_count):
                return False

    motif_name = conditions.get("motif")
    if motif_name is not None:
        if "min_count" not in conditions:
            raise ValueError(f"Graph-scoped typology motif {motif_name!r} must declare conditions.min_count in YAML.")
        min_count = int(conditions["min_count"])
        if len(motif_values(features, str(motif_name))) < min_count:
            return False

    metric_name = conditions.get("metric")
    if metric_name is not None:
        metric_value = graph_metric_value(str(metric_name), features)
        min_value = conditions.get("min_value")
        if min_value is not None and metric_value < float(min_value):
            return False
        max_value = conditions.get("max_value")
        if max_value is not None and metric_value > float(max_value):
            return False

    return True


def motif_values(features: GraphFeatures, motif_name: str) -> list[Any]:
    try:
        value = getattr(features.motifs, motif_name)
    except AttributeError as exc:
        raise ValueError(f"Unsupported motif {motif_name!r} in typology skill.") from exc
    if not isinstance(value, list):
        raise ValueError(f"Motif {motif_name!r} is not list-like.")
    return value


def graph_metric_value(metric_name: str, features: GraphFeatures) -> float:
    if metric_name == "repeated_amount_score":
        return float(features.repeated_amount_score)
    if metric_name == "repeated_amount_value":
        return float(features.repeated_amount_value or 0.0)
    raise ValueError(f"Unsupported graph metric {metric_name!r} in typology skill.")


def compute_match_confidence(
    rule: dict[str, Any],
    features: GraphFeatures,
    confidence_policy: dict[str, Any],
    *,
    node_feature: NodeFeature | None = None,
) -> float:
    confidence = float(rule["base_confidence"])
    if node_feature is not None:
        degree_weight = float(confidence_policy["node_degree_weight"])
        degree_cap = float(confidence_policy["node_degree_cap"])
        confidence += min(degree_cap, (node_feature.in_degree + node_feature.out_degree) * degree_weight)
    repeated_amount_weight = float(confidence_policy["repeated_amount_weight"])
    repeated_amount_cap = float(confidence_policy["repeated_amount_cap"])
    confidence += min(repeated_amount_cap, features.repeated_amount_score * repeated_amount_weight)
    min_confidence = float(confidence_policy["min_confidence"])
    max_confidence = float(confidence_policy["max_confidence"])
    return round(max(min_confidence, min(max_confidence, confidence)), 3)


def missing_context_limitations(
    features: GraphFeatures,
    context_messages: dict[str, Any] | None = None,
) -> list[str]:
    messages = context_messages if context_messages is not None else load_typology_skill().get("context_limitations", {})
    if not isinstance(messages, dict):
        raise ValueError("skills.afc_typology_mapping.typology_rules.context_limitations must be an object.")
    return [str(text) for flag, text in messages.items() if features.missing_context_flags.get(flag)]


def require_node_feature(field: str, node_feature: NodeFeature | None) -> None:
    if node_feature is None:
        raise ValueError(f"Evidence field {field!r} requires a node-scoped typology match.")


def dedupe(items: list[str]) -> list[str]:
    seen = set()
    output = []
    for item in items:
        if item not in seen:
            output.append(item)
            seen.add(item)
    return output
