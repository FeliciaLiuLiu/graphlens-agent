# GraphLens Agent

GraphLens Agent is an agentic AI proof of concept that converts graph screenshots into structured graph JSON, runs graph analytics, and generates evidence-backed narratives that non-technical users can understand.

The goal of this project is to help analysts, investigators, product teams, and business stakeholders understand graph-based model outputs without requiring deep knowledge of graph neural networks, graph analytics, or network visualization.

## 1. Project Purpose

Many graph analytics and GNN-based systems produce outputs that are difficult for non-technical users to interpret. A graph screenshot may show nodes, edges, arrows, labels, and risk patterns, but the business meaning is often unclear.

GraphLens Agent addresses this gap by building an AI agent that can:

1. Read a graph screenshot.
2. Extract nodes, edges, labels, directions, and edge values.
3. Convert the screenshot into a structured JSON representation.
4. Run graph analytics on the extracted structure.
5. Detect graph patterns such as fan-in, fan-out, hub-and-spoke, chain, cycle, and collector behavior.
6. Generate plain-language narratives backed by graph evidence.
7. Provide warnings when the extraction is uncertain.

The system is designed as a company-usable POC, not just a chatbot demo.

## 2. Example Use Case

A user uploads a graph screenshot showing multiple accounts sending money into one central account.

GraphLens Agent should extract the graph structure and identify that:

- There are multiple source accounts.
- They all send funds to the same target account.
- The target account acts like a collector.
- The transaction amounts are similar or repeated.
- The overall graph pattern is a fan-in aggregation pattern.

The agent then generates a narrative such as:

> This graph shows several accounts sending similar amounts into one central account. The central account appears to act as a collection point. The key signal is not one individual transfer, but the overall structure: multiple sources, one shared destination, and repeated transaction amounts. This pattern may be worth reviewing in a risk or AML workflow, although it does not prove wrongdoing by itself.

## 3. Core Concept

The project separates graph understanding into four layers:

1. **Visual Extraction**
   - Converts a graph screenshot into structured data.
   - Extracts visible nodes, node labels, edges, arrows, edge labels, and approximate positions.

2. **Graph Data Model**
   - Normalizes the extracted information into a consistent JSON schema.
   - Stores nodes, edges, graph metadata, confidence scores, and warnings.

3. **Graph Analytics**
   - Runs deterministic algorithms using graph libraries.
   - Computes metrics such as in-degree, out-degree, central node, total inbound amount, repeated amount pattern, and graph motif.

4. **Narrative Generation**
   - Uses an LLM-based agent to convert graph facts into human-readable explanations.
   - Ensures the narrative is grounded in extracted graph evidence.

## 4. Target Users

This POC is designed for:

- Non-technical business stakeholders
- Risk analysts
- Fraud analysts
- AML investigators
- Product managers
- Model governance teams
- Data science teams explaining GNN outputs
- Engineering teams building AI-assisted analytics tools

## 5. MVP Scope

The first version focuses on a simple but useful workflow:

```text
Graph Screenshot
      ↓
Screenshot-to-Graph Extraction
      ↓
Graph JSON
      ↓
Graph Analytics
      ↓
Plain-Language Narrative
```

## Phase 1 Backend Scope

Phase 1 covers backend-only functionality:

- Graph JSON data model
- JSON Schema artifact
- Graph JSON validator
- Deterministic graph analytics
- Sample graph JSON
- Automated tests
- Mock screenshot-to-graph extraction endpoint

Frontend work is intentionally out of scope for Phase 1.

## Project Structure

```text
graphlens-agent/
├── samples/
│   └── fan_in_collector.json
├── schemas/
│   └── graph.schema.json
├── src/
│   └── graphlens_agent/
│       ├── analytics.py
│       ├── api.py
│       ├── cli.py
│       ├── extraction.py
│       ├── io.py
│       ├── schema.py
│       └── validator.py
├── tests/
│   ├── test_api.py
│   └── test_phase1.py
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

Extract graph JSON from an uploaded image:

```bash
curl -X POST http://127.0.0.1:8000/extract-graph \
  -F "file=@path/to/graph.png"
```

The Phase 2A extraction endpoint uses a mock provider and returns the bundled sample graph JSON with a warning. Real computer vision, OCR, and model calls are not implemented yet.
