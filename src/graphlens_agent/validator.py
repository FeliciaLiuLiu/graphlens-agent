from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set

from graphlens_agent.schema import (
    SCHEMA_VERSION,
    GraphDocument,
    GraphEdge,
    GraphMetadata,
    GraphNode,
    Position,
)


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    path: str
    message: str


class GraphValidationError(ValueError):
    def __init__(self, issues: Sequence[ValidationIssue]) -> None:
        self.issues = list(issues)
        message = "; ".join(f"{issue.path}: {issue.message}" for issue in self.issues)
        super().__init__(message)


def collect_validation_issues(payload: Any) -> List[ValidationIssue]:
    """Return validation errors and extraction-quality warnings for graph JSON."""

    issues: List[ValidationIssue] = []
    if not isinstance(payload, Mapping):
        return [_error("$", "graph document must be a JSON object")]

    _validate_top_level(payload, issues)
    if any(issue.severity == "error" for issue in issues):
        return issues

    node_ids = _collect_node_ids(payload.get("nodes", []), issues)
    _validate_edges(payload.get("edges", []), node_ids, issues)
    _validate_extraction_quality(payload, issues)
    return issues


def validate_graph_document(payload: Any) -> GraphDocument:
    """Validate and normalize a GraphLens graph document.

    Raises:
        GraphValidationError: when structural schema errors are present.
    """

    issues = collect_validation_issues(payload)
    errors = [issue for issue in issues if issue.severity == "error"]
    if errors:
        raise GraphValidationError(errors)

    assert isinstance(payload, Mapping)
    metadata = _build_metadata(_as_mapping(payload.get("metadata", {})))
    nodes = [_build_node(node) for node in payload.get("nodes", [])]
    edges = [_build_edge(edge) for edge in payload.get("edges", [])]
    warnings = [str(item) for item in payload.get("warnings", [])]
    warnings.extend(issue.message for issue in issues if issue.severity == "warning")
    return GraphDocument(metadata=metadata, nodes=nodes, edges=edges, warnings=warnings)


def _validate_top_level(payload: Mapping[str, Any], issues: List[ValidationIssue]) -> None:
    allowed = {"metadata", "nodes", "edges", "warnings"}
    _reject_unknown_keys(payload, allowed, "$", issues)

    metadata = payload.get("metadata")
    if "metadata" not in payload:
        issues.append(_error("$.metadata", "metadata is required"))
    elif not isinstance(metadata, Mapping):
        issues.append(_error("$.metadata", "metadata must be an object when present"))
    else:
        _validate_metadata(metadata, issues)

    nodes = payload.get("nodes")
    if not isinstance(nodes, list):
        issues.append(_error("$.nodes", "nodes must be an array"))
    else:
        _validate_nodes(nodes, issues)

    edges = payload.get("edges")
    if not isinstance(edges, list):
        issues.append(_error("$.edges", "edges must be an array"))

    warnings = payload.get("warnings", [])
    if not isinstance(warnings, list) or not all(isinstance(item, str) for item in warnings):
        issues.append(_error("$.warnings", "warnings must be an array of strings when present"))


def _validate_metadata(metadata: Mapping[str, Any], issues: List[ValidationIssue]) -> None:
    allowed = {
        "schema_version",
        "source_type",
        "source_name",
        "directed",
        "extraction_method",
        "extraction_confidence",
        "created_at",
        "domain",
    }
    _reject_unknown_keys(metadata, allowed, "$.metadata", issues)
    _optional_string(metadata, "schema_version", "$.metadata.schema_version", issues)
    _optional_string(metadata, "source_type", "$.metadata.source_type", issues)
    _optional_string(metadata, "source_name", "$.metadata.source_name", issues)
    _optional_string(metadata, "extraction_method", "$.metadata.extraction_method", issues)
    _optional_string(metadata, "created_at", "$.metadata.created_at", issues)
    _optional_string(metadata, "domain", "$.metadata.domain", issues)
    if "directed" in metadata and not isinstance(metadata["directed"], bool):
        issues.append(_error("$.metadata.directed", "directed must be a boolean"))
    if "extraction_confidence" in metadata:
        _confidence(metadata["extraction_confidence"], "$.metadata.extraction_confidence", issues)

    version = metadata.get("schema_version", SCHEMA_VERSION)
    if version != SCHEMA_VERSION:
        issues.append(_error("$.metadata.schema_version", f"expected schema version {SCHEMA_VERSION!r}"))


