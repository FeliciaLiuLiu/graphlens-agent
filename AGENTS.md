# Agent Guidance

This repo separates visual extraction from AFC interpretation.

- The model layer is adapter-based. The only supported backend is `pixtral` with local `mistral-community/pixtral-12b`, implemented by `Pixtral12BAdapter`.
- Every VLM backend may only extract visible graph facts from images.
- AFC typology mapping, scoring, and narratives must come from Python features, YAML skill files, and templates.
- Do not fine-tune visual models in this project.
- Do not add AFC knowledge to model folders.
- Put downloaded models under `./models/`; never commit model weights.
- Keep `numpy==1.26.4` and Python `>=3.11,<3.12`.
- Keep the PyTorch stack pinned together: `torch==2.8.0`, `torchvision==0.23.0`, `torchaudio==2.8.0`.
- Do not add `flash-attn` or `xformers` to the base requirements.
- Use cautious investigative language. Do not make criminal conclusions or SAR filing decisions.

## Ownership Model

This repo is organized into:

1. `Model`
2. `Skills`
3. `Harness`

### Model

- Model code lives in `src/afc_network_narrative/model/`.
- The current working model backend is local `mistral-community/pixtral-12b`.
- It is wrapped by `Pixtral12BAdapter`, which implements the generic `VLMAdapter` interface.
- It is used only for visible graph extraction.
- It is not fine-tuned here.
- Do not move AFC policy or typology knowledge into model assets.
- The stable model contract is: `image input -> VLMAdapter.extract_graph(...) -> GraphExtraction`.
- Skills and harness code must not consume raw model responses or model-specific output formats.

### Skills

`skills/` is the SME-owned layer.

Put the following kinds of changes in `skills/`:

- typology rules
- typology glossary text
- source descriptions
- scoring policy
- SAR/STR red flag review-signal policy
- investigation playbooks
- narrative policy
- narrative template text
- prohibited claims
- graph extraction prompt wording
- extraction schema contracts

Working rule:

- If an AFC SME should be able to change it without editing Python, it belongs in `skills/`.

### Harness

`src/afc_network_narrative/harness/` is the engineering-owned execution layer.

Put the following kinds of changes in the harness:

- new feature computation
- new motif detection logic
- new rule condition support
- new evidence field support
- new API behavior
- new input modality support
- orchestration changes
- validation changes
- retry, cache, or execution-flow changes

Working rule:

- If an engineer must change how the system executes, validates, computes, or orchestrates, it belongs in the harness.

## Change Policy

### Change Skills Only

Normally do not edit Python for:

- threshold changes
- wording changes
- scoring changes
- new investigation steps
- narrative copy changes
- glossary updates
- prohibited-claim updates

### Change Harness

Edit Python when:

- a skill asks for a capability the current contracts do not support
- a new computed feature is required
- a new rule condition or evidence type is required
- the API contract changes

### Change Model

Edit `src/afc_network_narrative/model/` when:

- a new VLM backend is required
- adapter selection logic changes
- model-specific request, response parsing, or local loading changes
- a backend dependency such as Transformers or Pixtral-specific loading code changes

## Contract Enforcement

SME-facing skill files are contract-validated by the harness at load time.

Do not bypass these checks.

Current contract-validated skill areas:

- `skills/graph_image_extraction/`
- `skills/afc_typology_mapping/`
- `skills/alert_investigation_boost/`
- `skills/narrative_generation/`

After changing either `skills/` or the harness, run:

```bash
python -m pytest
```

If a change is supposed to be SME-editable, prefer extending the skill contract instead of hardcoding a new default into Python.
