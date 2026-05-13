from __future__ import annotations

from abc import ABC, abstractmethod

from afc_network_narrative.schemas.graph_extraction_schema import GraphExtraction


class VLMAdapterError(RuntimeError):
    """Raised when a visual model adapter cannot produce GraphExtraction."""


class VLMAdapter(ABC):
    """Stable interface between visual models and the model-independent pipeline."""

    @abstractmethod
    def extract_graph(self, image_path: str) -> GraphExtraction:
        """Extract visible network graph facts from an image."""
