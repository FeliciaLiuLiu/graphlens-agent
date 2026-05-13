from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from afc_network_narrative.harness.app.pipeline import analyze_graph, analyze_image_file
from afc_network_narrative.harness.reporting.pdf_report import build_report_pdf_bytes
from afc_network_narrative.harness.schemas.graph_extraction_schema import GraphValidationError
from afc_network_narrative.model import VLMAdapter, VLMAdapterError, VLMConfig, create_vlm_adapter

app = FastAPI(title="afc-network-narrative", version="0.1.0")
_adapter_cache: dict[VLMConfig, VLMAdapter] = {}


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze-graph-json")
def analyze_graph_json(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return analyze_graph(payload).to_dict()
    except (GraphValidationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/analyze-image")
async def analyze_image(
    image: UploadFile = File(...),
    backend: str | None = Query(default=None, description="Only the pixtral backend is supported."),
    pixtral_model_path: str | None = Query(default=None, description="Local Pixtral 12B model path."),
    model_path: str | None = Query(default=None, description="Alias for the selected local model path."),
    max_new_tokens: int | None = Query(default=None, description="Maximum graph-extraction generation tokens."),
    extraction_prompt_path: str | None = Query(default=None, description="Graph extraction prompt path."),
) -> dict[str, Any]:
    if image.content_type not in {"image/png", "image/jpeg", "image/jpg"}:
        raise HTTPException(status_code=415, detail="Only PNG and JPEG images are supported.")

    suffix = ".png" if image.content_type == "image/png" else ".jpg"
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await image.read())
            tmp_path = Path(tmp.name)
        output = analyze_image_file(
            str(tmp_path),
            get_adapter(
                backend=backend,
                pixtral_model_path=pixtral_model_path or model_path,
                max_new_tokens=max_new_tokens,
                extraction_prompt_path=extraction_prompt_path,
            ),
        )
        return output.to_dict()
    except (VLMAdapterError, GraphValidationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        if tmp_path:
            tmp_path.unlink(missing_ok=True)


@app.post("/analyze-graph-json-report")
def analyze_graph_json_report(payload: dict[str, Any]) -> Response:
    try:
        output = analyze_graph(payload).to_dict()
        pdf = build_report_pdf_bytes(output, input_name="graph_json_input")
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": 'inline; filename="afc-network-narrative-report.pdf"'},
        )
    except (GraphValidationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/analyze-image-report")
async def analyze_image_report(
    image: UploadFile = File(...),
    backend: str | None = Query(default=None, description="Only the pixtral backend is supported."),
    pixtral_model_path: str | None = Query(default=None, description="Local Pixtral 12B model path."),
    model_path: str | None = Query(default=None, description="Alias for the selected local model path."),
    max_new_tokens: int | None = Query(default=None, description="Maximum graph-extraction generation tokens."),
    extraction_prompt_path: str | None = Query(default=None, description="Graph extraction prompt path."),
) -> Response:
    if image.content_type not in {"image/png", "image/jpeg", "image/jpg"}:
        raise HTTPException(status_code=415, detail="Only PNG and JPEG images are supported.")

    suffix = ".png" if image.content_type == "image/png" else ".jpg"
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await image.read())
            tmp_path = Path(tmp.name)
        output = analyze_image_file(
            str(tmp_path),
            get_adapter(
                backend=backend,
                pixtral_model_path=pixtral_model_path or model_path,
                max_new_tokens=max_new_tokens,
                extraction_prompt_path=extraction_prompt_path,
            ),
        ).to_dict()
        pdf = build_report_pdf_bytes(output, input_name=image.filename or tmp_path.name)
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": 'inline; filename="afc-network-narrative-report.pdf"'},
        )
    except (VLMAdapterError, GraphValidationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        if tmp_path:
            tmp_path.unlink(missing_ok=True)


def get_adapter(
    backend: str | None,
    pixtral_model_path: str | None,
    max_new_tokens: int | None,
    extraction_prompt_path: str | None,
) -> VLMAdapter:
    config = VLMConfig.from_mapping(
        {
            "backend": backend,
            "pixtral_model_path": pixtral_model_path,
            "max_new_tokens": max_new_tokens,
            "extraction_prompt_path": extraction_prompt_path,
        }
    )
    if config not in _adapter_cache:
        _adapter_cache[config] = create_vlm_adapter(config=config)
    return _adapter_cache[config]
