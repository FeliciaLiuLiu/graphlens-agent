from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from afc_network_narrative.harness.features.motif_detector import MotifResult, detect_motifs
from afc_network_narrative.harness.schemas.graph_extraction_schema import GraphExtraction


@dataclass
class NodeFeature:
    node_id: str
    label: str
    in_degree: int = 0
    out_degree: int = 0
    weighted_inbound_amount: float = 0.0
    weighted_outbound_amount: float = 0.0
    inbound_edges: list[int] = field(default_factory=list)
    outbound_edges: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "label": self.label,
            "in_degree": self.in_degree,
            "out_degree": self.out_degree,
            "weighted_inbound_amount": round(self.weighted_inbound_amount, 2),
            "weighted_outbound_amount": round(self.weighted_outbound_amount, 2),
            "inbound_edges": self.inbound_edges,
            "outbound_edges": self.outbound_edges,
        }


@dataclass
class GraphFeatures:
    node_features: dict[str, NodeFeature]
    repeated_amount_score: float
    repeated_amount_value: float | None
    motifs: MotifResult
    missing_context_flags: dict[str, bool]
    average_node_confidence: float
    average_direction_confidence: float
    average_amount_confidence: float
    overall_extraction_confidence: float
    distinct_counterparty_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_features": {node_id: feature.to_dict() for node_id, feature in self.node_features.items()},
            "repeated_amount_score": self.repeated_amount_score,
            "repeated_amount_value": self.repeated_amount_value,
            "motifs": self.motifs.to_dict(),
            "missing_context_flags": self.missing_context_flags,
            "average_node_confidence": self.average_node_confidence,
            "average_direction_confidence": self.average_direction_confidence,
            "average_amount_confidence": self.average_amount_confidence,
            "overall_extraction_confidence": self.overall_extraction_confidence,
            "distinct_counterparty_count": self.distinct_counterparty_count,
        }


def build_graph_features(graph: GraphExtraction) -> GraphFeatures:
    node_features = {
        node.id: NodeFeature(node_id=node.id, label=node.label)
        for node in graph.nodes
    }
    for index, edge in enumerate(graph.edges):
        amount = edge.amount_value or 0.0
        amount_weight = edge.amount_confidence if edge.amount_value is not None else 0.0

        source = node_features[edge.source]
        target = node_features[edge.target]
        source.out_degree += 1
        source.weighted_outbound_amount += amount * amount_weight
        source.outbound_edges.append(index)
        target.in_degree += 1
        target.weighted_inbound_amount += amount * amount_weight
        target.inbound_edges.append(index)

    in_degree = {node_id: feature.in_degree for node_id, feature in node_features.items()}
    out_degree = {node_id: feature.out_degree for node_id, feature in node_features.items()}
    motifs = detect_motifs(graph, in_degree, out_degree)
    repeated_amount_score, repeated_amount_value = compute_repeated_amount_score(graph)

    average_node_confidence = average([node.confidence for node in graph.nodes])
    average_direction_confidence = average([edge.direction_confidence for edge in graph.edges])
    average_amount_confidence = average([edge.amount_confidence for edge in graph.edges if edge.amount_value is not None])
    overall_extraction_confidence = average(
        [
            value
            for value in [average_node_confidence, average_direction_confidence, average_amount_confidence]
            if value > 0
        ]
    )

    return GraphFeatures(
        node_features=node_features,
        repeated_amount_score=repeated_amount_score,
        repeated_amount_value=repeated_amount_value,
        motifs=motifs,
        missing_context_flags=build_missing_context_flags(graph),
        average_node_confidence=average_node_confidence,
        average_direction_confidence=average_direction_confidence,
        average_amount_confidence=average_amount_confidence,
        overall_extraction_confidence=overall_extraction_confidence,
        distinct_counterparty_count=len(graph.nodes),
    )


def compute_repeated_amount_score(graph: GraphExtraction) -> tuple[float, float | None]:
    amounts = [round(edge.amount_value, 2) for edge in graph.edges if edge.amount_value is not None]
    if len(amounts) < 2:
        return 0.0, None
    counts = Counter(amounts)
    value, count = counts.most_common(1)[0]
    if count < 2:
        return 0.0, None
    return round(count / len(amounts), 3), value


def build_missing_context_flags(graph: GraphExtraction) -> dict[str, bool]:
    provided = graph.visual_signals.get("context_available", {})
    if not isinstance(provided, dict):
        provided = {}
    return {
        "timestamps_absent": not bool(provided.get("timestamps")),
        "customer_profile_absent": not bool(provided.get("customer_profile")),
        "kyc_device_ip_absent": not bool(provided.get("kyc_device_ip")),
        "geography_absent": not bool(provided.get("geography")),
        "channel_absent": not bool(provided.get("channel")),
        "customer_baseline_absent": not bool(provided.get("customer_baseline")),
    }


def average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 3)
