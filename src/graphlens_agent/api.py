from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, File, HTTPException, UploadFile

from graphlens_agent.analytics import analyze_graph
from graphlens_agent.extraction import MockScreenshotExtractionProvider, ScreenshotExtractionProvider
from graphlens_agent.validator import GraphValidationError, validate_graph_document

ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
screenshot_extraction_provider: ScreenshotExtractionProvider = MockScreenshotExtractionProvider()

app = FastAPI(
    title="GraphLens Agent API",
    version="0.1.0",
    description="API for validating graph JSON, analyzing graphs, and mock screenshot extraction.",
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


@app.post("/extract-graph")
async def extract_graph_endpoint(file: UploadFile = File(...)) -> Dict[str, Any]:
    filename = file.filename or ""
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Upload a png, jpg, or jpeg image.",
        )

    content = await file.read()
    document = screenshot_extraction_provider.extract(
        filename=file.filename,
        content_type=file.content_type,
        content=content,
    )
    return document.to_dict()
