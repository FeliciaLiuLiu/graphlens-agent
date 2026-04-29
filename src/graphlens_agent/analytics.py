from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple, Union

import networkx as nx

from graphlens_agent.schema import GraphDocument
from graphlens_agent.validator import validate_graph_document


GraphInput = Union[GraphDocument, Mapping[str, Any]]


def build_networkx_graph(document: GraphInput) -> Union[nx.MultiDiGraph, nx.MultiGraph]:
    graph_document = _ensure_document(document)
    graph: Union[nx.MultiDiGraph, nx.MultiGraph]
    graph = nx.MultiDiGraph() if graph_document.metadata.directed else nx.MultiGraph()

    for node in graph_document.nodes:
        graph.add_node(
            node.id,
            label=node.label,
            type=node.type,
            confidence=node.confidence,
            position=node.position.to_dict() if node.position else None,
            attributes=node.attributes,
        )

    for edge in graph_document.edges:
        graph.add_edge(
            edge.source,
            edge.target,
            key=edge.id,
            id=edge.id,
            label=edge.label,
            amount=edge.amount,
            currency=edge.currency,
            directed=edge.directed if edge.directed is not None else graph_document.metadata.directed,
            confidence=edge.confidence,
            attributes=edge.attributes,
        )

    return graph


def analyze_graph(document: GraphInput) -> Dict[str, Any]:
    """Run deterministic graph analytics for a validated GraphLens graph document."""

    graph_document = _ensure_document(document)
    graph = build_networkx_graph(graph_document)
    node_metrics = _compute_node_metrics(graph)
    central_node = _central_node(node_metrics)
    repeated_amounts = _repeated_amount_pattern(graph_document)
    motif = _detect_motif(graph, node_metrics)
    collector = _detect_collector_behavior(graph, node_metrics)

    return {
        "schema_version": graph_document.metadata.schema_version,
        "summary": {
            "node_count": graph.number_of_nodes(),
            "edge_count": graph.number_of_edges(),
            "directed": graph_document.metadata.directed,
            "central_node": central_node,
            "graph_motif": motif["motif"],
            "motif_confidence": motif["confidence"],
            "collector_node": collector["node_id"],
            "has_collector_behavior": collector["detected"],
        },
        "nodes": node_metrics,
        "amount_patterns": repeated_amounts,
        "motifs": motif,
        "collector_behavior": collector,
        "warnings": graph_document.warnings,
        "evidence": _build_evidence(graph_document, node_metrics, repeated_amounts, motif, collector),
    }


def _compute_node_metrics(graph: Union[nx.MultiDiGraph, nx.MultiGraph]) -> Dict[str, Dict[str, Any]]:
    metrics: Dict[str, Dict[str, Any]] = {}
    directed = graph.is_directed()
    for node_id, attrs in graph.nodes(data=True):
        if directed:
            in_degree = int(graph.in_degree(node_id))
            out_degree = int(graph.out_degree(node_id))
            inbound_amount = _sum_edge_amounts(data for _, _, _, data in graph.in_edges(node_id, keys=True, data=True))
            outbound_amount = _sum_edge_amounts(data for _, _, _, data in graph.out_edges(node_id, keys=True, data=True))
        else:
            in_degree = int(graph.degree(node_id))
            out_degree = int(graph.degree(node_id))
            inbound_amount = _sum_edge_amounts(data for _, _, _, data in graph.edges(node_id, keys=True, data=True))
            outbound_amount = inbound_amount

        metrics[node_id] = {
            "id": node_id,
            "label": attrs.get("label"),
            "type": attrs.get("type"),
            "in_degree": in_degree,
            "out_degree": out_degree,
            "degree": in_degree + out_degree if directed else in_degree,
            "total_inbound_amount": inbound_amount,
            "total_outbound_amount": outbound_amount,
        }
    return metrics


