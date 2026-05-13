# Typology Glossary Skill Contract

This document defines the boundary between the typology glossary skill file and the Python harness.

## Ownership Boundary

- SME-owned:
  - human-readable glossary text for each typology id

- Engineering-owned:
  - typology ids declared in `typology_rules.yaml`
  - validation that glossary coverage matches runtime typology ids

## Files

- Skill definition: `typology_glossary.yaml`
- Machine contract: `typology_glossary.schema.json`

## Required Structure

`typology_glossary.yaml` is a flat object:

```yaml
fan_in_collection: "..."
fan_out_distribution: "..."
```

Each value must be a non-empty string.

## Semantic Rules

- glossary keys must exactly match the set of typology ids in `typology_rules.yaml`
- no missing typology ids
- no extra typology ids

This keeps SME-facing terminology synchronized with the actual rule engine.

Invalid glossary files should fail early during loading.
