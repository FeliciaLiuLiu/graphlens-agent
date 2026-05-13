from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AFCNarrativeOutput:
    graph_summary: dict[str, Any]
    detected_typologies: list[dict[str, Any]]
    alert_boost: dict[str, Any]
    sar_red_flags: dict[str, Any]
    recommended_investigation_steps: list[str]
    narrative: str
    limitations: list[str]
    evidence: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph_summary": self.graph_summary,
            "detected_typologies": self.detected_typologies,
            "alert_boost": self.alert_boost,
            "sar_red_flags": self.sar_red_flags,
            "recommended_investigation_steps": self.recommended_investigation_steps,
            "narrative": self.narrative,
            "limitations": self.limitations,
            "evidence": self.evidence,
        }
