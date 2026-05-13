# SAR Red Flags Skill Contract

This skill defines SAR/STR red flag review signals that can be supported by graph structure.

It does not define SAR filing decisions. The harness must keep the final decision value as
`not_determined_by_system`.

## Top-level fields

- `decision_boundary`: required object that states the filing decision boundary.
- `red_flags`: required list of graph-supported red flag review signals.
- `context_required_red_flags`: required list of red flags that require non-graph context and must not be matched from topology alone.

## `decision_boundary`

Required fields:

- `decision_value`: must be `not_determined_by_system`.
- `summary`: plain-language boundary text.
- `matched_signal_status`: status used when a graph-supported signal matched.
- `context_only_status`: status used when a red flag requires unavailable context.

## `red_flags`

Each item must include:

- `id`: stable snake_case identifier.
- `name`: SME-readable display name.
- `description`: what the red flag means.
- `related_typologies`: typology ids from `skills/afc_typology_mapping/typology_rules.yaml`.
- `source_registry_ids`: ids from `skills/afc_typology_mapping/source_registry.yaml`.
- `review_question`: the analyst question raised by this signal.
- `matched_text`: cautious sentence used when the signal matches.
- `caution`: boundary language.
- `recommended_checks`: next checks for analyst review.
- `requires_context`: context needed before escalation or SAR/STR consideration.

## `context_required_red_flags`

Use this section for public red flags that cannot be detected from graph topology alone.

Examples:

- transactions inconsistent with customer profile
- no apparent lawful purpose
- missing originator or beneficiary information
- sanctions, terrorist financing, human trafficking, or structuring concerns

The harness may list these as missing-context review areas, but must not mark them as graph-supported matches.
