# afc-network-narrative

Local Python 3.11 system for AFC network graph narrative support.

## Architecture

The system is intentionally organized into three layers:

1. `Model`
2. `Skills`
3. `Harness`

### Model

Path: `src/afc_network_narrative/model/`

The model layer is responsible only for visual extraction. It takes a network graph image as input and returns a normalized `GraphExtraction` object containing visible graph facts such as nodes, directed edges, labels, amounts, colors, and extraction confidence.

This layer is adapter-based. The rest of the system talks only to the generic `VLMAdapter` interface:

```text
image input -> VLMAdapter.extract_graph(...) -> GraphExtraction
```

Current working backends:

- `ollama`: local Ollama `qwen2.5vl:3b` through `OllamaVLMAdapter`; this is the default backend
- `qwen`: local `Qwen2.5-VL-7B-Instruct` through `QwenVLAdapter`
- `florence2`: local `microsoft/Florence-2-base-ft` through `Florence2Adapter`

Future backend names reserved by the adapter factory:

- `approved_endpoint`
- `llama`
- `gemini`
- `openai`
- `claude`
- `granite`

All model adapters must return the same validated `GraphExtraction` contract. Model-specific imports, prompts, request formats, response parsing, and model-loading logic must stay inside the adapter implementation.

The model layer must not perform AFC interpretation, AML judgment, typology classification, alert scoring, or narrative generation.

### Skills

Path: `skills/`

The skills layer contains SME-owned AFC domain knowledge and policy. It stores typology rules, SAR/STR red flag review signals, motif thresholds, scoring policy, investigation playbooks, narrative templates, prohibited claims, glossary definitions, and contract files.

This layer is intentionally non-executable. It exists so that AFC subject matter experts can update domain logic, policy wording, thresholds, and narrative behavior without changing Python code.

Typical skill content includes:

- graph extraction prompt and extraction schema contracts
- typology rules
- typology glossary
- source registry
- scoring policy
- SAR/STR red flag review-signal policy
- investigation playbooks
- narrative policy
- narrative template
- prohibited claims

Working rule:

- If an AFC SME should be able to change it without editing Python, it belongs in `skills/`.

### Harness

Path: `src/afc_network_narrative/harness/`

The harness layer is the engineering-owned execution and orchestration layer. It connects model output to AFC skills and produces the final constrained output.

The harness is responsible for:

- adapter selection and pipeline orchestration
- skill loading
- skill contract validation
- graph validation
- deterministic feature computation
- motif detection
- rule execution
- scoring execution
- narrative rendering
- API orchestration
- error handling

Working rule:

- If an engineer must change how the system executes, validates, computes, or orchestrates, the change belongs in the harness.

### Harness Subfolders

- `harness/app/`: Handles input, selects the adapter, and starts the full pipeline.
- `harness/schemas/`: Defines and validates `GraphExtraction` and the final output schema.
- `harness/features/`: Turns the graph into computed features and detected motifs.
- `harness/rules/`: Reads `skills/afc_typology_mapping/` and `skills/alert_investigation_boost/`, then performs typology matching and scoring.
- `harness/narrative/`: Reads `skills/narrative_generation/` and the investigation playbooks, generates the narrative, and checks prohibited claims.
- `harness/reporting/`: Writes the results into a PDF report.
- `harness/evaluation/`: Runs golden-set evaluation and is not part of the main online pipeline.

### Stable System Contract

```text
image input
-> VLMAdapter.extract_graph(...)
-> GraphExtraction
-> harness validation and feature computation
-> skills-driven AFC interpretation
-> AFCNarrativeOutput
```

This contract is the key architectural boundary in the project. The model layer produces structured graph facts. The skills layer defines AFC knowledge. The harness layer applies that knowledge to the extracted graph in a controlled and testable way.

`AFCNarrativeOutput` includes:

- `graph_summary`
- `detected_typologies`
- `alert_boost`
- `sar_red_flags`
- `recommended_investigation_steps`
- `narrative`
- `limitations`
- `evidence`

