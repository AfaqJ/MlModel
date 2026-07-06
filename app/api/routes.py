from __future__ import annotations

import time
from fastapi import APIRouter, HTTPException, Request

from app.api.schemas import (
    BatchPredictRequest,
    BatchPredictResponse,
    PredictRequest,
    PredictResponse,
    RowError,
)
from app.core.runtime import get_bundle, get_predictor


router = APIRouter()


@router.get("/health")
def health(request: Request) -> dict:
    return {
        "status": "ok",
        "service_version": request.app.state.settings.service_version,
        "model_loaded": request.app.state.bundle is not None,
    }


@router.get("/model-info")
def model_info(request: Request) -> dict:
    return get_bundle(request.app).info()


@router.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest, request: Request) -> dict:
    return get_predictor(request.app).predict(**payload.model_dump())


@router.post("/predict-batch", response_model=BatchPredictResponse)
def predict_batch(payload: BatchPredictRequest, request: Request) -> dict:
    settings = request.app.state.settings
    if len(payload.items) > settings.max_batch_size:
        raise HTTPException(
            status_code=413,
            detail=f"Batch has {len(payload.items)} items; max is {settings.max_batch_size}.",
        )

    started = time.perf_counter()
    results = []
    counts = {"count": len(payload.items), "auto_accept": 0, "review_required": 0, "errors": 0}
    predictor = get_predictor(request.app)
    for item in payload.items:
        try:
            data = item.model_dump()
            data["top_k"] = payload.top_k
            result = predictor.predict(**data)
            counts[result["decision"]] += 1
            results.append(PredictResponse(**result))
        except Exception as exc:
            counts["errors"] += 1
            results.append(RowError(input_id=item.input_id, error={"code": "row_failed", "message": str(exc)}))

    return {
        "batch_id": payload.batch_id,
        "model_version": get_bundle(request.app).model_version,
        "results": results,
        "summary": counts,
        "latency_ms": int((time.perf_counter() - started) * 1000),
    }
