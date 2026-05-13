from __future__ import annotations

import json
from string import Formatter
from functools import lru_cache
from pathlib import Path
from typing import Any


def project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() and (parent / "skills").is_dir():
            return parent
    raise ValueError("Could not locate project root containing pyproject.toml and skills/.")


@lru_cache(maxsize=None)
def load_structured_file(path: str) -> dict[str, Any]:
    text = Path(path).read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
    except Exception:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"Expected object in {path}")
    return data


@lru_cache(maxsize=None)
def load_text_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8").strip()


def load_typology_skill(path: str | Path | None = None) -> dict[str, Any]:
    resolved = Path(path) if path else project_root() / "skills" / "afc_typology_mapping" / "typology_rules.yaml"
    data = load_structured_file(str(resolved))
    schema_path = project_root() / "skills" / "afc_typology_mapping" / "typology_rules.schema.json"
    validate_typology_skill_contract(data, schema_path)
    typology_ids = {str(rule["id"]) for rule in data.get("typologies", [])}
    load_typology_glossary(expected_typology_ids=typology_ids)
    load_source_registry()
    return data


def load_scoring_policy(path: str | Path | None = None) -> dict[str, Any]:
    resolved = Path(path) if path else project_root() / "skills" / "alert_investigation_boost" / "scoring_policy.yaml"
    data = load_structured_file(str(resolved))
    schema_path = project_root() / "skills" / "alert_investigation_boost" / "scoring_policy.schema.json"
    validate_scoring_policy_contract(data, schema_path)
    return data


def load_narrative_policy(path: str | Path | None = None) -> dict[str, Any]:
    resolved = Path(path) if path else project_root() / "skills" / "narrative_generation" / "narrative_policy.yaml"
    data = load_structured_file(str(resolved))
    schema_path = project_root() / "skills" / "narrative_generation" / "narrative_policy.schema.json"
    template_path = project_root() / "skills" / "narrative_generation" / "narrative_template.md"
    validate_narrative_policy_contract(data, schema_path, template_path)
    return data


def load_prohibited_claims(path: str | Path | None = None) -> list[str]:
    resolved = Path(path) if path else project_root() / "skills" / "narrative_generation" / "prohibited_claims.yaml"
    data = load_structured_file(str(resolved))
    schema_path = project_root() / "skills" / "narrative_generation" / "prohibited_claims.schema.json"
    validate_prohibited_claims_contract(data, schema_path)
    claims = data.get("prohibited_claims", [])
    if not isinstance(claims, list):
        raise ValueError("prohibited_claims must be a list.")
    return [str(item) for item in claims]


def load_narrative_template(path: str | Path | None = None) -> str:
    resolved = Path(path) if path else project_root() / "skills" / "narrative_generation" / "narrative_template.md"
    return load_text_file(str(resolved))


def load_extraction_prompt(path: str | Path | None = None) -> str:
    resolved = Path(path) if path else project_root() / "skills" / "graph_image_extraction" / "extraction_prompt.md"
    prompt = load_text_file(str(resolved))
    schema_path = project_root() / "skills" / "graph_image_extraction" / "graph_schema.json"
    contract_path = project_root() / "skills" / "graph_image_extraction" / "graph_schema_contract.schema.json"
    validate_graph_image_extraction_skill_contract(prompt, schema_path, contract_path)
    return prompt


def load_investigation_playbooks(path: str | Path | None = None) -> dict[str, Any]:
    resolved = Path(path) if path else project_root() / "skills" / "alert_investigation_boost" / "investigation_playbooks.yaml"
    data = load_structured_file(str(resolved))
    schema_path = project_root() / "skills" / "alert_investigation_boost" / "investigation_playbooks.schema.json"
    validate_investigation_playbooks_contract(data, schema_path)
    return data


def load_graph_extraction_schema(path: str | Path | None = None) -> dict[str, Any]:
    resolved = Path(path) if path else project_root() / "skills" / "graph_image_extraction" / "graph_schema.json"
    data = load_structured_file(str(resolved))
    contract_path = project_root() / "skills" / "graph_image_extraction" / "graph_schema_contract.schema.json"
    prompt_path = project_root() / "skills" / "graph_image_extraction" / "extraction_prompt.md"
    validate_graph_image_extraction_skill_contract(load_text_file(str(prompt_path)), resolved, contract_path, schema_data=data)
    return data


def load_typology_glossary(
    path: str | Path | None = None,
    *,
    expected_typology_ids: set[str] | None = None,
) -> dict[str, str]:
    resolved = Path(path) if path else project_root() / "skills" / "afc_typology_mapping" / "typology_glossary.yaml"
    data = load_structured_file(str(resolved))
    schema_path = project_root() / "skills" / "afc_typology_mapping" / "typology_glossary.schema.json"
    validate_typology_glossary_contract(data, schema_path, expected_typology_ids=expected_typology_ids)
    return {str(key): str(value) for key, value in data.items()}


