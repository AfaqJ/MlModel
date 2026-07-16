from __future__ import annotations

from pathlib import Path
import time
from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.schemas import (
    BatchPredictRequest,
    BatchPredictResponse,
    PredictRequest,
    PredictResponse,
    RowError,
)
from app.core.config import Settings
from app.core.runtime import (
    bundle_dependency,
    predictor_dependency,
    settings_dependency,
)


router = APIRouter()


@router.get("/health")
def health(request: Request) -> dict:
    # health must NOT trigger a model load, so it peeks at app.state directly
    # instead of using the bundle dependency (which would build the model).
    return {
        "status": "ok",
        "service_version": request.app.state.settings.service_version,
        "model_loaded": request.app.state.bundle is not None,
    }


@router.get("/model-info")
def model_info(bundle=Depends(bundle_dependency)) -> dict:
    return bundle.info()


@router.get("/artifact-check")
def artifact_check(settings: Settings = Depends(settings_dependency)) -> dict:
    model_dir = Path(settings.model_dir)
    files = {}
    for relative in [
        "model.onnx",
        "classifier.joblib",
        "model_card.json",
        "labels.json",
        "tokenizer/tokenizer.json",
    ]:
        path = model_dir / relative
        exists = path.exists()
        first_bytes = ""
        if exists and path.is_file():
            first_bytes = path.read_bytes()[:80].decode("utf-8", errors="replace")
        files[relative] = {
            "exists": exists,
            "size_bytes": path.stat().st_size if exists else 0,
            "looks_like_lfs_pointer": first_bytes.startswith("version https://git-lfs.github.com/spec"),
        }
    return {"model_dir": str(model_dir), "files": files}


@router.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest, predictor=Depends(predictor_dependency)) -> dict:
    # `predictor` is left un-annotated on purpose: annotating it with `Predictor`
    # would force importing the ML stack at startup and break the lazy load.
    return predictor.predict(**payload.model_dump())


@router.post("/predict-batch", response_model=BatchPredictResponse)
def predict_batch(
    payload: BatchPredictRequest,
    settings: Settings = Depends(settings_dependency),
    predictor=Depends(predictor_dependency),
    bundle=Depends(bundle_dependency),
) -> dict:
    if len(payload.items) > settings.max_batch_size:
        raise HTTPException(
            status_code=413,
            detail=f"Batch has {len(payload.items)} items; max is {settings.max_batch_size}.",
        )

    started = time.perf_counter()
    results = []
    counts = {"count": len(payload.items), "auto_accept": 0, "review_required": 0, "errors": 0}
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
        "model_version": bundle.model_version,
        "results": results,
        "summary": counts,
        "latency_ms": int((time.perf_counter() - started) * 1000),
    }
