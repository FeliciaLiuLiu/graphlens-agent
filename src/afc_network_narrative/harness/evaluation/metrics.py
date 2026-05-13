from __future__ import annotations

from typing import Any


def precision(detected: set[str], expected: set[str]) -> float:
    if not detected:
        return 1.0 if not expected else 0.0
    return len(detected & expected) / len(detected)


def recall(detected: set[str], expected: set[str]) -> float:
    if not expected:
        return 1.0
    return len(detected & expected) / len(expected)


def unsupported_claim_rate(narratives: list[str], prohibited: list[str]) -> float:
    if not narratives:
        return 0.0
    violations = 0
    for narrative in narratives:
        lowered = narrative.lower()
        if any(claim.lower() in lowered for claim in prohibited):
            violations += 1
    return violations / len(narratives)


def missing_context_correctness(limitations: list[list[str]], required_terms: list[str]) -> float:
    if not limitations:
        return 0.0
    scores = []
    for items in limitations:
        text = " ".join(items).lower()
        if not required_terms:
            scores.append(0.0)
            continue
        scores.append(sum(1 for term in required_terms if str(term).lower() in text) / len(required_terms))
    return sum(scores) / len(scores)


def narrative_grounding_score(output: dict[str, Any]) -> float:
    evidence = output.get("evidence", [])
    narrative = output.get("narrative", "")
    if not evidence:
        return 1.0
    mentions = 0
    for item in evidence[:10]:
        token = item.get("node_id") or item.get("source") or item.get("target")
        if token and str(token) in narrative:
            mentions += 1
    return mentions / min(len(evidence), 10)
