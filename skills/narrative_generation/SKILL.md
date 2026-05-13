# Narrative Generation Skill

Narrative must include:
- Network observation
- AFC typology hypothesis
- Alert investigation boost
- Key entities and money-flow evidence
- Recommended investigation steps
- Limitations and missing context

Use cautious language such as “potential”, “consistent with”, “may indicate”, and “warrants review”.

Contract:
- human-readable contract: `narrative_policy_contract.md`
- machine-readable contract: `narrative_policy.schema.json`
- prohibited claims contract: `prohibited_claims_contract.md`
- prohibited claims machine-readable contract: `prohibited_claims.schema.json`

The harness validates `narrative_policy.yaml`, `prohibited_claims.yaml`, and required `narrative_template.md` placeholders before narrative rendering.
