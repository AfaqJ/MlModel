"""Flow: GET /model-info  --  the FIRST request that forces the model to load.

The best graph for 'how does the model load?'. Because the app booted empty
(lazy load), this runs the whole build chain exactly once:

  bundle_dependency -> get_bundle -> ModelBundle(...)
     -> OnnxEncoder      (AutoTokenizer.from_pretrained + onnxruntime.InferenceSession)
     -> LogisticHead     (joblib.load classifier.joblib)
     -> ProductLookup    (reads the CSV, normalizes each row)

then model_info -> bundle.info().
"""
from __future__ import annotations

from _common import trace, fake_request
from app.api import routes
from app.core import runtime

with trace("model_info"):
    bundle = runtime.bundle_dependency(fake_request)  # builds the model on first call
    result = routes.model_info(bundle=bundle)

print("model_info -> version:", result["model_version"])
