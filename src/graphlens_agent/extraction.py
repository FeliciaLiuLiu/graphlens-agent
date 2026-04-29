from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional, Protocol

from graphlens_agent.schema import GraphDocument
from graphlens_agent.validator import validate_graph_document


class ScreenshotExtractionProvider(Protocol):
    def extract(self, filename: Optional[str], content_type: Optional[str], content: bytes) -> GraphDocument:
        """Extract a graph document from uploaded screenshot bytes."""


class MockScreenshotExtractionProvider:
    """Phase 2A mock provider that returns the bundled fan-in sample graph."""

    def __init__(self, sample_path: Optional[Path] = None) -> None:
        self.sample_path = sample_path or Path(__file__).resolve().parents[2] / "samples" / "fan_in_collector.json"

    def extract(self, filename: Optional[str], content_type: Optional[str], content: bytes) -> GraphDocument:
        with self.sample_path.open("r", encoding="utf-8") as handle:
            payload: Dict[str, Any] = json.load(handle)

        mock_payload = deepcopy(payload)
        warnings = list(mock_payload.get("warnings", []))
        warnings.append("Mock extraction result: no real screenshot analysis was performed.")
        mock_payload["warnings"] = warnings
        return validate_graph_document(mock_payload)
