from __future__ import annotations

import time
import numpy as np

from app.core.model_loader import ModelBundle
from app.inference.confidence import DecisionResult, decide, entropy
from app.inference.business_rules import direction_mask
from app.inference.model_input import build_model_text
from app.inference.ambiguity_guard import model_review_guard_reason


class Predictor:
    def __init__(self, bundle: ModelBundle, shadow_mode: bool = False):
        self.bundle = bundle
        self.shadow_mode = shadow_mode

    def build_text(
        self,
        item_text: str,
        description: str = "",
        provider: str = "",
        transaction_type: str | None = None,
    ) -> str:
        return build_model_text(item_text, description, provider, transaction_type)

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
        if meter_code and (transaction_type or "").upper() == "COMPRAS":
            meter_hit = self.bundle.meter_lookup.match(meter_code)
            if meter_hit:
                return self._invoice_context_guard(
                    self._meter_response(meter_hit, meter_code, input_id, started, top_k, return_debug),
                    invoice_metadata,
                )

        # A verified exact sales phrase is authoritative. Skip both the model and
        # product lookup: this is the deterministic path the incident lacked.
        rule_hit = self.bundle.business_rules.match(item_text, transaction_type)
        if rule_hit:
            return self._invoice_context_guard(
                self._business_rule_response(rule_hit, input_id, started, top_k, return_debug),
                invoice_metadata,
            )

        # Row-level client product labels are stronger than invoice-folder
        # placement. Product hits short-circuit and cannot be vetoed by ML.
        lookup_hit = self.bundle.lookup.match(item_text, provider) if (
            transaction_type or ""
        ).upper() == "COMPRAS" else None
        if lookup_hit:
            return self._invoice_context_guard(
                self._product_response(lookup_hit, input_id, started, top_k, return_debug),
                invoice_metadata,
            )

        text = self.build_text(item_text, description, provider, transaction_type)
        embedding = self.bundle.encoder.embed([text])
        proba = self.bundle.head.predict_proba(embedding)[0]
        classes = self.bundle.head.classes_

        # Direction is learned in the model text and also enforced here. The
        # mask is defense in depth: impossible cross-direction labels can never
        # be returned even when the model is confidently wrong.
        masked = direction_mask(classes, transaction_type)
        if masked:
            proba = proba.copy()
            proba[masked] = 0.0
            total = proba.sum()
            if total > 0:
                proba = proba / total

        order = np.argsort(-proba)
        if masked:
            masked_set = set(masked)
            order = np.asarray([index for index in order if index not in masked_set])

        if len(order) == 0:
            raise RuntimeError("direction mask removed every model class")
        # Acceptance must never depend on how many predictions the caller asks
        # us to display. Compute top1/top2 from the full, unrounded probability
        # vector; round only the response representation below.
        top1_index = int(order[0])
        top2_index = int(order[1]) if len(order) > 1 else None
        code1 = str(classes[top1_index])
        top1 = float(proba[top1_index])
        top2 = float(proba[top2_index]) if top2_index is not None else 0.0
        model_top = [self._prediction(classes[index], proba[index]) for index in order[:top_k]]
        source = "model"
        predictions = model_top

        decision = decide(
            source=source,
            code1=code1,
            top1=top1,
            margin=top1 - top2,
            weak_classes=self.bundle.weak_classes,
            thresholds=self.bundle.thresholds,
            shadow_mode=self.shadow_mode,
        )
        ambiguity_reason = model_review_guard_reason(item_text, description, code1) if source == "model" else None
        if ambiguity_reason:
            decision = DecisionResult("review_required", ambiguity_reason)
        if (transaction_type or "").upper() == "VENTAS" and source != "business_rule":
            # The known operating sales were handled by the exact lookup above.
            # An unknown sale may be an asset disposal or a missing taxonomy
            # class, so a probabilistic result is useful for review but unsafe to
            # auto-accept regardless of its confidence.
            decision = DecisionResult("review_required", "unknown_sales_item")
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
                "model_top1": model_top[0],
            }
        return self._invoice_context_guard(response, invoice_metadata)

    @staticmethod
    def _invoice_context_guard(response: dict, invoice_metadata: dict | None) -> dict:
        metadata = invoice_metadata or {}
        document_type = str(metadata.get("document_type") or metadata.get("tipo_dte") or "").lstrip("0")
        document_kind = str(metadata.get("xml_document_kind") or "").lower()
        if document_type == "43" or document_kind == "liquidacion":
            response["decision"] = "review_required"
            response["reason"] = "liquidacion_dte43_requires_client_category"
        return response

    def _business_rule_response(self, hit, input_id, started, top_k, return_debug) -> dict:
        latency_ms = int((time.perf_counter() - started) * 1000)
        prediction = {
            "code": hit.category_code,
            "name": self.bundle.names.get(hit.category_code, ""),
            "score": 1.0,
        }
        decision = decide(
            source="business_rule",
            code1=hit.category_code,
            top1=1.0,
            margin=1.0,
            weak_classes=self.bundle.weak_classes,
            thresholds=self.bundle.thresholds,
            shadow_mode=self.shadow_mode,
        )
        response = {
            "input_id": input_id,
            "model_version": self.bundle.model_version,
            "source": "business_rule",
            "predictions": [prediction][:top_k],
            "confidence": {"top1": 1.0, "margin": 1.0, "entropy": 0.0},
            "decision": decision.decision,
            "reason": decision.reason,
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

    def _product_response(self, hit, input_id, started, top_k, return_debug) -> dict:
        latency_ms = int((time.perf_counter() - started) * 1000)
        prediction = {
            "code": hit.category_code,
            "name": self.bundle.names.get(hit.category_code, ""),
            "score": 1.0,
        }
        decision = decide(
            source="product_lookup",
            code1=hit.category_code,
            top1=1.0,
            margin=1.0,
            weak_classes=self.bundle.weak_classes,
            thresholds=self.bundle.thresholds,
            shadow_mode=self.shadow_mode,
        )
        response = {
            "input_id": input_id,
            "model_version": self.bundle.model_version,
            "source": "product_lookup",
            "predictions": [prediction][:top_k],
            "confidence": {"top1": 1.0, "margin": 1.0, "entropy": 0.0},
            "decision": decision.decision,
            "reason": decision.reason,
            "latency_ms": latency_ms,
            "debug": None,
        }
        if return_debug:
            response["debug"] = {"product_lookup": hit.__dict__}
        return response

    def _prediction(self, code: str, score: float) -> dict:
        code = str(code)
        return {
            "code": code,
            "name": self.bundle.names.get(code, ""),
            "score": round(float(score), 4),
        }