The human-readable narrative is structured to answer:

- whether the graph is an alert-review candidate
- which AFC pattern hypotheses matched
- what those graph patterns may mean in AFC terms
- why the graph should be reviewed
- which SAR/STR red flag review signals are graph-supported
- what the analyst should check next

### Compliance Boundary

The system is designed as an investigation-support tool, not a final decision engine. It may produce cautious typology hypotheses, alert-investigation priority, and graph-supported SAR/STR red flag review signals, but it must not make criminal conclusions or SAR filing decisions.

## Repository Layout

```text
src/afc_network_narrative/
  model/       # Model layer: VLMAdapter, backend factory, Ollama/Qwen/Florence adapters.
  harness/     # Harness engineering: API, pipeline, schemas, features, rules, narrative, reporting, evaluation.
skills/        # Skills layer: AFC rules, policies, prompts, playbooks, templates, and contracts.
scripts/       # CLI utilities for downloads, image analysis, graph JSON analysis, and smoke tests.
tests/         # Unit tests for model adapters, harness behavior, skill contracts, and narratives.
```

## Pipeline

1. Select a VLM backend through `create_vlm_adapter(...)`.
2. Input a network graph image.
3. The selected adapter extracts visible graph facts and returns `GraphExtraction`.
4. Python validator checks the graph JSON.
5. Python feature builder computes fan-in, fan-out, hubs, pass-through motifs, cycles, many-to-many structure, and repeated amounts.
6. AFC skills and YAML rules map features to cautious typology hypotheses.
7. Alert investigation boost skill assigns priority.
8. Narrative skill outputs a grounded AFC investigation narrative.

The visual model is not fine-tuned and is not used for AFC interpretation. It only extracts visible graph facts. Everything after `GraphExtraction` is model-independent.

## Change Guide

Use this decision rule before editing the repo:

- Change `src/afc_network_narrative/model/` when the change is about VLM backend selection, model-specific request/response handling, local model loading, or image-to-`GraphExtraction` normalization.
- Change `skills/` when the change is about AFC knowledge, policy, wording, thresholds, scoring policy, or narrative style.
- Change the harness when the change requires new computation, new execution behavior, new API behavior, or new rule-engine capability.

### Change Model

These changes belong in `src/afc_network_narrative/model/`:

- add a new VLM backend
- change adapter selection logic
- change an adapter prompt transport or request format
- parse a model-specific raw response
- normalize model output into `GraphExtraction`
- isolate model-specific dependencies such as Ollama, Transformers, Qwen utilities, or future endpoint clients

### Change Skills Only

These changes should normally not require Python edits:

- update typology wording
- adjust fan-in or fan-out thresholds
- change confidence parameters
- update scoring points or priority bands
- add or revise investigation steps
- change narrative wording or layout text
- add prohibited claims
- update glossary definitions
- update source descriptions
- revise graph extraction prompt wording

### Change Harness

These changes usually require Python edits:

- add a new graph feature
- add a new motif detector
- add a new rule condition type not currently supported by the contract
- add a new evidence field not currently supported by the rule engine
- support a new input type such as PDF, multi-image, or video
- change API request or response contracts
- change validation flow, retries, caching, or async execution

### Practical Test

Ask this question:

- If the change is about how a visual model is called or normalized, the change belongs in `model/`.
- If an AFC SME should be able to make the change without editing Python, the change belongs in `skills/`.

If neither is true and the change affects execution, validation, computation, output generation, or tests, the change belongs in `harness/`.

## Skill Contracts

Core SME-facing skill files are contract-validated by the harness at load time.

That means:

- invalid YAML structure fails early
- missing required placeholders fail early
- unknown typology keys fail early
- missing required source ids fail early
- prohibited-claims regressions fail early

Contract validation currently covers:

