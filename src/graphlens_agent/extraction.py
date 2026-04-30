from __future__ import annotations

import json
from copy import deepcopy
import os
from pathlib import Path
from typing import Any, Dict, Optional, Protocol

from graphlens_agent.schema import GraphDocument
from graphlens_agent.validator import validate_graph_document


ALLOWED_EXTRACTION_PROVIDERS = ("mock", "local_cv")


class ScreenshotExtractionProvider(Protocol):
    def extract(self, filename: Optional[str], content_type: Optional[str], content: bytes) -> GraphDocument:
        """Extract a graph document from uploaded screenshot bytes."""


class ProviderConfigurationError(ValueError):
    """Raised when screenshot extraction provider configuration is invalid."""


class LocalCVNotImplementedError(NotImplementedError):
    """Raised when the planned local OCR/OpenCV provider is selected."""


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


class LocalCVExtractionProvider:
    """Planned local OCR/OpenCV screenshot extraction provider."""

    def extract(self, filename: Optional[str], content_type: Optional[str], content: bytes) -> GraphDocument:
        raise LocalCVNotImplementedError(
            "Local OCR/OpenCV screenshot extraction is planned but not implemented yet. "
            "Use GRAPH_EXTRACTION_PROVIDER=mock for the current portfolio demo."
        )


def get_screenshot_extraction_provider(provider_name: Optional[str] = None) -> ScreenshotExtractionProvider:
    selected_provider = (provider_name or os.getenv("GRAPH_EXTRACTION_PROVIDER", "mock")).strip().lower()
    if selected_provider == "mock":
        return MockScreenshotExtractionProvider()
    if selected_provider == "local_cv":
        return LocalCVExtractionProvider()
    raise ProviderConfigurationError(
        "Unsupported GRAPH_EXTRACTION_PROVIDER "
        f"{selected_provider!r}. Expected one of: {', '.join(ALLOWED_EXTRACTION_PROVIDERS)}."
    )
