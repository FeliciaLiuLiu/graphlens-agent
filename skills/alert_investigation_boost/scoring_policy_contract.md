# Scoring Policy Skill Contract

This document defines the boundary between the alert investigation boost skill and the Python harness.

## Ownership Boundary

- SME-owned:
  - `scoring_policy.yaml`
  - typology point values
  - boost values
  - deduction values
  - supported role labels
  - priority bands
  - reason text templates
  - explanation template

- Engineering-owned:
  - score accumulation
  - typology match iteration
  - extraction-confidence comparison
  - band lookup execution
  - error handling

If an AFC SME should be able to change it without editing Python, it belongs in `scoring_policy.yaml`.

## Files

- Skill definition: `scoring_policy.yaml`
- Machine contract: `scoring_policy.schema.json`
- Skill description: `SKILL.md`

## Required Top-Level Keys

`scoring_policy.yaml` must define:

- `typology_points`
- `boosts`
- `supported_role_labels`
- `deductions`
- `repeated_amount_min_score`
- `distinct_counterparty_threshold`
- `low_confidence_threshold`
- `priority_bands`
- `reason_templates`
- `explanation_template`
- `empty_reason_codes_text`

## typology_points

Map of typology id to integer points.

The harness expects point values for every typology id that may be returned by the rule engine.

## boosts

Required keys:

- `repeated_amount`
- `distinct_counterparties`
- `supported_role_label`

All values must be integers.

## supported_role_labels

List of role labels that can support the label-based score boost.

The harness compares these strings case-insensitively against `role_hint_from_label`.

## deductions

Required keys:

- `low_extraction_confidence`

This value should normally be `0` or negative. Positive values are rejected by semantic validation.

## Threshold Fields

- `repeated_amount_min_score`: numeric
- `distinct_counterparty_threshold`: integer
- `low_confidence_threshold`: numeric

## priority_bands

Map of band name to two-integer inclusive bounds:

```yaml
priority_bands:
  Low: [0, 39]
  Medium: [40, 59]
  High: [60, 79]
  Critical: [80, 100]
```

Semantic rules:

- each band must contain exactly two integers
- lower bound must be less than or equal to upper bound
- bands must not overlap

## reason_templates

Required keys:

- `typology_match`
- `repeated_amount`
- `distinct_counterparties`
- `supported_role_label`
- `low_extraction_confidence`

Semantic rules:

- `typology_match` must contain `{typology_name}`

## explanation_template

The explanation template must contain:

- `{priority_band}`
- `{score}`
- `{reason_codes}`

## What the Harness Guarantees

When the policy passes contract validation, the harness will:

- score matched typologies
- apply configured boosts and deductions
- determine the priority band
- render reason text using the configured templates

## What the Skill Must Not Do

The skill must not:

- omit required keys
- rely on hidden Python defaults
- create overlapping priority bands
- use a positive deduction for `low_extraction_confidence`
- remove required explanation placeholders

Invalid policy files should fail early during loading.
