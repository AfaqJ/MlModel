"""Deterministic, transaction-aware business rules applied before the model.

WHY THIS EXISTS
---------------
Two distinct failures in the v1.1.0 incident share one shape: the model was
forced to answer a question it could not answer, and answered confidently.

1. `VENTA DE LECHE` repeats identically across 47 invoices and its name states
   its category outright. Asking a probabilistic classifier to rediscover a
   known fact spends uncertainty for nothing. A lookup is simply correct.

2. `VENTA DE ACTIVO FIJO` (sale of a fixed asset) has NO correct category in the
   taxonomy at all — every ING-* code is operating revenue, and selling a truck
   is not. The model must still return something, so it returns the nearest
   neighbour. In testing it produced "milk sales" at 0.841 confidence and would
   have been auto-accepted. That is the original incident inverted.

Rules therefore support two actions:
    assign  -> a known category, score 1.0, skip the model
    review  -> force review_required, never auto-accept, regardless of the model

`review` rules are the important half: they encode "we know we do not know",
which is the one thing the model cannot express about a missing category.

DIRECTION MASKING
-----------------
Separately, a COMPRAS (purchase) line can never be income. The model has no
notion of transaction direction — it was parsed and stored but never reached the
predictor — so it produced 12 purchase lines predicted as income. Masking the
ING-* classes for purchases removes that class of error by construction rather
than hoping training fixes it.

The reverse mask (VENTAS cannot be an expense) is deliberately NOT applied:
asset disposals genuinely have no income category, and forcing them into one is
exactly the failure above. They are routed to review by rule instead.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from app.inference.normalize import normalize_text


@dataclass(frozen=True)
class BusinessRuleHit:
    category_code: str | None   # None when action == "review"
    action: str                 # "assign" | "review"
    rule_version: str
    note: str
    matched_key: str


class BusinessRules:
    """Exact-match rules on (transaction_type, normalized item_text)."""

    def __init__(self, path: Path):
        self.path = path
        self.entries: dict[tuple[str, str], BusinessRuleHit] = {}
        self.version = ""
        if path.exists():
            self._load(path)

    @property
    def enabled(self) -> bool:
        return bool(self.entries)

    def _load(self, path: Path) -> None:
        with open(path, newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                direction = (row.get("transaction_type") or "").strip().upper()
                text = normalize_text(row.get("item_text", ""))
                action = (row.get("action") or "assign").strip().lower()
                code = (row.get("category_code") or "").strip() or None
                if not direction or not text:
                    continue
                if action == "assign" and not code:
                    # An assign rule with no category is a data error; skipping it
                    # silently would reintroduce the exact class of bug this file
                    # exists to prevent.
                    raise ValueError(
                        f"business_rules.csv: action=assign with empty category_code "
                        f"for {direction}/{text!r}"
                    )
                self.entries[(direction, text)] = BusinessRuleHit(
                    category_code=code,
                    action=action,
                    rule_version=(row.get("rule_version") or "").strip(),
                    note=(row.get("note") or "").strip(),
                    matched_key=text,
                )
                self.version = (row.get("rule_version") or "").strip() or self.version

    def match(self, item_text: str, transaction_type: str | None) -> BusinessRuleHit | None:
        if not transaction_type:
            return None
        return self.entries.get(
            ((transaction_type or "").strip().upper(), normalize_text(item_text))
        )

    def info(self) -> dict:
        return {
            "enabled": self.enabled,
            "path": str(self.path),
            "entries": len(self.entries),
            "rule_version": self.version,
            "assign_rules": sum(1 for h in self.entries.values() if h.action == "assign"),
            "review_rules": sum(1 for h in self.entries.values() if h.action == "review"),
        }


def direction_mask(classes, transaction_type: str | None):
    """Indices of classes that are IMPOSSIBLE for this transaction direction.

    Only the purchase->income direction is masked. See the module docstring for
    why the reverse is not.
    """
    if (transaction_type or "").strip().upper() != "COMPRAS":
        return []
    return [i for i, code in enumerate(classes) if str(code).startswith("ING-")]
