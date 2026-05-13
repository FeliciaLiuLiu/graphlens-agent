from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from afc_network_narrative.app.skill_loader import load_typology_skill
from afc_network_narrative.features.amount_parser import parse_amount_with_currency, normalize_currency


class GraphValidationError(ValueError):
    """Raised when extracted graph JSON violates the internal contract."""


ALLOWED_GRAPH_FIELDS = {
    "case_id",
    "nodes",
    "edges",
    "visual_signals",
    "extraction_uncertainties",
}
ALLOWED_NODE_FIELDS = {
    "id",
    "label",
    "visible_color",
    "role_hint_from_label",
    "confidence",
}
ALLOWED_EDGE_FIELDS = {
    "source",
    "target",
    "amount_text",
    "amount_value",
    "currency",
    "visible_color",
    "direction_confidence",
    "amount_confidence",
}


@dataclass
class Node:
    id: str
    label: str
    visible_color: str | None = None
    role_hint_from_label: str | None = None
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "visible_color": self.visible_color,
            "role_hint_from_label": self.role_hint_from_label,
            "confidence": self.confidence,
        }


@dataclass
class Edge:
    source: str
    target: str
    amount_text: str | None = None
    amount_value: float | None = None
    currency: str | None = None
    visible_color: str | None = None
    direction_confidence: float = 0.0
    amount_confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "amount_text": self.amount_text,
            "amount_value": self.amount_value,
            "currency": self.currency,
            "visible_color": self.visible_color,
            "direction_confidence": self.direction_confidence,
            "amount_confidence": self.amount_confidence,
        }


@dataclass
class GraphExtraction:
    nodes: list[Node]
    edges: list[Edge]
    visual_signals: dict[str, Any] = field(default_factory=dict)
    extraction_uncertainties: list[str] = field(default_factory=list)
    case_id: str = "local_case"

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "visual_signals": dict(self.visual_signals),
            "extraction_uncertainties": list(self.extraction_uncertainties),
        }

    def node_by_id(self) -> dict[str, Node]:
        return {node.id: node for node in self.nodes}


