# Narrative Policy Skill Contract

This document defines the boundary between the narrative generation skill and the Python harness.

## Ownership Boundary

- SME-owned:
  - `narrative_policy.yaml`
  - `narrative_template.md`
  - section text templates
  - rendering separators and `none` text
  - static limitation text
  - evaluation term lists

- Engineering-owned:
  - template rendering
  - evidence object construction
  - prohibited-claim enforcement
  - output assembly
  - error handling

If an AFC SME should be able to change it without editing Python, it belongs in the narrative skill files.

## Files

- Skill definition: `narrative_policy.yaml`
- Machine contract: `narrative_policy.schema.json`
- Layout template: `narrative_template.md`
- Skill description: `SKILL.md`

## Required Top-Level Keys

`narrative_policy.yaml` must define:

- `section_templates`
- `rendering`
- `static_limitations`
- `evaluation_terms`
- `report_pdf`

## section_templates

Required keys:

- `network_observation`
- `typology_hypothesis`
- `no_match_hypothesis`
- `alert_boost`
- `key_evidence_match`
- `key_evidence_fallback`
- `evidence_item`
- `evidence_item_with_amount`

Each required key must be a non-empty string.

### Required placeholders

`network_observation` must contain:

- `{node_count}`
- `{edge_count}`
- `{fan_in_nodes}`
- `{fan_out_nodes}`
- `{pass_through_nodes}`

`typology_hypothesis` must contain:

- `{typology_name}`
- `{confidence}`
- `{evidence}`
- `{caution}`

`alert_boost` must contain:

- `{priority_band}`
- `{score}`
- `{explanation}`

`key_evidence_match` must contain:

- `{typology_name}`
- `{evidence}`

`evidence_item` must contain:

- `{metric}`
- `{value}`
- `{node_suffix}`

`evidence_item_with_amount` must contain:

- `{metric}`
- `{value}`
- `{amount_value}`
- `{node_suffix}`

## rendering

Required keys:

- `none_text`
- `list_joiner`
- `section_joiner`

All values must be strings.

## static_limitations

List of strings appended to every narrative output.

This is where the narrative skill owns text such as:

- output is an investigative aid
- output does not make a SAR filing decision

## evaluation_terms

Required keys:

- `missing_context_required_terms`

This list is used by evaluation metrics when checking whether missing-context language is present.

## report_pdf

Required keys:

- `title`
- `subtitle_template`
- `input_reference_template`
- `section_titles`
- `summary_item_templates`
- `typology_line_template`
- `alert_boost_template`
- `evidence_line_template`
- `max_evidence_items`

### Required placeholders

`subtitle_template` must contain:

- `{case_id}`

`input_reference_template` must contain:

- `{input_name}`

`typology_line_template` must contain:

- `{name}`
- `{confidence}`
- `{interpretation}`

`alert_boost_template` must contain:

- `{priority_band}`
- `{score}`
- `{explanation}`

`evidence_line_template` must contain:

- `{label}`
- `{details}`

## narrative_template.md

The outer template must contain these placeholders exactly once or more:

- `{network_observation}`
- `{typology_hypothesis}`
- `{alert_boost}`
- `{evidence}`
- `{recommended_steps}`
- `{limitations}`

The harness validates this contract when loading the narrative skill.

## What the Harness Guarantees

When the narrative skill passes contract validation, the harness will:

- format each narrative section using the configured templates
- render evidence consistently
- join sections using configured separators
- append static limitations
- reject prohibited claims

## What the Skill Must Not Do

The skill must not:

- omit required template placeholders
- rely on hidden Python fallback text
- rename required section keys
- provide an outer template that drops a required narrative section

Invalid narrative skill files should fail early during loading.
