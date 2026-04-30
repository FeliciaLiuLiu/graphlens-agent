from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

from fastapi import FastAPI, File, HTTPException, UploadFile

from graphlens_agent.analytics import analyze_graph
from graphlens_agent.extraction import (
    LocalCVNotImplementedError,
    ProviderConfigurationError,
    get_screenshot_extraction_provider,
)
from graphlens_agent.narrative import generate_narrative
from graphlens_agent.schema import GraphDocument
from graphlens_agent.validator import GraphValidationError, validate_graph_document

ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}

app = FastAPI(
    title="GraphLens Agent API",
    version="0.1.0",
    description="API for validating graph JSON, analyzing graphs, and screenshot extraction.",
)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze-graph")
def analyze_graph_endpoint(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        document = validate_graph_document(payload)
    except GraphValidationError as error:
        raise HTTPException(status_code=422, detail=_validation_error_detail(error)) from error

    return analyze_graph(document)


@app.post("/explain-graph")
def explain_graph_endpoint(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        document = validate_graph_document(payload)
    except GraphValidationError as error:
        raise HTTPException(status_code=422, detail=_validation_error_detail(error)) from error

    analytics = analyze_graph(document)
    narrative = generate_narrative(document, analytics)
    return {
        "analytics": analytics,
        "narrative": narrative,
    }


@app.post("/extract-graph")
async def extract_graph_endpoint(file: UploadFile = File(...)) -> Dict[str, Any]:
    _provider_used, document = await _extract_graph_from_upload(file)
    return document.to_dict()


@app.post("/pipeline/screenshot-to-narrative")
async def screenshot_to_narrative_pipeline_endpoint(file: UploadFile = File(...)) -> Dict[str, Any]:
    provider_used, document = await _extract_graph_from_upload(file)
    graph = document.to_dict()
    analytics = analyze_graph(document)
    narrative = generate_narrative(document, analytics)
    return {
        "graph": graph,
        "analytics": analytics,
        "narrative": narrative,
        "warnings": graph["warnings"],
        "provider_used": provider_used,
    }


async def _extract_graph_from_upload(file: UploadFile) -> Tuple[str, GraphDocument]:
    filename = file.filename or ""
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Upload a png, jpg, or jpeg image.",
        )

    content = await file.read()
    try:
        provider = get_screenshot_extraction_provider()
        provider_used = provider.__class__.__name__
        document = provider.extract(
            filename=file.filename,
            content_type=file.content_type,
            content=content,
        )
    except ProviderConfigurationError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except LocalCVNotImplementedError as error:
        raise HTTPException(status_code=501, detail=str(error)) from error
    except GraphValidationError as error:
        raise HTTPException(status_code=422, detail=_validation_error_detail(error)) from error

    return provider_used, document


def _validation_error_detail(error: GraphValidationError) -> list[Dict[str, str]]:
    return [
        {
            "path": issue.path,
            "message": issue.message,
        }
        for issue in error.issues
    ]
