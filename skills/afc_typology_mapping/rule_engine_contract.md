# Rule Engine Skill Contract

This document defines the boundary between the AFC typology skill and the Python harness.

## Ownership Boundary

- SME-owned:
  - `typology_rules.yaml`
  - AFC typology names
  - AFC interpretation text
  - caution text
  - investigation boost text
  - motif thresholds
  - confidence policy parameters
  - missing-context limitation text
  - evidence field selection per typology

- Engineering-owned:
  - YAML loading
  - schema validation
  - graph validation
  - feature computation
  - motif detection execution
  - rule matching execution
  - confidence arithmetic execution
  - error handling

If an AFC SME should be able to change it without editing Python, it belongs in `typology_rules.yaml`.

## Files

- Skill definition: `typology_rules.yaml`
- Machine contract: `typology_rules.schema.json`
- Skill description: `SKILL.md`

## Top-Level YAML Contract

`typology_rules.yaml` must define:

- `version`
- `role_hint_tokens`
- `motif_detection_policy`
- `confidence_policy`
- `context_limitations`
- `typologies`

## role_hint_tokens

Array of lowercase or mixed-case strings. These tokens are matched case-insensitively against visible node labels to populate `role_hint_from_label` when the extractor does not provide it directly.

Example:

```yaml
role_hint_tokens:
  - mule
  - collector
  - distributor
  - relay
```

## motif_detection_policy.thresholds

These parameters control how the harness computes motifs from validated graph structure.

Required fields:

- `fan_in`
- `fan_out`
- `inbound_hub`
- `outbound_hub`
- `pass_through_in_degree`
- `pass_through_out_degree`
- `max_cycle_length`
- `bipartite_min_sources`
- `bipartite_min_targets`
- `bipartite_min_edges`

All values must be integers.

## confidence_policy

These parameters control the match-confidence formula used by the harness.

Required fields:

- `min_confidence`
- `max_confidence`
- `node_degree_weight`
- `node_degree_cap`
- `repeated_amount_weight`
- `repeated_amount_cap`

All values must be numeric.

## context_limitations

This is the skill-owned text for missing-context limitations. The keys must match the harness flags exactly:

- `timestamps_absent`
- `customer_profile_absent`
- `kyc_device_ip_absent`
- `geography_absent`
- `channel_absent`
- `customer_baseline_absent`

All values must be strings.

## typologies

Each typology rule must define:

- `id`
- `name`
- `match_scope`
- `base_confidence`
- `conditions`
- `afc_interpretation`
- `caution`
- `evidence_fields`
- `investigation_boost`

Optional:

- `limitations`

Typology IDs must be unique.

## match_scope

Supported values:

- `node`
- `graph`

### node scope

Use `node` when the typology attaches to one or more specific nodes selected by a motif list.

Supported condition keys:

- `motif`
- `min_in_degree`
- `min_out_degree`

Required:

- `motif`

Supported motif names:

- `fan_in`
- `fan_out`
- `inbound_hub`
- `outbound_hub`
- `pass_through_relay`

### graph scope

Use `graph` when the typology attaches to the overall graph rather than a single node.

Supported graph condition patterns:

1. Required motif presence

```yaml
conditions:
  required_motifs:
    fan_out: 1
    fan_in: 1
```

2. Graph motif count

```yaml
conditions:
  motif: cycle_or_circular_flow
  min_count: 1
```

Supported graph motif names:

- `cycle_or_circular_flow`
- `bipartite_many_to_many`
- `fan_in`
- `fan_out`
- `inbound_hub`
- `outbound_hub`
- `pass_through_relay`
- `two_hop_paths`

3. Graph metric threshold

```yaml
conditions:
  metric: repeated_amount_score
  min_value: 0.8
```

Supported graph metric names:

- `repeated_amount_score`
- `repeated_amount_value`

## evidence_fields

The harness only supports these evidence fields:

- `in_degree`
- `out_degree`
- `weighted_inbound_amount`
- `weighted_outbound_amount`
- `weighted_flow_amount`
- `repeated_amount_score`
- `repeated_amount_value`
- `fan_out_nodes`
- `fan_in_nodes`
- `cycle_count`
- `many_to_many_groups`

Node-scoped evidence fields:

- `in_degree`
- `out_degree`
- `weighted_inbound_amount`
- `weighted_outbound_amount`
- `weighted_flow_amount`
- `repeated_amount_score`
- `repeated_amount_value`

Graph-scoped evidence fields:

- `repeated_amount_score`
- `repeated_amount_value`
- `fan_out_nodes`
- `fan_in_nodes`
- `cycle_count`
- `many_to_many_groups`

## What the Harness Guarantees

When the skill file passes contract validation, the harness will:

- load the YAML
- validate it against the machine schema
- apply semantic validation
- compute deterministic graph features
- match rules in a stable order
- build grounded evidence objects
- compute confidence using skill-defined parameters

## What the Skill Must Not Do

The skill must not:

- declare unsupported `match_scope` values
- use unsupported motifs
- use unsupported metrics
- use unsupported evidence fields
- omit required condition keys for the selected scope
- assume the harness will infer missing keys

The harness is intentionally strict. Missing contract fields should fail early rather than silently falling back to Python defaults.