def _validate_nodes(nodes: Sequence[Any], issues: List[ValidationIssue]) -> None:
    seen: Set[str] = set()
    for index, node in enumerate(nodes):
        path = f"$.nodes[{index}]"
        if not isinstance(node, Mapping):
            issues.append(_error(path, "node must be an object"))
            continue

        allowed = {"id", "label", "type", "confidence", "position", "attributes"}
        _reject_unknown_keys(node, allowed, path, issues)
        node_id = _required_string(node, "id", f"{path}.id", issues)
        _required_string(node, "label", f"{path}.label", issues)
        _optional_string(node, "type", f"{path}.type", issues)
        if "confidence" in node:
            _confidence(node["confidence"], f"{path}.confidence", issues)
        if "attributes" in node and not isinstance(node["attributes"], Mapping):
            issues.append(_error(f"{path}.attributes", "attributes must be an object"))
        if "position" in node:
            _validate_position(node["position"], f"{path}.position", issues)
        if node_id:
            if node_id in seen:
                issues.append(_error(f"{path}.id", f"duplicate node id {node_id!r}"))
            seen.add(node_id)


def _collect_node_ids(nodes: Sequence[Any], issues: List[ValidationIssue]) -> Set[str]:
    ids: Set[str] = set()
    for node in nodes:
        if isinstance(node, Mapping) and isinstance(node.get("id"), str) and node["id"].strip():
            ids.add(node["id"])
    if not ids:
        issues.append(_warning("$.nodes", "graph contains no valid nodes"))
    return ids


def _validate_edges(edges: Sequence[Any], node_ids: Set[str], issues: List[ValidationIssue]) -> None:
    seen: Set[str] = set()
    for index, edge in enumerate(edges):
        path = f"$.edges[{index}]"
        if not isinstance(edge, Mapping):
            issues.append(_error(path, "edge must be an object"))
            continue

        allowed = {
            "id",
            "source",
            "target",
            "label",
            "amount",
            "currency",
            "directed",
            "confidence",
            "attributes",
        }
        _reject_unknown_keys(edge, allowed, path, issues)
        edge_id = _required_string(edge, "id", f"{path}.id", issues)
        source = _required_string(edge, "source", f"{path}.source", issues)
        target = _required_string(edge, "target", f"{path}.target", issues)
        _optional_string(edge, "label", f"{path}.label", issues)
        _optional_string(edge, "currency", f"{path}.currency", issues)
        if "amount" in edge and not _is_number(edge["amount"]):
            issues.append(_error(f"{path}.amount", "amount must be a number"))
        if "directed" in edge and not isinstance(edge["directed"], bool):
            issues.append(_error(f"{path}.directed", "directed must be a boolean"))
        if "confidence" in edge:
            _confidence(edge["confidence"], f"{path}.confidence", issues)
        if "attributes" in edge and not isinstance(edge["attributes"], Mapping):
            issues.append(_error(f"{path}.attributes", "attributes must be an object"))

        if edge_id:
            if edge_id in seen:
                issues.append(_error(f"{path}.id", f"duplicate edge id {edge_id!r}"))
            seen.add(edge_id)
        if source and source not in node_ids:
            issues.append(_error(f"{path}.source", f"unknown source node {source!r}"))
        if target and target not in node_ids:
            issues.append(_error(f"{path}.target", f"unknown target node {target!r}"))

    if not edges:
        issues.append(_warning("$.edges", "graph contains no edges"))


def _validate_position(position: Any, path: str, issues: List[ValidationIssue]) -> None:
    if not isinstance(position, Mapping):
        issues.append(_error(path, "position must be an object"))
        return

    allowed = {"x", "y", "confidence"}
    _reject_unknown_keys(position, allowed, path, issues)
    if "x" not in position or not _is_number(position.get("x")):
        issues.append(_error(f"{path}.x", "x must be a number"))
    if "y" not in position or not _is_number(position.get("y")):
        issues.append(_error(f"{path}.y", "y must be a number"))
    if "confidence" in position:
        _confidence(position["confidence"], f"{path}.confidence", issues)


