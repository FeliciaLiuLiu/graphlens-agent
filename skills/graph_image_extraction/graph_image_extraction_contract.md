# Graph Image Extraction Skill Contract

This document defines the boundary between the graph image extraction skill and the Python harness.

## Ownership Boundary

- SME-owned:
  - `extraction_prompt.md`
  - `graph_schema.json`

- Engineering-owned:
  - local Qwen loading
  - prompt submission
  - response parsing
  - schema validation
  - retry behavior
  - downstream graph validation

If an AFC SME should be able to change it without editing Python, it belongs in `extraction_prompt.md` or `graph_schema.json`, subject to this contract.

## Files

- Skill prompt: `extraction_prompt.md`
- Skill schema: `graph_schema.json`
- Machine contract for schema file: `graph_schema_contract.schema.json`
- Skill description: `SKILL.md`

## extraction_prompt.md Requirements

The prompt must explicitly instruct Qwen to:

- extract only visible network graph facts
- return JSON only
- avoid AML, AFC, fraud, sanctions, suspicious activity, and typology inference
- return:
  - `case_id`
  - `nodes`
  - `edges`
  - `visual_signals`
  - `extraction_uncertainties`
- follow arrowheads for direction
- reduce `direction_confidence` when direction is uncertain
- normalize visible amount text

The harness validates these requirements by checking for required instruction fragments.

## graph_schema.json Requirements

`graph_schema.json` must remain a Draft 2020-12 JSON Schema describing the extractor output object.

Top-level contract:

- `type: object`
- `additionalProperties: false`
- required fields:
  - `nodes`
  - `edges`
  - `visual_signals`
  - `extraction_uncertainties`

Node item contract:

- `additionalProperties: false`
- required:
  - `id`
  - `label`
  - `confidence`

Edge item contract:

- `additionalProperties: false`
- required:
  - `source`
  - `target`
  - `direction_confidence`
  - `amount_confidence`

## What the Harness Guarantees

When the graph extraction skill passes contract validation, the harness will:

- load the prompt text
- load the extraction schema
- validate the extraction schema contract
- call Qwen with the prompt
- parse JSON output
- pass the result into downstream graph validation

## What the Skill Must Not Do

The skill must not:

- remove required output fields expected by the harness
- weaken the prompt so it asks Qwen for AFC interpretation
- add hidden fallback assumptions in place of explicit prompt instructions

Invalid graph extraction skill files should fail early during loading.
