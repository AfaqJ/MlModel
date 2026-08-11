from __future__ import annotations

import re
import time
import numpy as np

from app.core.model_loader import ModelBundle
from app.inference.confidence import decide, entropy
from app.inference.business_rules import direction_mask


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
        meter_code: str | None = None,
        transaction_type: str | None = None,
        invoice_metadata: dict | None = None,
        input_id: str | None = None,
        top_k: int = 3,
        return_debug: bool = False,
    ) -> dict:
        started = time.perf_counter()

        # Deterministic electricity path: when a known meter (CdgIntRecep) is
        # supplied, the category is fixed by the client's meter map and the ML
        # model is skipped entirely. An unknown meter falls through to the model.
        if meter_code:
            meter_hit = self.bundle.meter_lookup.match(meter_code)
            if meter_hit:
                return self._meter_response(meter_hit, meter_code, input_id, started, top_k, return_debug)

        # Transaction-aware business rules. Two outcomes:
        #   assign -> known category, skip the model entirely
        #   review -> we know this line has NO correct category in the taxonomy
        #             (asset disposals). Force review; never let the model guess.
        rule_hit = self.bundle.business_rules.match(item_text, transaction_type)
        if rule_hit and rule_hit.action == "review":
            return self._rule_review_response(rule_hit, input_id, started, top_k, return_debug)

        lookup_hit = self.bundle.lookup.match(item_text, provider)
        text = self.build_text(item_text, description, provider)
        embedding = self.bundle.encoder.embed([text])
        proba = self.bundle.head.predict_proba(embedding)[0]
        classes = self.bundle.head.classes_

        # A purchase can never be income. The model has no notion of transaction
        # direction, which is how 12 COMPRAS lines were predicted as ING-*.
        # Masking removes that error class by construction. Probabilities are
        # renormalised so the reported confidence stays a real probability.
        masked = direction_mask(classes, transaction_type)
        if masked:
            proba = proba.copy()
            proba[masked] = 0.0
            total = proba.sum()
            if total > 0:
                proba = proba / total

        order = np.argsort(-proba)

        model_top = [self._prediction(classes[index], proba[index]) for index in order[:top_k]]
        source = "model"
        predictions = model_top
        lookup_conflict = False

        # An `assign` business rule outranks the model: the item name states its
        # own category and the transaction direction confirms it. The model still
        # runs, so a strong disagreement can still be surfaced for review.
        if rule_hit and rule_hit.action == "assign":
            source = "business_rule"
            rule_code = rule_hit.category_code
            lookup_conflict = classes[order[0]] != rule_code and float(proba[order[0]]) >= 0.90
            model_without_rule = [p for p in model_top if p["code"] != rule_code]
            predictions = [
                {"code": rule_code, "name": self.bundle.names.get(rule_code, ""), "score": 1.0},
                *model_without_rule[: max(0, top_k - 1)],
            ]
        elif lookup_hit:
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

    def _rule_review_response(self, hit, input_id, started, top_k, return_debug) -> dict:
        """A line we KNOW we cannot categorise.

        Asset disposals (`VENTA CAMIONETA`, `VENTA DE ACTIVO FIJO`, machinery)
        have no category in this taxonomy — every ING-* code is operating
        revenue. Returning no prediction at all is the honest answer, and it is
        strictly safer than letting the model return its nearest neighbour at
        high confidence, which is what produced "milk sales @ 0.841" for a truck.
        """
        latency_ms = int((time.perf_counter() - started) * 1000)
        response = {
            "input_id": input_id,
            "model_version": self.bundle.model_version,
            "source": "business_rule",
            "predictions": [],
            "confidence": {"top1": 0.0, "margin": 0.0, "entropy": 0.0},
            "decision": "review_required",
            "reason": "no_category_in_taxonomy",
            "latency_ms": latency_ms,
            "debug": None,
        }
        if return_debug:
            response["debug"] = {"business_rule": hit.__dict__}
        return response

    def _meter_response(self, hit, meter_code, input_id, started, top_k, return_debug) -> dict:
        prediction = {
            "code": hit.category_code,
            "name": self.bundle.names.get(hit.category_code, ""),
            "score": 1.0,
        }
        decision = decide(
            source="meter_lookup",
            code1=hit.category_code,
            top1=1.0,
            margin=1.0,
            weak_classes=self.bundle.weak_classes,
            thresholds=self.bundle.thresholds,
            shadow_mode=self.shadow_mode,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        response = {
            "input_id": input_id,
            "model_version": self.bundle.model_version,
            "source": "meter_lookup",
            "predictions": [prediction][:top_k],
            "confidence": {"top1": 1.0, "margin": 1.0, "entropy": 0.0},
            "decision": decision.decision,
            "reason": decision.reason,
            "latency_ms": latency_ms,
            "debug": None,
        }
        if return_debug:
            response["debug"] = {"meter_hit": hit.__dict__, "meter_code": meter_code}
        return response

    def _prediction(self, code: str, score: float) -> dict:
        code = str(code)
        return {
            "code": code,
            "name": self.bundle.names.get(code, ""),
            "score": round(float(score), 4),
        }