def _validate_extraction_quality(payload: Mapping[str, Any], issues: List[ValidationIssue]) -> None:
    metadata = _as_mapping(payload.get("metadata", {}))
    confidence = metadata.get("extraction_confidence")
    if _is_number(confidence) and confidence < 0.8:
        issues.append(_warning("$.metadata.extraction_confidence", "overall extraction confidence is below 0.8"))

    for index, node in enumerate(payload.get("nodes", [])):
        if isinstance(node, Mapping) and _is_number(node.get("confidence")) and node["confidence"] < 0.7:
            issues.append(_warning(f"$.nodes[{index}].confidence", f"node {node.get('id')!r} has low confidence"))
        position = node.get("position") if isinstance(node, Mapping) else None
        if isinstance(position, Mapping) and _is_number(position.get("confidence")) and position["confidence"] < 0.7:
            issues.append(_warning(f"$.nodes[{index}].position.confidence", f"node {node.get('id')!r} position has low confidence"))

    for index, edge in enumerate(payload.get("edges", [])):
        if isinstance(edge, Mapping) and _is_number(edge.get("confidence")) and edge["confidence"] < 0.7:
            issues.append(_warning(f"$.edges[{index}].confidence", f"edge {edge.get('id')!r} has low confidence"))


def _build_metadata(metadata: Mapping[str, Any]) -> GraphMetadata:
    return GraphMetadata(
        schema_version=str(metadata.get("schema_version", SCHEMA_VERSION)),
        source_type=str(metadata.get("source_type", "screenshot")),
        directed=bool(metadata.get("directed", True)),
        source_name=_optional_str_value(metadata.get("source_name")),
        extraction_method=_optional_str_value(metadata.get("extraction_method")),
        extraction_confidence=float(metadata.get("extraction_confidence", 1.0)),
        created_at=_optional_str_value(metadata.get("created_at")),
        domain=_optional_str_value(metadata.get("domain")),
    )


def _build_node(node: Mapping[str, Any]) -> GraphNode:
    position = None
    if isinstance(node.get("position"), Mapping):
        raw_position = node["position"]
        position = Position(
            x=float(raw_position["x"]),
            y=float(raw_position["y"]),
            confidence=float(raw_position.get("confidence", 1.0)),
        )
    return GraphNode(
        id=str(node["id"]),
        label=str(node["label"]),
        type=str(node.get("type", "entity")),
        confidence=float(node.get("confidence", 1.0)),
        position=position,
        attributes=dict(node.get("attributes", {})),
    )


def _build_edge(edge: Mapping[str, Any]) -> GraphEdge:
    directed: Optional[bool]
    directed = edge.get("directed") if "directed" in edge else None
    return GraphEdge(
        id=str(edge["id"]),
        source=str(edge["source"]),
        target=str(edge["target"]),
        label=_optional_str_value(edge.get("label")),
        amount=float(edge["amount"]) if "amount" in edge else None,
        currency=_optional_str_value(edge.get("currency")),
        directed=directed,
        confidence=float(edge.get("confidence", 1.0)),
        attributes=dict(edge.get("attributes", {})),
    )


def _reject_unknown_keys(
    payload: Mapping[str, Any],
    allowed: Iterable[str],
    path: str,
    issues: List[ValidationIssue],
) -> None:
    allowed_set = set(allowed)
    for key in payload.keys():
        if key not in allowed_set:
            issues.append(_error(f"{path}.{key}", "unknown field"))


def _required_string(
    payload: Mapping[str, Any],
    key: str,
    path: str,
    issues: List[ValidationIssue],
) -> Optional[str]:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        issues.append(_error(path, f"{key} must be a non-empty string"))
        return None
    return value


def _optional_string(
    payload: Mapping[str, Any],
    key: str,
    path: str,
    issues: List[ValidationIssue],
) -> None:
    if key in payload and not isinstance(payload[key], str):
        issues.append(_error(path, f"{key} must be a string"))


def _confidence(value: Any, path: str, issues: List[ValidationIssue]) -> None:
    if not _is_number(value):
        issues.append(_error(path, "confidence must be a number between 0 and 1"))
        return
    if value < 0 or value > 1:
        issues.append(_error(path, "confidence must be between 0 and 1"))


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _optional_str_value(value: Any) -> Optional[str]:
    return str(value) if value is not None else None


def _error(path: str, message: str) -> ValidationIssue:
    return ValidationIssue(severity="error", path=path, message=message)


def _warning(path: str, message: str) -> ValidationIssue:
    return ValidationIssue(severity="warning", path=path, message=message)
