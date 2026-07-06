from __future__ import annotations

import re
import time
import numpy as np

from app.core.model_loader import ModelBundle
from app.inference.confidence import decide, entropy


NUMERIC_RE = re.compile(r"[\d\s.,\-/]+$")


class Predictor:
    def __init__(self, bundle: ModelBundle, shadow_mode: bool = False):
        self.bundle = bundle
        self.shadow_mode = shadow_mode

    def build_text(self, item_text: str, description: str = "", provider: str = "") -> str:
        desc = (description or "").strip()
        if NUMERIC_RE.fullmatch(desc or "0"):
            desc = ""
        parts = [item_text.strip(), desc, (provider or "").strip()]
        return " | ".join(part for part in parts if part)

    def predict(
        self,
        *,
        item_text: str,
        description: str = "",
        provider: str = "",
        invoice_metadata: dict | None = None,
        input_id: str | None = None,
        top_k: int = 3,
        return_debug: bool = False,
    ) -> dict:
        started = time.perf_counter()
        lookup_hit = self.bundle.lookup.match(item_text, provider)
        text = self.build_text(item_text, description, provider)
        embedding = self.bundle.encoder.embed([text])
        proba = self.bundle.head.predict_proba(embedding)[0]
        order = np.argsort(-proba)
        classes = self.bundle.head.classes_

        model_top = [self._prediction(classes[index], proba[index]) for index in order[:top_k]]
        source = "model"
        predictions = model_top
        lookup_conflict = False

        if lookup_hit:
            source = "product_lookup"
            lookup_code = lookup_hit.category_code
            lookup_conflict = classes[order[0]] != lookup_code and float(proba[order[0]]) >= 0.70
            model_without_lookup = [p for p in model_top if p["code"] != lookup_code]
            predictions = [
                {
                    "code": lookup_code,
                    "name": self.bundle.names.get(lookup_code, ""),
                    "score": 1.0,
                },
                *model_without_lookup[: max(0, top_k - 1)],
            ]

        code1 = str(predictions[0]["code"])
        top1 = float(predictions[0]["score"])
        top2 = float(predictions[1]["score"]) if len(predictions) > 1 else 0.0
        decision = decide(
            source=source,
            code1=code1,
            top1=top1,
            margin=top1 - top2,
            weak_classes=self.bundle.weak_classes,
            thresholds=self.bundle.thresholds,
            lookup_model_conflict=lookup_conflict,
            shadow_mode=self.shadow_mode,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        response = {
            "input_id": input_id,
            "model_version": self.bundle.model_version,
            "source": source,
            "predictions": predictions,
            "confidence": {
                "top1": round(top1, 4),
                "margin": round(top1 - top2, 4),
                "entropy": round(entropy(proba), 4),
            },
            "decision": decision.decision,
            "reason": decision.reason,
            "latency_ms": latency_ms,
            "debug": None,
        }
        if return_debug:
            response["debug"] = {
                "model_text": text,
                "lookup_hit": None if not lookup_hit else lookup_hit.__dict__,
                "model_top1": model_top[0],
            }
        return response

    def _prediction(self, code: str, score: float) -> dict:
        code = str(code)
        return {
            "code": code,
            "name": self.bundle.names.get(code, ""),
            "score": round(float(score), 4),
        }