def load_source_registry(path: str | Path | None = None) -> dict[str, Any]:
    resolved = Path(path) if path else project_root() / "skills" / "afc_typology_mapping" / "source_registry.yaml"
    data = load_structured_file(str(resolved))
    schema_path = project_root() / "skills" / "afc_typology_mapping" / "source_registry.schema.json"
    validate_source_registry_contract(data, schema_path)
    return data


def validate_typology_skill_contract(data: dict[str, Any], schema_path: str | Path) -> None:
    validate_json_contract(data, schema_path, "Typology skill")
    validate_typology_skill_semantics(data)


def validate_scoring_policy_contract(data: dict[str, Any], schema_path: str | Path) -> None:
    validate_json_contract(data, schema_path, "Scoring policy")
    validate_scoring_policy_semantics(data)


def validate_narrative_policy_contract(
    data: dict[str, Any],
    schema_path: str | Path,
    template_path: str | Path,
) -> None:
    validate_json_contract(data, schema_path, "Narrative policy")
    validate_narrative_policy_semantics(data)
    validate_narrative_template_contract(load_text_file(str(template_path)))


def validate_prohibited_claims_contract(data: dict[str, Any], schema_path: str | Path) -> None:
    validate_json_contract(data, schema_path, "Prohibited claims")
    validate_prohibited_claims_semantics(data)


def validate_typology_glossary_contract(
    data: dict[str, Any],
    schema_path: str | Path,
    *,
    expected_typology_ids: set[str] | None = None,
) -> None:
    validate_json_contract(data, schema_path, "Typology glossary")
    validate_typology_glossary_semantics(data, expected_typology_ids=expected_typology_ids)


def validate_source_registry_contract(data: dict[str, Any], schema_path: str | Path) -> None:
    validate_json_contract(data, schema_path, "Source registry")
    validate_source_registry_semantics(data)


def validate_json_contract(data: dict[str, Any], schema_path: str | Path, label: str) -> None:
    schema = load_structured_file(str(schema_path))
    try:
        import jsonschema  # type: ignore
    except ImportError as exc:
        raise ValueError("jsonschema is required to validate skill contracts.") from exc

    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as exc:  # type: ignore[attr-defined]
        location = ".".join(str(item) for item in exc.absolute_path) or "root"
        raise ValueError(f"{label} contract validation failed at {location}: {exc.message}") from exc


def validate_investigation_playbooks_contract(data: dict[str, Any], schema_path: str | Path) -> None:
    validate_json_contract(data, schema_path, "Investigation playbooks")
    validate_investigation_playbooks_semantics(data)


def validate_graph_image_extraction_skill_contract(
    prompt_text: str,
    schema_path: str | Path,
    contract_path: str | Path,
    *,
    schema_data: dict[str, Any] | None = None,
) -> None:
    schema = schema_data if schema_data is not None else load_structured_file(str(schema_path))
    validate_json_contract(schema, contract_path, "Graph extraction schema")
    validate_graph_extraction_schema_semantics(schema)
    validate_extraction_prompt_semantics(prompt_text)


def validate_typology_skill_semantics(data: dict[str, Any]) -> None:
    typologies = data.get("typologies", [])
    ids = [str(rule["id"]) for rule in typologies]
    duplicates = sorted({rule_id for rule_id in ids if ids.count(rule_id) > 1})
    if duplicates:
        raise ValueError(f"Typology skill contract validation failed: duplicate typology ids: {', '.join(duplicates)}")

    node_evidence_fields = {
        "in_degree",
        "out_degree",
        "weighted_inbound_amount",
        "weighted_outbound_amount",
        "weighted_flow_amount",
        "repeated_amount_score",
        "repeated_amount_value",
    }
    graph_evidence_fields = {
        "repeated_amount_score",
        "repeated_amount_value",
        "fan_out_nodes",
        "fan_in_nodes",
        "cycle_count",
        "many_to_many_groups",
    }

    for rule in typologies:
        rule_id = str(rule["id"])
        scope = str(rule["match_scope"])
        evidence_fields = {str(field) for field in rule.get("evidence_fields", [])}
        if scope == "node":
            unsupported = sorted(evidence_fields - node_evidence_fields)
            if unsupported:
                raise ValueError(
                    f"Typology skill contract validation failed for {rule_id}: "
                    f"node-scoped rules cannot use evidence_fields {', '.join(unsupported)}"
                )
        elif scope == "graph":
            unsupported = sorted(evidence_fields - graph_evidence_fields)
            if unsupported:
                raise ValueError(
                    f"Typology skill contract validation failed for {rule_id}: "
                    f"graph-scoped rules cannot use evidence_fields {', '.join(unsupported)}"
                )
        else:
            raise ValueError(f"Typology skill contract validation failed for {rule_id}: unsupported match_scope {scope!r}")


