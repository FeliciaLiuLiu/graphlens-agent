from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from afc_network_narrative.app.skill_loader import load_typology_skill
from afc_network_narrative.schemas.graph_extraction_schema import Edge, GraphExtraction


@dataclass
class MotifResult:
    fan_in: list[str] = field(default_factory=list)
    fan_out: list[str] = field(default_factory=list)
    inbound_hub: list[str] = field(default_factory=list)
    outbound_hub: list[str] = field(default_factory=list)
    pass_through_relay: list[str] = field(default_factory=list)
    cycle_or_circular_flow: list[list[str]] = field(default_factory=list)
    bipartite_many_to_many: list[dict[str, Any]] = field(default_factory=list)
    two_hop_paths: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fan_in": self.fan_in,
            "fan_out": self.fan_out,
            "inbound_hub": self.inbound_hub,
            "outbound_hub": self.outbound_hub,
            "pass_through_relay": self.pass_through_relay,
            "cycle_or_circular_flow": self.cycle_or_circular_flow,
            "bipartite_many_to_many": self.bipartite_many_to_many,
            "two_hop_paths": self.two_hop_paths,
        }


def detect_motifs(
    graph: GraphExtraction,
    in_degree: dict[str, int],
    out_degree: dict[str, int],
    *,
    policy: dict[str, Any] | None = None,
) -> MotifResult:
    thresholds = motif_thresholds(policy)
    fan_in_threshold = int(thresholds["fan_in"])
    fan_out_threshold = int(thresholds["fan_out"])
    inbound_hub_threshold = int(thresholds["inbound_hub"])
    outbound_hub_threshold = int(thresholds["outbound_hub"])
    pass_through_in_degree = int(thresholds["pass_through_in_degree"])
    pass_through_out_degree = int(thresholds["pass_through_out_degree"])
    max_cycle_length = int(thresholds["max_cycle_length"])
    bipartite_min_sources = int(thresholds["bipartite_min_sources"])
    bipartite_min_targets = int(thresholds["bipartite_min_targets"])
    bipartite_min_edges = int(thresholds["bipartite_min_edges"])

    fan_in = sorted([node_id for node_id, degree in in_degree.items() if degree >= fan_in_threshold])
    fan_out = sorted([node_id for node_id, degree in out_degree.items() if degree >= fan_out_threshold])
    inbound_hub = sorted([node_id for node_id, degree in in_degree.items() if degree >= inbound_hub_threshold])
    outbound_hub = sorted([node_id for node_id, degree in out_degree.items() if degree >= outbound_hub_threshold])
    pass_through = sorted(
        [
            node_id
            for node_id in set(in_degree) | set(out_degree)
            if in_degree.get(node_id, 0) >= pass_through_in_degree
            and out_degree.get(node_id, 0) >= pass_through_out_degree
        ]
    )
    return MotifResult(
        fan_in=fan_in,
        fan_out=fan_out,
        inbound_hub=inbound_hub,
        outbound_hub=outbound_hub,
        pass_through_relay=pass_through,
        cycle_or_circular_flow=find_cycles(graph, max_cycle_length=max_cycle_length),
        bipartite_many_to_many=find_bipartite_many_to_many(
            graph,
            min_sources=bipartite_min_sources,
            min_targets=bipartite_min_targets,
            min_edges=bipartite_min_edges,
        ),
        two_hop_paths=find_two_hop_paths(graph.edges),
    )


def find_two_hop_paths(edges: list[Edge]) -> list[dict[str, Any]]:
    outgoing: dict[str, list[tuple[int, Edge]]] = defaultdict(list)
    for index, edge in enumerate(edges):
        outgoing[edge.source].append((index, edge))

    paths = []
    for first_index, first_edge in enumerate(edges):
        for second_index, second_edge in outgoing.get(first_edge.target, []):
            if first_edge.source == second_edge.target:
                continue
            paths.append(
                {
                    "source": first_edge.source,
                    "via": first_edge.target,
                    "target": second_edge.target,
                    "edge_indices": [first_index, second_index],
                }
            )
    return paths


def find_cycles(graph: GraphExtraction, *, max_cycle_length: int) -> list[list[str]]:
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in graph.edges:
        adjacency[edge.source].append(edge.target)

    cycles: set[tuple[str, ...]] = set()
    for start in adjacency:
        stack = [(start, [start])]
        while stack:
            node, path = stack.pop()
            if len(path) > max_cycle_length:
                continue
            for next_node in adjacency.get(node, []):
                if next_node == start and len(path) >= 3:
                    cycles.add(canonical_cycle(path))
                elif next_node not in path:
                    stack.append((next_node, path + [next_node]))
    return [list(cycle) for cycle in sorted(cycles)]


def canonical_cycle(path: list[str]) -> tuple[str, ...]:
    rotations = [tuple(path[index:] + path[:index]) for index in range(len(path))]
    return min(rotations)


def find_bipartite_many_to_many(
    graph: GraphExtraction,
    *,
    min_sources: int,
    min_targets: int,
    min_edges: int,
) -> list[dict[str, Any]]:
    outgoing_targets: dict[str, set[str]] = defaultdict(set)
    incoming_sources: dict[str, set[str]] = defaultdict(set)
    for edge in graph.edges:
        outgoing_targets[edge.source].add(edge.target)
        incoming_sources[edge.target].add(edge.source)

    sources = {node for node, targets in outgoing_targets.items() if len(targets) >= min_sources}
    targets = {node for node, source_set in incoming_sources.items() if len(source_set) >= min_targets}
    if len(sources) >= min_sources and len(targets) >= min_targets:
        edge_count = sum(1 for edge in graph.edges if edge.source in sources and edge.target in targets)
        if edge_count >= min_edges:
            return [{"sources": sorted(sources), "targets": sorted(targets), "edge_count": edge_count}]
    return []


def motif_thresholds(policy: dict[str, Any] | None = None) -> dict[str, Any]:
    skill = policy or load_typology_skill().get("motif_detection_policy", {})
    thresholds = skill.get("thresholds", {}) if isinstance(skill, dict) else {}
    if not isinstance(thresholds, dict):
        raise ValueError("skills.afc_typology_mapping.typology_rules.motif_detection_policy.thresholds must be an object.")
    return thresholds
