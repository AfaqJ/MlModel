"""Flow: POST /predict  --  the full single-item prediction pipeline.

We warm the model up first (OUTSIDE the trace) so THIS graph is only the predict
pipeline, not the one-time model build:

  routes.predict
    -> Predictor.predict
        -> ProductLookup.match      (-> normalize_text)
        -> Predictor.build_text
        -> OnnxEncoder.embed        (tokenizer -> onnx session.run -> mean-pool)
        -> LogisticHead.predict_proba
        -> confidence.decide        (-> entropy)
        -> Predictor._prediction    (per top-k label)
"""
from __future__ import annotations

from _common import trace, fake_request
from app.api import routes
from app.api.schemas import PredictRequest
from app.core import runtime

# Warm-up: build the model ONCE, outside the trace.
predictor = runtime.predictor_dependency(fake_request)
predictor.predict(item_text="warm up")

payload = PredictRequest(
    item_text="aceite de oliva virgen extra 1L",
    description="botella de vidrio",
    provider="acme foods",
    top_k=3,
    return_debug=True,
)

with trace("predict"):
    result = routes.predict(payload, predictor=predictor)

print("predict -> decision:", result["decision"], "| reason:", result["reason"])