def validate_typology_glossary_semantics(
    data: dict[str, Any],
    *,
    expected_typology_ids: set[str] | None = None,
) -> None:
    ids = expected_typology_ids if expected_typology_ids is not None else raw_typology_ids()
    glossary_ids = {str(key) for key in data}
    missing = sorted(ids - glossary_ids)
    extra = sorted(glossary_ids - ids)
    if missing:
        raise ValueError(
            "Typology glossary contract validation failed: "
            f"missing typology ids: {', '.join(missing)}"
        )
    if extra:
        raise ValueError(
            "Typology glossary contract validation failed: "
            f"unknown typology ids: {', '.join(extra)}"
        )


def validate_source_registry_semantics(data: dict[str, Any]) -> None:
    sources = data.get("sources", [])
    ids = [str(item["id"]) for item in sources]
    duplicates = sorted({source_id for source_id in ids if ids.count(source_id) > 1})
    if duplicates:
        raise ValueError(f"Source registry contract validation failed: duplicate source ids: {', '.join(duplicates)}")

    required_ids = {"internal_graph_features", "visible_graph_image"}
    missing = sorted(required_ids - set(ids))
    if missing:
        raise ValueError(
            "Source registry contract validation failed: "
            f"missing required source ids: {', '.join(missing)}"
        )


def validate_prohibited_claims_semantics(data: dict[str, Any]) -> None:
    claims = [str(item).strip() for item in data.get("prohibited_claims", [])]
    lowered = [claim.lower() for claim in claims]
    duplicates = sorted({claim for claim in lowered if lowered.count(claim) > 1})
    if duplicates:
        raise ValueError(
            "Prohibited claims contract validation failed: "
            f"duplicate claims: {', '.join(duplicates)}"
        )

    required_claims = {
        "confirmed money laundering",
        "committed money laundering",
        "sar required",
    }
    missing = sorted(required_claims - set(lowered))
    if missing:
        raise ValueError(
            "Prohibited claims contract validation failed: "
            f"missing required baseline claims: {', '.join(missing)}"
        )


def validate_investigation_playbooks_semantics(data: dict[str, Any]) -> None:
    valid_typology_ids = {str(rule["id"]) for rule in load_typology_skill().get("typologies", [])}
    unknown = sorted(set(data["typology_steps"]) - valid_typology_ids)
    if unknown:
        raise ValueError(
            "Investigation playbooks contract validation failed: "
            f"unknown typology_steps keys: {', '.join(unknown)}"
        )


def raw_typology_ids() -> set[str]:
    path = project_root() / "skills" / "afc_typology_mapping" / "typology_rules.yaml"
    data = load_structured_file(str(path))
    typologies = data.get("typologies", [])
    if not isinstance(typologies, list):
        raise ValueError("Unable to read typology ids from typology_rules.yaml.")
    return {str(rule["id"]) for rule in typologies}


def validate_graph_extraction_schema_semantics(schema: dict[str, Any]) -> None:
    try:
        import jsonschema  # type: ignore
    except ImportError as exc:
        raise ValueError("jsonschema is required to validate skill contracts.") from exc

    try:
        jsonschema.Draft202012Validator.check_schema(schema)  # type: ignore[attr-defined]
    except jsonschema.SchemaError as exc:  # type: ignore[attr-defined]
        raise ValueError(f"Graph extraction schema contract validation failed: invalid JSON Schema: {exc.message}") from exc

    top_required = set(schema["required"])
    required_top_fields = {"nodes", "edges", "visual_signals", "extraction_uncertainties"}
    missing_top_fields = sorted(required_top_fields - top_required)
    if missing_top_fields:
        raise ValueError(
            "Graph extraction schema contract validation failed: "
            f"top-level required fields missing: {', '.join(missing_top_fields)}"
        )

    node_required = set(schema["properties"]["nodes"]["items"]["required"])
    missing_node_fields = sorted({"id", "label", "confidence"} - node_required)
    if missing_node_fields:
        raise ValueError(
            "Graph extraction schema contract validation failed: "
            f"node required fields missing: {', '.join(missing_node_fields)}"
        )

    edge_required = set(schema["properties"]["edges"]["items"]["required"])
    missing_edge_fields = sorted({"source", "target", "direction_confidence", "amount_confidence"} - edge_required)
    if missing_edge_fields:
        raise ValueError(
            "Graph extraction schema contract validation failed: "
            f"edge required fields missing: {', '.join(missing_edge_fields)}"
        )