- `skills/graph_image_extraction/`
- `skills/afc_typology_mapping/`
- `skills/alert_investigation_boost/`
- `skills/narrative_generation/`

Run tests after any skill or harness change:

```bash
python -m pytest
```

## Requirements

- Python `>=3.11,<3.12`
- `numpy==1.26.4`
- Local deployment
- VLM backend selected by `VLM_BACKEND`
- Ollama `qwen2.5vl:3b` pulled locally for the default `ollama` backend
- Qwen2.5-VL-7B model files under `./models/` for the `qwen` backend
- Florence-2 model files under `./models/` for the lightweight CPU-oriented `florence2` backend

For the current Qwen backend, Torch must be installed as one compatible PyTorch 2.8.0 stack:

- `torch==2.8.0`
- `torchvision==0.23.0`
- `torchaudio==2.8.0`

Pick exactly one torch requirements file for your local CUDA or CPU setup. Do not add `flash-attn` or `xformers` to the base requirements.

## Setup

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

For Qwen2.5-VL-7B, install exactly one torch requirements file before `requirements.txt`. Use `requirements-torch-cu128.txt` for CUDA 12.8, `requirements-torch-cu126.txt` for CUDA 12.6, or `requirements-torch-cpu.txt` for CPU.

Florence-2 also requires a local PyTorch installation, plus the base packages `transformers`, `pillow`, `timm`, and `einops`. The adapter loads the model locally with `trust_remote_code=True`, so company environments should approve the model artifact before use.

On Intel macOS, PyTorch 2.8.0 CPU wheels are not available for native `osx-64` Python. Use the Linux CPU Docker path instead:

```bash
docker compose -f docker-compose.cpu.yml build
docker compose -f docker-compose.cpu.yml run --rm afc-network-narrative python scripts/check_torch_stack.py
docker compose -f docker-compose.cpu.yml run --rm afc-network-narrative python -m pytest
```

## Download Models

### Default backend: Ollama qwen2.5vl:3b

Install Ollama separately if it is not already installed, then pull the model:

```bash
python scripts/download_ollama_model.py --model qwen2.5vl:3b
```

The Ollama adapter uses the local Ollama service at `http://127.0.0.1:11434` by default. It does not send AFC interpretation to the model; it only asks for visible graph extraction JSON.

### Optional backend: Qwen2.5-VL-7B

Do not commit downloaded model files. `./models/` is ignored by git.

```bash
python scripts/download_qwen.py \
  --model-id Qwen/Qwen2.5-VL-7B-Instruct \
  --local-dir ./models/Qwen2.5-VL-7B-Instruct
```

### Lightweight CPU-oriented backend: Florence-2

```bash
python scripts/download_florence.py \
  --model-id microsoft/Florence-2-base-ft \
  --local-dir ./models/Florence-2-base-ft
```

## Run the Project

This project supports both CLI and API execution.

Use these paths in the examples below:

- input image: `image/testimage1.png`
- output JSON: `output/report.json`
- output PDF: `output/report.pdf`

Create the output folder first:

```bash
mkdir -p output
```

### Run via CLI

Run the full pipeline from the command line and generate both JSON and PDF in one command. This uses the configured VLM backend. By default, `VLM_BACKEND=ollama` and `OLLAMA_MODEL=qwen2.5vl:3b`:

```bash
python scripts/analyze_image.py image/testimage1.png \
  --pretty \
  --json-out output/report.json \
  --pdf-out output/report.pdf
```

Select Ollama explicitly:

```bash
python scripts/analyze_image.py image/testimage1.png \
  --backend ollama \
  --ollama-model qwen2.5vl:3b \
  --pretty \
  --json-out output/report.json \
  --pdf-out output/report.pdf
```

Select Qwen explicitly:

```bash
python scripts/analyze_image.py image/testimage1.png \
  --backend qwen \
  --qwen-model-path ./models/Qwen2.5-VL-7B-Instruct \
  --pretty \
  --json-out output/report.json \
  --pdf-out output/report.pdf
```

