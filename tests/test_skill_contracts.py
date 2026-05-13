from __future__ import annotations

import copy
from pathlib import Path

import pytest

from afc_network_narrative.harness.app.skill_loader import (
    load_graph_extraction_schema,
    load_investigation_playbooks,
    load_narrative_policy,
    load_prohibited_claims,
    load_sar_red_flags,
    load_scoring_policy,
    load_source_registry,
    load_typology_glossary,
    load_typology_skill,
    validate_graph_image_extraction_skill_contract,
    validate_investigation_playbooks_contract,
    validate_narrative_policy_contract,
    validate_prohibited_claims_contract,
    validate_sar_red_flags_contract,
    validate_scoring_policy_contract,
    validate_source_registry_contract,
    validate_typology_glossary_contract,
    validate_typology_skill_contract,
)


def test_typology_skill_contract_accepts_current_yaml() -> None:
    skill = load_typology_skill()
    assert skill["typologies"]


def test_typology_skill_contract_rejects_invalid_graph_evidence_field() -> None:
    skill = copy.deepcopy(load_typology_skill())
    invalid = {
        **skill,
        "typologies": [
            {
                **skill["typologies"][0],
                "id": "bad_graph_rule",
                "match_scope": "graph",
                "conditions": {"metric": "repeated_amount_score", "min_value": 0.8},
                "evidence_fields": ["weighted_inbound_amount"],
            }
        ],
    }
    schema_path = Path(__file__).resolve().parents[1] / "skills" / "afc_typology_mapping" / "typology_rules.schema.json"
    with pytest.raises(ValueError, match="graph-scoped rules cannot use evidence_fields"):
        validate_typology_skill_contract(invalid, schema_path)


def test_typology_glossary_contract_accepts_current_yaml() -> None:
    glossary = load_typology_glossary()
    assert glossary["fan_in_collection"]


def test_typology_glossary_contract_rejects_unknown_typology_key() -> None:
    glossary = copy.deepcopy(load_typology_glossary())
    glossary["unknown_typology"] = "Unknown."
    schema_path = Path(__file__).resolve().parents[1] / "skills" / "afc_typology_mapping" / "typology_glossary.schema.json"
    with pytest.raises(ValueError, match="unknown typology ids"):
        validate_typology_glossary_contract(glossary, schema_path)


def test_source_registry_contract_accepts_current_yaml() -> None:
    registry = load_source_registry()
    assert registry["sources"]


def test_source_registry_contract_rejects_duplicate_source_ids() -> None:
    registry = copy.deepcopy(load_source_registry())
    registry["sources"].append(copy.deepcopy(registry["sources"][0]))
    schema_path = Path(__file__).resolve().parents[1] / "skills" / "afc_typology_mapping" / "source_registry.schema.json"
    with pytest.raises(ValueError, match="duplicate source ids"):
        validate_source_registry_contract(registry, schema_path)


def test_scoring_policy_contract_accepts_current_yaml() -> None:
    policy = load_scoring_policy()
    assert policy["priority_bands"]


def test_scoring_policy_contract_rejects_overlapping_bands() -> None:
    policy = copy.deepcopy(load_scoring_policy())
    policy["priority_bands"]["Low"] = [0, 50]
    policy["priority_bands"]["Medium"] = [40, 59]
    schema_path = Path(__file__).resolve().parents[1] / "skills" / "alert_investigation_boost" / "scoring_policy.schema.json"
    with pytest.raises(ValueError, match="overlaps"):
        validate_scoring_policy_contract(policy, schema_path)


def test_sar_red_flags_contract_accepts_current_yaml() -> None:
    red_flags = load_sar_red_flags()
    assert red_flags["decision_boundary"]["decision_value"] == "not_determined_by_system"
    assert red_flags["red_flags"]


def test_sar_red_flags_contract_rejects_unknown_related_typology() -> None:
    red_flags = copy.deepcopy(load_sar_red_flags())
    red_flags["red_flags"][0]["related_typologies"].append("unknown_typology")
    schema_path = Path(__file__).resolve().parents[1] / "skills" / "alert_investigation_boost" / "sar_red_flags.schema.json"
    with pytest.raises(ValueError, match="unknown related_typologies"):
        validate_sar_red_flags_contract(red_flags, schema_path)


def test_narrative_policy_contract_accepts_current_yaml_and_template() -> None:
    policy = load_narrative_policy()
    assert policy["section_templates"]


def test_narrative_policy_contract_rejects_missing_placeholder() -> None:
    policy = copy.deepcopy(load_narrative_policy())
    policy["section_templates"]["alert_boost"] = "{priority_band} priority only"
    schema_path = Path(__file__).resolve().parents[1] / "skills" / "narrative_generation" / "narrative_policy.schema.json"
    template_path = Path(__file__).resolve().parents[1] / "skills" / "narrative_generation" / "narrative_template.md"
    with pytest.raises(ValueError, match="missing placeholders"):
        validate_narrative_policy_contract(policy, schema_path, template_path)


def test_prohibited_claims_contract_accepts_current_yaml() -> None:
    claims = load_prohibited_claims()
    assert "SAR required" in claims


def test_prohibited_claims_contract_rejects_missing_required_baseline_claim() -> None:
    claims = {"prohibited_claims": [claim for claim in load_prohibited_claims() if claim != "SAR required"]}
    schema_path = Path(__file__).resolve().parents[1] / "skills" / "narrative_generation" / "prohibited_claims.schema.json"
    with pytest.raises(ValueError, match="missing required baseline claims"):
        validate_prohibited_claims_contract(claims, schema_path)


def test_investigation_playbooks_contract_accepts_current_yaml() -> None:
    playbooks = load_investigation_playbooks()
    assert playbooks["default_steps"]


def test_investigation_playbooks_contract_rejects_unknown_typology_key() -> None:
    playbooks = copy.deepcopy(load_investigation_playbooks())
    playbooks["typology_steps"]["unknown_typology"] = ["Review something."]
    schema_path = Path(__file__).resolve().parents[1] / "skills" / "alert_investigation_boost" / "investigation_playbooks.schema.json"
    with pytest.raises(ValueError, match="unknown typology_steps keys"):
        validate_investigation_playbooks_contract(playbooks, schema_path)


def test_graph_image_extraction_contract_accepts_current_files() -> None:
    schema = load_graph_extraction_schema()
    assert schema["properties"]["nodes"]


def test_graph_image_extraction_contract_rejects_prompt_missing_required_instruction() -> None:
    prompt = "Return JSON only."
    schema_path = Path(__file__).resolve().parents[1] / "skills" / "graph_image_extraction" / "graph_schema.json"
    contract_path = Path(__file__).resolve().parents[1] / "skills" / "graph_image_extraction" / "graph_schema_contract.schema.json"
    with pytest.raises(ValueError, match="missing required instruction fragments"):
        validate_graph_image_extraction_skill_contract(prompt, schema_path, contract_path)
