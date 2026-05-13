# Alert Investigation Boost Skill

Purpose: convert matched typology hypotheses and extraction quality into an investigation priority score.

The score is an alert triage aid only. It is not a SAR filing decision and not a final suspicious activity conclusion.

Contract:
- human-readable contract: `scoring_policy_contract.md`
- machine-readable contract: `scoring_policy.schema.json`
- playbook contract: `investigation_playbooks_contract.md`
- playbook machine-readable contract: `investigation_playbooks.schema.json`

The harness validates `scoring_policy.yaml` against the contract before scoring.
The harness validates `investigation_playbooks.yaml` against the contract before building recommended investigation steps.