def validate_graph_extraction(payload: GraphExtraction | dict[str, Any] | str) -> GraphExtraction:
    if isinstance(payload, GraphExtraction):
        return payload
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise GraphValidationError(f"Invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise GraphValidationError("Graph extraction must be a JSON object.")

    reject_unknown_fields(payload, ALLOWED_GRAPH_FIELDS, "graph")
    require_fields(payload, ["nodes", "edges", "visual_signals", "extraction_uncertainties"], "graph")
    if not isinstance(payload["nodes"], list):
        raise GraphValidationError("graph.nodes must be a list.")
    if not isinstance(payload["edges"], list):
        raise GraphValidationError("graph.edges must be a list.")

    nodes = [_validate_node(raw, index) for index, raw in enumerate(payload["nodes"])]
    node_ids = [node.id for node in nodes]
    if len(node_ids) != len(set(node_ids)):
        raise GraphValidationError("Duplicate node id detected.")

    edges = [_validate_edge(raw, index, set(node_ids)) for index, raw in enumerate(payload["edges"])]
    visual_signals = payload.get("visual_signals") or {}
    if not isinstance(visual_signals, dict):
        raise GraphValidationError("graph.visual_signals must be an object when provided.")
    uncertainties = payload.get("extraction_uncertainties") or []
    if not isinstance(uncertainties, list):
        raise GraphValidationError("graph.extraction_uncertainties must be a list when provided.")

    return GraphExtraction(
        case_id=str(payload.get("case_id") or "local_case"),
        nodes=nodes,
        edges=edges,
        visual_signals=visual_signals,
        extraction_uncertainties=[str(item) for item in uncertainties],
    )


def _validate_node(raw: Any, index: int) -> Node:
    if not isinstance(raw, dict):
        raise GraphValidationError(f"nodes[{index}] must be an object.")
    reject_unknown_fields(raw, ALLOWED_NODE_FIELDS, f"nodes[{index}]")
    require_fields(raw, ["id", "label", "confidence"], f"nodes[{index}]")

    node_id = str(raw["id"]).strip()
    label = str(raw["label"]).strip()
    if not node_id:
        raise GraphValidationError(f"nodes[{index}].id cannot be empty.")
    if not label:
        raise GraphValidationError(f"nodes[{index}].label cannot be empty.")

    return Node(
        id=node_id,
        label=label,
        visible_color=optional_str(raw.get("visible_color")),
        role_hint_from_label=optional_str(raw.get("role_hint_from_label")) or infer_role_hint(label),
        confidence=parse_confidence(raw.get("confidence"), f"nodes[{index}].confidence"),
    )


def _validate_edge(raw: Any, index: int, node_ids: set[str]) -> Edge:
    if not isinstance(raw, dict):
        raise GraphValidationError(f"edges[{index}] must be an object.")
    reject_unknown_fields(raw, ALLOWED_EDGE_FIELDS, f"edges[{index}]")
    require_fields(raw, ["source", "target", "direction_confidence", "amount_confidence"], f"edges[{index}]")

    source = str(raw["source"]).strip()
    target = str(raw["target"]).strip()
    if source not in node_ids:
        raise GraphValidationError(f"edges[{index}].source references missing node '{source}'.")
    if target not in node_ids:
        raise GraphValidationError(f"edges[{index}].target references missing node '{target}'.")

    amount_text = optional_str(raw.get("amount_text"))
    amount_value = optional_float(raw.get("amount_value"), f"edges[{index}].amount_value")
    currency = normalize_currency(optional_str(raw.get("currency")))
    parsed_value, parsed_currency = parse_amount_with_currency(amount_text)
    if parsed_value is None:
        if amount_value is not None:
            raise GraphValidationError(
                f"edges[{index}].amount_value must be null when amount_text is absent or invalid."
            )
    elif amount_value is None:
        amount_value = parsed_value
    elif abs(amount_value - parsed_value) > max(1.0, abs(parsed_value) * 0.01):
        raise GraphValidationError(
            f"edges[{index}].amount_value does not match visible amount_text {amount_text!r}."
        )

    return Edge(
        source=source,
        target=target,
        amount_text=amount_text,
        amount_value=amount_value,
        currency=currency or parsed_currency,
        visible_color=optional_str(raw.get("visible_color")),
        direction_confidence=parse_confidence(raw.get("direction_confidence"), f"edges[{index}].direction_confidence"),
        amount_confidence=parse_confidence(raw.get("amount_confidence"), f"edges[{index}].amount_confidence"),
    )


def reject_unknown_fields(raw: dict[str, Any], allowed: set[str], location: str) -> None:
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise GraphValidationError(f"{location} contains unsupported fields: {', '.join(unknown)}")


def require_fields(raw: dict[str, Any], required: list[str], location: str) -> None:
    missing = [field for field in required if field not in raw]
    if missing:
        raise GraphValidationError(f"{location} missing required fields: {', '.join(missing)}")


def parse_confidence(value: Any, location: str) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError) as exc:
        raise GraphValidationError(f"{location} must be a number between 0 and 1.") from exc
    if not 0.0 <= confidence <= 1.0:
        raise GraphValidationError(f"{location} must be between 0 and 1.")
    return confidence


def optional_float(value: Any, location: str) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise GraphValidationError(f"{location} must be a number or null.") from exc


def optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def infer_role_hint(label: str) -> str | None:
    lowered = label.lower()
    for token in role_hint_tokens():
        if token in lowered:
            return token
    return None


def role_hint_tokens() -> list[str]:
    tokens = load_typology_skill().get("role_hint_tokens", [])
    if not isinstance(tokens, list):
        raise GraphValidationError("skills.afc_typology_mapping.typology_rules.role_hint_tokens must be a list.")
    return [str(token).strip().lower() for token in tokens if str(token).strip()]
