import copy
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from graphlens_agent.analytics import analyze_graph
from graphlens_agent.io import load_graph_json
from graphlens_agent.validator import (
    GraphValidationError,
    collect_validation_issues,
    validate_graph_document,
)


SAMPLE_PATH = ROOT / "samples" / "fan_in_collector.json"


def load_sample():
    return json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))


def graph_payload(edges, directed=True):
    node_ids = sorted({node_id for edge in edges for node_id in edge[:2]})
    return {
        "metadata": {
            "schema_version": "1.0",
            "source_type": "screenshot",
            "directed": directed,
            "extraction_confidence": 0.95,
        },
        "nodes": [
            {
                "id": node_id,
                "label": node_id.upper(),
                "type": "account",
                "confidence": 0.95,
            }
            for node_id in node_ids
        ],
        "edges": [
            {
                "id": f"edge_{index}",
                "source": source,
                "target": target,
                "confidence": 0.95,
            }
            for index, (source, target) in enumerate(edges)
        ],
    }


class Phase1SchemaValidatorTests(unittest.TestCase):
    def test_json_schema_artifact_loads(self):
        schema = json.loads((ROOT / "schemas" / "graph.schema.json").read_text(encoding="utf-8"))

        self.assertEqual(schema["title"], "GraphLens Graph Document")
        self.assertIn("node", schema["$defs"])
        self.assertIn("edge", schema["$defs"])

    def test_sample_json_validates(self):
        document = validate_graph_document(load_sample())

        self.assertEqual(document.metadata.schema_version, "1.0")
        self.assertEqual(len(document.nodes), 5)
        self.assertEqual(len(document.edges), 4)
        self.assertEqual(document.warnings, ["Sample graph is hand-authored for Phase 1 analytics and validation tests."])

    def test_load_graph_json_validates_file(self):
        document = load_graph_json(SAMPLE_PATH)

        self.assertEqual(document.nodes[-1].id, "acct_collector")

    def test_duplicate_node_ids_are_rejected(self):
        payload = load_sample()
        duplicate = copy.deepcopy(payload["nodes"][0])
        payload["nodes"].append(duplicate)

        with self.assertRaises(GraphValidationError) as context:
            validate_graph_document(payload)

        self.assertIn("duplicate node id", str(context.exception))

    def test_edges_must_reference_known_nodes(self):
        payload = load_sample()
        payload["edges"][0]["source"] = "missing_source"

        with self.assertRaises(GraphValidationError) as context:
            validate_graph_document(payload)

        self.assertIn("unknown source node", str(context.exception))

    def test_metadata_is_required(self):
        payload = load_sample()
        del payload["metadata"]

        with self.assertRaises(GraphValidationError) as context:
            validate_graph_document(payload)

        self.assertIn("metadata is required", str(context.exception))

    def test_low_confidence_values_become_warnings_not_errors(self):
        payload = load_sample()
        payload["edges"][0]["confidence"] = 0.4

        issues = collect_validation_issues(payload)
        warnings = [issue for issue in issues if issue.severity == "warning"]
        errors = [issue for issue in issues if issue.severity == "error"]
        document = validate_graph_document(payload)

        self.assertFalse(errors)
        self.assertTrue(any("low confidence" in issue.message for issue in warnings))
        self.assertTrue(any("low confidence" in warning for warning in document.warnings))


class Phase1AnalyticsTests(unittest.TestCase):
    def test_fan_in_sample_detects_collector_and_repeated_amounts(self):
        analysis = analyze_graph(load_sample())

        self.assertEqual(analysis["summary"]["graph_motif"], "fan_in_aggregation")
        self.assertTrue(analysis["summary"]["has_collector_behavior"])
        self.assertEqual(analysis["summary"]["collector_node"], "acct_collector")
        self.assertEqual(analysis["collector_behavior"]["inbound_sources"], ["acct_a", "acct_b", "acct_c", "acct_d"])
        self.assertEqual(analysis["nodes"]["acct_collector"]["in_degree"], 4)
        self.assertEqual(analysis["nodes"]["acct_collector"]["total_inbound_amount"], 1975.0)
        self.assertTrue(analysis["amount_patterns"]["has_repeated_amounts"])
        self.assertEqual(analysis["amount_patterns"]["repeated_amounts"], {"500": 3})

    def test_detects_fan_out_distribution(self):
        payload = graph_payload([("hub", "a"), ("hub", "b"), ("hub", "c")])

        analysis = analyze_graph(payload)

        self.assertEqual(analysis["summary"]["graph_motif"], "fan_out_distribution")
        self.assertEqual(analysis["summary"]["central_node"]["id"], "hub")

    def test_detects_chain(self):
        payload = graph_payload([("a", "b"), ("b", "c"), ("c", "d")])

        analysis = analyze_graph(payload)

        self.assertEqual(analysis["summary"]["graph_motif"], "chain")

    def test_detects_cycle(self):
        payload = graph_payload([("a", "b"), ("b", "c"), ("c", "a")])

        analysis = analyze_graph(payload)

        self.assertEqual(analysis["summary"]["graph_motif"], "cycle")

    def test_detects_undirected_hub_and_spoke(self):
        payload = graph_payload([("center", "a"), ("center", "b"), ("center", "c")], directed=False)

        analysis = analyze_graph(payload)

        self.assertEqual(analysis["summary"]["graph_motif"], "hub_and_spoke")
        self.assertEqual(analysis["summary"]["central_node"]["id"], "center")


class Phase1CliTests(unittest.TestCase):
    def run_cli(self, *args):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run(
            [sys.executable, "-m", "graphlens_agent.cli", *args],
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_cli_prints_formatted_analytics_json(self):
        result = self.run_cli(str(SAMPLE_PATH))

        self.assertEqual(result.returncode, 0, result.stderr)
        analysis = json.loads(result.stdout)
        self.assertEqual(analysis["summary"]["graph_motif"], "fan_in_aggregation")
        self.assertEqual(analysis["summary"]["collector_node"], "acct_collector")
        self.assertIn("\n  ", result.stdout)

    def test_cli_supports_help(self):
        result = self.run_cli("--help")

        self.assertEqual(result.returncode, 0)
        self.assertIn("usage:", result.stdout)
        self.assertIn("graph_json", result.stdout)


if __name__ == "__main__":
    unittest.main()
