from __future__ import annotations

from typing import Any

from afc_network_narrative.features.graph_features import build_graph_features
from afc_network_narrative.narrative.narrative_builder import build_narrative_output
from afc_network_narrative.rules.rule_engine import RuleEngine
from afc_network_narrative.rules.scoring import score_alert
from afc_network_narrative.schemas.afc_output_schema import AFCNarrativeOutput
from afc_network_narrative.schemas.graph_extraction_schema import GraphExtraction, validate_graph_extraction
from afc_network_narrative.vlm.base import VLMAdapter


def analyze_graph(graph_payload: GraphExtraction | dict[str, Any] | str) -> AFCNarrativeOutput:
    graph = validate_graph_extraction(graph_payload)
    features = build_graph_features(graph)
    matches = RuleEngine().match(graph, features)
    alert_boost = score_alert(graph, features, matches)
    return build_narrative_output(graph, features, matches, alert_boost)


def analyze_image_file(image_path: str, adapter: VLMAdapter) -> AFCNarrativeOutput:
    graph = adapter.extract_graph(image_path)
    return analyze_graph(graph)
