from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from afc_network_narrative.harness.app.skill_loader import load_narrative_policy, load_prohibited_claims
from afc_network_narrative.harness.app.pipeline import analyze_graph
from afc_network_narrative.harness.evaluation.metrics import (
    missing_context_correctness,
    narrative_grounding_score,
    precision,
    recall,
    unsupported_claim_rate,
)


def run_golden_set(golden_dir: str | Path) -> dict[str, float]:
    cases = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(Path(golden_dir).glob("*.json"))]
    if not cases:
        raise ValueError(f"No JSON golden cases found in {golden_dir}")

    precisions = []
    recalls = []
    narratives = []
    limitations = []
    grounding = []
    for case in cases:
        output = analyze_graph(case["graph"]).to_dict()
        detected = {item["typology_id"] for item in output["detected_typologies"]}
        expected = set(case.get("expected_typologies", []))
        precisions.append(precision(detected, expected))
        recalls.append(recall(detected, expected))
        narratives.append(output["narrative"])
        limitations.append(output["limitations"])
        grounding.append(narrative_grounding_score(output))

    narrative_policy = load_narrative_policy()
    prohibited = load_prohibited_claims()
    required_terms = narrative_policy.get("evaluation_terms", {}).get("missing_context_required_terms", [])
    return {
        "typology_precision": round(sum(precisions) / len(precisions), 3),
        "typology_recall": round(sum(recalls) / len(recalls), 3),
        "unsupported_claim_rate": round(unsupported_claim_rate(narratives, prohibited), 3),
        "missing_context_correctness": round(missing_context_correctness(limitations, required_terms), 3),
        "narrative_grounding_score": round(sum(grounding) / len(grounding), 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("golden_dir")
    args = parser.parse_args()
    print(json.dumps(run_golden_set(args.golden_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
