# AFC Typology Mapping Skill

Purpose: map deterministic graph features into cautious AFC typology hypotheses.

Use only:
- validated graph facts,
- deterministic graph features,
- `typology_rules.yaml`,
- limitations and evidence listed by the rule engine.

Contract:
- human-readable contract: `rule_engine_contract.md`
- machine-readable contract: `typology_rules.schema.json`
- glossary contract: `typology_glossary_contract.md`
- glossary machine-readable contract: `typology_glossary.schema.json`
- source registry contract: `source_registry_contract.md`
- source registry machine-readable contract: `source_registry.schema.json`

The harness validates `typology_rules.yaml`, `typology_glossary.yaml`, and `source_registry.yaml` against their contracts before rule execution.

Do not output final suspicious activity conclusions.
Do not infer sanctions, terrorist financing, human trafficking, or structuring without explicit supporting context.
