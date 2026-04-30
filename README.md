# GraphLens Agent

GraphLens Agent is a backend proof of concept for converting graph-shaped data into validated graph JSON and deterministic graph analytics.

The project is intentionally company-safe:

- It uses synthetic sample data only.
- It does not require external model APIs.
- It does not require external API keys.
- It does not call OpenAI, Gemini, Anthropic, or any other hosted vision or language model.
- Structured graph JSON is the preferred source of truth.
- Screenshot extraction is a fallback path for demos and future local computer-vision work.

## Purpose

Graph analytics and graph model outputs can be difficult for non-technical users to inspect. A graph may include nodes, edges, directions, labels, amounts, confidence scores, and risk-like patterns, but the structure often needs to be normalized before it can be analyzed or explained.

GraphLens Agent focuses on the backend foundation:

1. Accept structured graph JSON.
2. Validate nodes, edges, metadata, confidence scores, and warnings.
3. Run deterministic graph analytics with NetworkX.
4. Detect graph patterns such as fan-in, fan-out, hub-and-spoke, chain, cycle, and collector behavior.
5. Generate rule-based plain-language narratives from analytics evidence.
6. Provide a screenshot upload endpoint as a fallback extraction path.

Frontend UI is not implemented yet.

## Example Use Case

The bundled sample uses synthetic account-like nodes and synthetic transfer-like edges. It shows several source nodes pointing into one central node.

GraphLens Agent can identify:

- Multiple source nodes.
- One shared target node.
- A collector-style central node.
- Repeated or similar edge amounts.
- A fan-in aggregation pattern.

This does not make any real-world claim. It is a synthetic analytics demo.

## Backend Layers

1. **Graph Data Model**
   - Normalizes graph data into a consistent JSON schema.
   - Stores nodes, edges, graph metadata, confidence scores, positions, and warnings.

2. **Validation**
   - Rejects malformed graph JSON.
   - Verifies edge endpoints reference known nodes.
   - Preserves warnings for low-confidence extraction.

3. **Graph Analytics**
   - Computes in-degree, out-degree, central node, inbound amount, repeated amount patterns, collector behavior, and graph motif.

4. **Rule-Based Narrative Generation**
   - Converts analytics output into plain-language sections.
   - Uses deterministic templates and graph facts only.
   - Does not use an LLM or external model API.

5. **Screenshot Extraction Fallback**
   - `mock` provider returns bundled synthetic sample graph JSON.
   - `local_cv` provider is a planned local OCR/OpenCV extraction path and currently returns HTTP 501.
   - No external model API is used.

## Current Backend Scope

The current backend includes:

- Graph JSON data model
- JSON Schema artifact
- Graph JSON validator
- Deterministic graph analytics
- CLI analytics command
- FastAPI `/health`
- FastAPI `/analyze-graph`
- FastAPI `/explain-graph`
- FastAPI `/extract-graph`
- Rule-based narrative generation
- Mock screenshot extraction provider
- Planned `local_cv` provider skeleton
- Synthetic sample graph JSON
- Automated tests

## Project Structure

```text
graphlens-agent/
├── samples/
│   ├── fan_in_collector.json
│   └── fan_in_graph.png
├── schemas/
│   └── graph.schema.json
├── src/
│   └── graphlens_agent/
│       ├── analytics.py
│       ├── api.py
│       ├── cli.py
│       ├── extraction.py
│       ├── io.py
│       ├── narrative.py
│       ├── schema.py
│       └── validator.py
├── tests/
│   ├── test_api.py
│   ├── test_extraction.py
│   ├── test_narrative.py
│   └── test_phase1.py
├── .env.example
├── pyproject.toml
└── README.md
```

## Run Tests

```bash
python -m pytest -q
```

## Run CLI

```bash
PYTHONPATH=src python -m graphlens_agent.cli samples/fan_in_collector.json
```

## Run API

```bash
PYTHONPATH=src uvicorn graphlens_agent.api:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Analyze graph JSON:

```bash
curl -X POST http://127.0.0.1:8000/analyze-graph \
  -H "Content-Type: application/json" \
  --data @samples/fan_in_collector.json
```

Explain graph JSON with analytics and a rule-based narrative:

```bash
curl -X POST http://127.0.0.1:8000/explain-graph \
  -H "Content-Type: application/json" \
  --data @samples/fan_in_collector.json
```

Extract graph JSON from an uploaded image in mock mode:

```bash
curl -X POST http://127.0.0.1:8000/extract-graph \
  -F "file=@samples/fan_in_graph.png"
```

## Extraction Provider Configuration

`POST /extract-graph` selects an extraction provider with `GRAPH_EXTRACTION_PROVIDER`.

Allowed values:

- `mock`
- `local_cv`

Mock mode is the default portfolio-demo mode. It does not inspect the uploaded image; it returns the bundled synthetic sample graph JSON with a warning.

```bash
GRAPH_EXTRACTION_PROVIDER=mock \
PYTHONPATH=src uvicorn graphlens_agent.api:app --reload
```

`local_cv` mode is reserved for future local OCR/OpenCV screenshot extraction. It is intentionally not implemented yet and returns HTTP 501.

```bash
GRAPH_EXTRACTION_PROVIDER=local_cv \
PYTHONPATH=src uvicorn graphlens_agent.api:app --reload
```

`.env.example` contains only:

```bash
GRAPH_EXTRACTION_PROVIDER=mock
```

No external API keys are needed.

## Rule-Based Narrative Design

`POST /explain-graph` validates graph JSON, runs deterministic analytics, and returns both analytics and narrative sections.

Narrative sections:

- Plain-Language Summary
- What Is Happening
- Why This Pattern Matters
- Evidence From the Graph
- Suggested Next Review Steps
- Caveats

Currently supported motif narratives:

- `fan_in_aggregation`
- `fan_out_distribution`
- `unknown`

The narrative layer uses rules, analytics output, graph labels, graph metrics, evidence lines, and validation warnings. It does not call an LLM or any external model API.

## Screenshot Extraction Notes

Structured graph JSON should be used whenever available. It is the most reliable input for validation and analytics.

Screenshot extraction is a fallback workflow. Even when local OCR/OpenCV extraction is added later, extracted graph JSON should be treated as a draft that may require human validation, especially when labels, arrows, edge values, or node positions are unclear.
