# Investigation Playbooks Skill Contract

This document defines the boundary between the investigation playbooks skill and the Python harness.

## Ownership Boundary

- SME-owned:
  - `investigation_playbooks.yaml`
  - default investigation steps
  - typology-specific investigation steps

- Engineering-owned:
  - loading and validation
  - merging default and typology-specific steps
  - deduplication
  - output assembly

If an AFC SME should be able to change it without editing Python, it belongs in `investigation_playbooks.yaml`.

## Files

- Skill definition: `investigation_playbooks.yaml`
- Machine contract: `investigation_playbooks.schema.json`
- Skill description: `SKILL.md`

## Required Top-Level Keys

`investigation_playbooks.yaml` must define:

- `default_steps`
- `typology_steps`

## default_steps

An array of non-empty strings.

These steps are always included in recommended investigation output.

## typology_steps

An object mapping `typology_id` to an array of non-empty strings.

Example:

```yaml
typology_steps:
  fan_in_collection:
    - Review inbound counterparties for shared attributes or common funding behavior.
```

## Semantic Rules

- every key in `typology_steps` must correspond to a valid typology id from `skills/afc_typology_mapping/typology_rules.yaml`
- step strings must not be empty
- the harness may deduplicate repeated steps across default and typology-specific sections

## What the Harness Guarantees

When the playbook skill passes contract validation, the harness will:

- load default steps
- append typology-specific steps for matched typologies
- deduplicate repeated steps
- preserve text as written by the skill

## What the Skill Must Not Do

The skill must not:

- invent unknown typology ids
- rely on hidden Python fallback steps
- provide non-string steps

Invalid playbook files should fail early during loading.