def validate_extraction_prompt_semantics(prompt_text: str) -> None:
    required_fragments = [
        "Extract only visible network graph facts.",
        "Return JSON only.",
        "Do not infer AML, AFC, fraud, sanctions, suspicious activity, or typology.",
        "case_id",
        "nodes",
        "edges",
        "visual_signals",
        "extraction_uncertainties",
        "Follow arrowheads for edge direction.",
        "direction_confidence below 0.6",
        "Normalize visible amounts",
    ]
    missing = [fragment for fragment in required_fragments if fragment not in prompt_text]
    if missing:
        raise ValueError(
            "Graph extraction prompt contract validation failed: "
            f"missing required instruction fragments: {', '.join(missing)}"
        )


def validate_scoring_policy_semantics(data: dict[str, Any]) -> None:
    deduction = int(data["deductions"]["low_extraction_confidence"])
    if deduction > 0:
        raise ValueError("Scoring policy contract validation failed: deductions.low_extraction_confidence must be 0 or negative")

    typology_match_template = str(data["reason_templates"]["typology_match"])
    require_placeholders(
        typology_match_template,
        {"typology_name"},
        "Scoring policy contract validation failed: reason_templates.typology_match",
    )
    require_placeholders(
        str(data["explanation_template"]),
        {"priority_band", "score", "reason_codes"},
        "Scoring policy contract validation failed: explanation_template",
    )

    seen_ranges: list[tuple[str, int, int]] = []
    for band_name, bounds in data["priority_bands"].items():
        lower = int(bounds[0])
        upper = int(bounds[1])
        if lower > upper:
            raise ValueError(
                f"Scoring policy contract validation failed: priority_bands.{band_name} lower bound must be <= upper bound"
            )
        for existing_name, existing_lower, existing_upper in seen_ranges:
            if not (upper < existing_lower or lower > existing_upper):
                raise ValueError(
                    "Scoring policy contract validation failed: "
                    f"priority_bands.{band_name} overlaps with priority_bands.{existing_name}"
                )
        seen_ranges.append((str(band_name), lower, upper))


def validate_narrative_policy_semantics(data: dict[str, Any]) -> None:
    section_templates = data["section_templates"]
    required_section_placeholders = {
        "network_observation": {"node_count", "edge_count", "fan_in_nodes", "fan_out_nodes", "pass_through_nodes"},
        "typology_hypothesis": {"typology_name", "confidence", "evidence", "caution"},
        "alert_boost": {"priority_band", "score", "explanation"},
        "key_evidence_match": {"typology_name", "evidence"},
        "evidence_item": {"metric", "value", "node_suffix"},
        "evidence_item_with_amount": {"metric", "value", "amount_value", "node_suffix"},
    }
    for key, placeholders in required_section_placeholders.items():
        require_placeholders(
            str(section_templates[key]),
            placeholders,
            f"Narrative policy contract validation failed: section_templates.{key}",
        )
    report_pdf = data["report_pdf"]
    require_placeholders(
        str(report_pdf["subtitle_template"]),
        {"case_id"},
        "Narrative policy contract validation failed: report_pdf.subtitle_template",
    )
    require_placeholders(
        str(report_pdf["input_reference_template"]),
        {"input_name"},
        "Narrative policy contract validation failed: report_pdf.input_reference_template",
    )
    require_placeholders(
        str(report_pdf["typology_line_template"]),
        {"name", "confidence", "interpretation"},
        "Narrative policy contract validation failed: report_pdf.typology_line_template",
    )
    require_placeholders(
        str(report_pdf["alert_boost_template"]),
        {"priority_band", "score", "explanation"},
        "Narrative policy contract validation failed: report_pdf.alert_boost_template",
    )
    require_placeholders(
        str(report_pdf["evidence_line_template"]),
        {"label", "details"},
        "Narrative policy contract validation failed: report_pdf.evidence_line_template",
    )


def validate_narrative_template_contract(template_text: str) -> None:
    require_placeholders(
        template_text,
        {
            "network_observation",
            "typology_hypothesis",
            "alert_boost",
            "evidence",
            "recommended_steps",
            "limitations",
        },
        "Narrative template contract validation failed",
    )


def require_placeholders(template: str, required_placeholders: set[str], error_prefix: str) -> None:
    found = {
        field_name
        for _, field_name, _, _ in Formatter().parse(template)
        if field_name
    }
    missing = sorted(required_placeholders - found)
    if missing:
        raise ValueError(f"{error_prefix} missing placeholders: {', '.join(missing)}")
