from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class Position:
    """Approximate node position in screenshot or canvas coordinates."""

    x: float
    y: float
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "x": self.x,
            "y": self.y,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class GraphMetadata:
    schema_version: str = SCHEMA_VERSION
    source_type: str = "screenshot"
    directed: bool = True
    source_name: Optional[str] = None
    extraction_method: Optional[str] = None
    extraction_confidence: float = 1.0
    created_at: Optional[str] = None
    domain: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "schema_version": self.schema_version,
            "source_type": self.source_type,
            "directed": self.directed,
            "extraction_confidence": self.extraction_confidence,
        }
        if self.source_name is not None:
            payload["source_name"] = self.source_name
        if self.extraction_method is not None:
            payload["extraction_method"] = self.extraction_method
        if self.created_at is not None:
            payload["created_at"] = self.created_at
        if self.domain is not None:
            payload["domain"] = self.domain
        return payload


@dataclass(frozen=True)
class GraphNode:
    id: str
    label: str
    type: str = "entity"
    confidence: float = 1.0
    position: Optional[Position] = None
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "confidence": self.confidence,
        }
        if self.position is not None:
            payload["position"] = self.position.to_dict()
        if self.attributes:
            payload["attributes"] = self.attributes
        return payload


@dataclass(frozen=True)
class GraphEdge:
    id: str
    source: str
    target: str
    label: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    directed: Optional[bool] = None
    confidence: float = 1.0
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "confidence": self.confidence,
        }
        if self.label is not None:
            payload["label"] = self.label
        if self.amount is not None:
            payload["amount"] = self.amount
        if self.currency is not None:
            payload["currency"] = self.currency
        if self.directed is not None:
            payload["directed"] = self.directed
        if self.attributes:
            payload["attributes"] = self.attributes
        return payload


@dataclass(frozen=True)
class GraphDocument:
    metadata: GraphMetadata
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "warnings": list(self.warnings),
        }
