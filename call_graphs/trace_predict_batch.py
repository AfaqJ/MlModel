"""Flow: POST /predict-batch  --  many items through one request.

Same warm-up trick. The graph shows routes.predict_batch checking the size limit
against settings.max_batch_size, then looping and calling Predictor.predict once
PER item (each repeats the full pipeline from trace_predict.py), tallying
auto_accept / review_required / errors before returning.
"""
from __future__ import annotations

from _common import trace, fake_request
from app.api import routes
from app.api.schemas import BatchPredictRequest
from app.core import runtime

# Resolve the same dependencies FastAPI would inject, and warm the model up.
settings = runtime.settings_dependency(fake_request)
predictor = runtime.predictor_dependency(fake_request)
bundle = runtime.bundle_dependency(fake_request)
predictor.predict(item_text="warm up")

payload = BatchPredictRequest(
    batch_id="demo-batch-001",
    top_k=3,
    items=[
        {"item_text": "aceite de oliva 1L", "provider": "acme foods"},
        {"item_text": "servicio de limpieza mensual", "description": "oficina"},
        {"item_text": "tornillos m6 caja 100u"},
    ],
)

with trace("predict_batch"):
    result = routes.predict_batch(
        payload, settings=settings, predictor=predictor, bundle=bundle
    )

print("predict_batch -> summary:", result["summary"])
