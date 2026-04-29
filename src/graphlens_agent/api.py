from __future__ import annotations

from typing import Any, Dict

from fastapi import FastAPI, HTTPException

from graphlens_agent.analytics import analyze_graph
from graphlens_agent.validator import GraphValidationError, validate_graph_document


app = FastAPI(
    title="GraphLens Agent API",
    version="0.1.0",
    description="Phase 1 API for validating graph JSON and returning deterministic graph analytics.",
)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze-graph")
def analyze_graph_endpoint(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        document = validate_graph_document(payload)
    except GraphValidationError as error:
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "path": issue.path,
                    "message": issue.message,
                }
                for issue in error.issues
            ],
        ) from error

    return analyze_graph(document)