Select Florence-2 explicitly:

```bash
python scripts/analyze_image.py image/testimage1.png \
  --backend florence2 \
  --florence-model-path ./models/Florence-2-base-ft \
  --pretty \
  --json-out output/report.json \
  --pdf-out output/report.pdf
```

If you want to test the AFC pipeline without calling any VLM, run the JSON entrypoint instead:

```bash
python scripts/analyze_graph_json.py image/testimage1.graph.json \
  --pretty \
  --json-out output/report.json \
  --pdf-out output/report.pdf
```

### Run via API

Start the API server:

```bash
uvicorn afc_network_narrative.harness.app.main:app --host 127.0.0.1 --port 8000
```

Write the JSON result to `output/report.json`:

```bash
curl -s -X POST http://127.0.0.1:8000/analyze-image \
  -F "image=@image/testimage1.png" \
  -o output/report.json
```

Write the PDF report to `output/report.pdf`:

```bash
curl -s -X POST http://127.0.0.1:8000/analyze-image-report \
  -F "image=@image/testimage1.png" \
  -o output/report.pdf
```

The API uses two endpoints because JSON and PDF are different response types:

- `POST /analyze-image` returns JSON
- `POST /analyze-image-report` returns PDF

Select Qwen explicitly through query parameters:

```bash
curl -s -X POST "http://127.0.0.1:8000/analyze-image?backend=qwen&qwen_model_path=./models/Qwen2.5-VL-7B-Instruct" \
  -F "image=@image/testimage1.png" \
  -o output/report.json
```

Select Ollama explicitly through query parameters:

```bash
curl -s -X POST "http://127.0.0.1:8000/analyze-image?backend=ollama&ollama_model=qwen2.5vl:3b" \
  -F "image=@image/testimage1.png" \
  -o output/report.json
```

Select Florence-2 explicitly through query parameters:

```bash
curl -s -X POST "http://127.0.0.1:8000/analyze-image?backend=florence2&florence_model_path=./models/Florence-2-base-ft" \
  -F "image=@image/testimage1.png" \
  -o output/report.json
```

You can also test the non-VLM API path with pre-extracted graph JSON:

```bash
curl -s -X POST http://127.0.0.1:8000/analyze-graph-json \
  -H "Content-Type: application/json" \
  -d @image/testimage1.graph.json \
  -o output/report.json
```

```bash
curl -s -X POST http://127.0.0.1:8000/analyze-graph-json-report \
  -H "Content-Type: application/json" \
  -d @image/testimage1.graph.json \
  -o output/report.pdf
```

Set model environment variables if needed:

```bash
export VLM_BACKEND=ollama
export OLLAMA_MODEL=qwen2.5vl:3b
export OLLAMA_HOST=http://127.0.0.1:11434
export OLLAMA_TIMEOUT_SECONDS=600
export QWEN_MODEL_PATH=./models/Qwen2.5-VL-7B-Instruct
export FLORENCE_MODEL_PATH=./models/Florence-2-base-ft
export GRAPH_EXTRACTION_PROMPT_PATH=./skills/graph_image_extraction/extraction_prompt.md
export VLM_MAX_NEW_TOKENS=2048
export APPROVED_VLM_ENDPOINT_URL=
export VLM_ENDPOINT_URL=
export VLM_API_KEY_ENV=
```

## Safety Boundaries

- Never state that a person committed money laundering.
- Never make a SAR filing decision.
- Never infer sanctions, terrorist financing, human trafficking, or structuring without explicit supporting context.
- Use cautious language such as “potential”, “consistent with”, “may indicate”, and “warrants review”.
- Do not treat color as risk unless a configured legend defines it.

## Maintainer Summary

This repo is not designed around a fine-tuned AFC model.

It is designed around:

- an adapter-based visual model layer for extraction only
- SME-owned skills for AFC knowledge
- a stable harness for execution

Keep that boundary intact.