def _central_node(node_metrics: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not node_metrics:
        return None

    node_id, metrics = max(
        node_metrics.items(),
        key=lambda item: (
            item[1]["degree"],
            item[1]["in_degree"],
            item[1]["total_inbound_amount"],
            item[0],
        ),
    )
    return {
        "id": node_id,
        "label": metrics["label"],
        "degree": metrics["degree"],
        "in_degree": metrics["in_degree"],
        "out_degree": metrics["out_degree"],
    }


def _repeated_amount_pattern(document: GraphDocument) -> Dict[str, Any]:
    amounts = [_normalize_amount(edge.amount) for edge in document.edges if edge.amount is not None]
    amount_counts = Counter(amounts)
    repeated = {
        amount: count
        for amount, count in sorted(amount_counts.items(), key=lambda item: (-item[1], item[0]))
        if count >= 2
    }
    most_common_amount: Optional[str] = None
    most_common_count = 0
    if amount_counts:
        most_common_amount, most_common_count = amount_counts.most_common(1)[0]

    return {
        "has_repeated_amounts": bool(repeated),
        "repeated_amounts": repeated,
        "most_common_amount": most_common_amount,
        "most_common_count": most_common_count,
        "amount_edge_count": len(amounts),
    }


def _detect_motif(
    graph: Union[nx.MultiDiGraph, nx.MultiGraph],
    node_metrics: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    directed = graph.is_directed()
    simple_graph = _as_simple_directed_graph(graph)

    first_cycle = next(iter(nx.simple_cycles(simple_graph)), None) if directed else None
    if first_cycle:
        return {
            "motif": "cycle",
            "confidence": 1.0,
            "evidence": [f"graph contains directed cycle {' -> '.join(first_cycle)}"],
        }

    collector = _node_with_max_metric(node_metrics, "in_degree")
    distributor = _node_with_max_metric(node_metrics, "out_degree")

    if collector and collector[1]["in_degree"] >= 2 and collector[1]["out_degree"] <= 1:
        return {
            "motif": "fan_in_aggregation",
            "confidence": 0.95,
            "evidence": [
                f"{collector[0]} has {collector[1]['in_degree']} inbound edges",
                f"{collector[0]} has {collector[1]['out_degree']} outbound edges",
            ],
        }

    if distributor and distributor[1]["out_degree"] >= 2 and distributor[1]["in_degree"] <= 1:
        return {
            "motif": "fan_out_distribution",
            "confidence": 0.95,
            "evidence": [
                f"{distributor[0]} has {distributor[1]['out_degree']} outbound edges",
                f"{distributor[0]} has {distributor[1]['in_degree']} inbound edges",
            ],
        }

    hub = _node_with_max_metric(node_metrics, "degree")
    if hub and graph.number_of_edges() >= 3 and hub[1]["degree"] >= graph.number_of_edges():
        return {
            "motif": "hub_and_spoke",
            "confidence": 0.85,
            "evidence": [f"{hub[0]} touches {hub[1]['degree']} edge endpoints"],
        }

    if _is_chain(graph, simple_graph):
        return {
            "motif": "chain",
            "confidence": 0.9,
            "evidence": ["graph has one path-like connected component"],
        }

    return {
        "motif": "unknown",
        "confidence": 0.0,
        "evidence": ["no supported motif matched the graph structure"],
    }


def _detect_collector_behavior(
    graph: Union[nx.MultiDiGraph, nx.MultiGraph],
    node_metrics: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    if not graph.is_directed():
        return {
            "detected": False,
            "node_id": None,
            "inbound_sources": [],
            "total_inbound_amount": 0.0,
            "evidence": ["collector behavior requires directed edges"],
        }

    candidate = _node_with_max_metric(node_metrics, "in_degree")
    if not candidate:
        return {
            "detected": False,
            "node_id": None,
            "inbound_sources": [],
            "total_inbound_amount": 0.0,
            "evidence": [],
        }

    node_id, metrics = candidate
    sources = sorted({source for source, _target, _key in graph.in_edges(node_id, keys=True)})
    detected = metrics["in_degree"] >= 2 and len(sources) >= 2
    return {
        "detected": detected,
        "node_id": node_id if detected else None,
        "inbound_sources": sources if detected else [],
        "total_inbound_amount": metrics["total_inbound_amount"] if detected else 0.0,
        "evidence": [
            f"{node_id} receives {metrics['in_degree']} inbound edges",
            f"{node_id} receives inbound edges from {len(sources)} distinct sources",
        ],
    }


def _build_evidence(
    document: GraphDocument,
    node_metrics: Dict[str, Dict[str, Any]],
    repeated_amounts: Dict[str, Any],
    motif: Dict[str, Any],
    collector: Dict[str, Any],
) -> List[str]:
    evidence = [
        f"validated graph has {len(document.nodes)} nodes and {len(document.edges)} edges",
        f"detected graph motif: {motif['motif']}",
    ]

    central = _central_node(node_metrics)
    if central:
        evidence.append(
            f"central node {central['id']} has in-degree {central['in_degree']} and out-degree {central['out_degree']}"
        )
    if collector["detected"]:
        evidence.append(
            f"collector node {collector['node_id']} receives {collector['total_inbound_amount']} total inbound amount"
        )
    if repeated_amounts["has_repeated_amounts"]:
        evidence.append(f"repeated edge amounts found: {repeated_amounts['repeated_amounts']}")
    return evidence


def _is_chain(graph: Union[nx.MultiDiGraph, nx.MultiGraph], simple_graph: nx.DiGraph) -> bool:
    if graph.number_of_nodes() < 2 or graph.number_of_edges() != graph.number_of_nodes() - 1:
        return False

    undirected = simple_graph.to_undirected()
    if not nx.is_connected(undirected):
        return False

    if graph.is_directed():
        sources = [node for node in simple_graph.nodes if simple_graph.in_degree(node) == 0 and simple_graph.out_degree(node) == 1]
        sinks = [node for node in simple_graph.nodes if simple_graph.in_degree(node) == 1 and simple_graph.out_degree(node) == 0]
        middle = [
            node
            for node in simple_graph.nodes
            if simple_graph.in_degree(node) == 1 and simple_graph.out_degree(node) == 1
        ]
        return len(sources) == 1 and len(sinks) == 1 and len(middle) == graph.number_of_nodes() - 2

    degrees = [degree for _node, degree in graph.degree()]
    return degrees.count(1) == 2 and all(degree <= 2 for degree in degrees)


def _as_simple_directed_graph(graph: Union[nx.MultiDiGraph, nx.MultiGraph]) -> nx.DiGraph:
    simple = nx.DiGraph()
    simple.add_nodes_from(graph.nodes())
    if graph.is_directed():
        simple.add_edges_from((source, target) for source, target, _key in graph.edges(keys=True))
    else:
        for source, target, _key in graph.edges(keys=True):
            simple.add_edge(source, target)
            simple.add_edge(target, source)
    return simple


def _node_with_max_metric(
    node_metrics: Dict[str, Dict[str, Any]],
    metric_name: str,
) -> Optional[Tuple[str, Dict[str, Any]]]:
    if not node_metrics:
        return None
    return max(
        node_metrics.items(),
        key=lambda item: (
            item[1][metric_name],
            item[1]["degree"],
            item[1]["total_inbound_amount"],
            item[0],
        ),
    )


def _sum_edge_amounts(edge_data: Iterable[Dict[str, Any]]) -> float:
    return float(sum(data.get("amount") or 0 for data in edge_data))


def _normalize_amount(amount: float) -> str:
    decimal = Decimal(str(amount)).normalize()
    return format(decimal, "f")


def _ensure_document(document: GraphInput) -> GraphDocument:
    if isinstance(document, GraphDocument):
        return document
    return validate_graph_document(document)
