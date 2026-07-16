from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class DecisionResult:
    decision: str
    reason: str | None


def entropy(proba: np.ndarray) -> float:
    safe = np.clip(proba, 1e-12, 1.0)
    return float(-(safe * np.log(safe)).sum())


def decide(
    *,
    source: str,
    code1: str,
    top1: float,
    margin: float,
    weak_classes: set[str],
    thresholds: dict,
    lookup_model_conflict: bool = False,
    shadow_mode: bool = False,
) -> DecisionResult:
    if shadow_mode:
        return DecisionResult("review_required", "shadow_mode")
    if lookup_model_conflict:
        return DecisionResult("review_required", "lookup_model_conflict")
    if source in ("product_lookup", "meter_lookup"):
        return DecisionResult("auto_accept", None)
    if code1 in weak_classes:
        return DecisionResult("review_required", "weak_class")
    if top1 < thresholds["accept_top1"]:
        return DecisionResult("review_required", "low_confidence")
    if margin < thresholds["accept_margin"]:
        return DecisionResult("review_required", "small_margin")
    return DecisionResult("auto_accept", None)
