"""Deterministic, transaction-aware exact lookup applied before the model.

WHY THIS EXISTS
---------------
When an invoice item exactly names one of the client's 71 active taxonomy
categories, asking a probabilistic classifier to rediscover that known fact
adds uncertainty for no benefit. The table contains all canonical taxonomy
leaf names plus explicit, client-specific aliases. Matching is exact after
normalizing superficial spelling differences; it is never fuzzy.

DIRECTION MASKING
-----------------
The transaction direction is now also part of the trained model text. Masks
remain as defense in depth: COMPRAS cannot return income classes and VENTAS
cannot return expense/administration classes. Unknown sales are still forced to
review because asset disposals and other unmatched sales may be outside the
active taxonomy.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from app.inference.normalize import normalize_text


@dataclass(frozen=True)
class BusinessRuleHit:
    category_code: str
    action: str
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
        versions = set()
        with open(path, newline="", encoding="utf-8-sig") as handle:
            for line_number, row in enumerate(csv.DictReader(handle), start=2):
                direction = (row.get("transaction_type") or "").strip().upper()
                text = normalize_text(row.get("item_text", ""))
                action = (row.get("action") or "assign").strip().lower()
                code = (row.get("category_code") or "").strip() or None
                if not direction or not text:
                    raise ValueError(f"business_rules.csv:{line_number}: empty key")
                if direction not in {"COMPRAS", "VENTAS"}:
                    raise ValueError(f"business_rules.csv:{line_number}: invalid transaction_type {direction!r}")
                if action != "assign" or not code:
                    raise ValueError(
                        f"business_rules.csv:{line_number}: only assign rules with a category are supported"
                    )
                key = (direction, text)
                if key in self.entries:
                    raise ValueError(f"business_rules.csv:{line_number}: duplicate normalized key {key}")
                version = (row.get("rule_version") or "").strip()
                if not version:
                    raise ValueError(f"business_rules.csv:{line_number}: empty rule_version")
                versions.add(version)
                self.entries[key] = BusinessRuleHit(
                    category_code=code,
                    action=action,
                    rule_version=version,
                    note=(row.get("note") or "").strip(),
                    matched_key=text,
                )
        if len(versions) > 1:
            raise ValueError(f"business_rules.csv: mixed rule versions {sorted(versions)}")
        self.version = next(iter(versions), "")

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
            "assign_rules": len(self.entries),
        }


def direction_mask(classes, transaction_type: str | None):
    """Indices of classes that are IMPOSSIBLE for this transaction direction.

    The probabilistic model still returns a review suggestion for an unknown
    sale, but it may only suggest a direction-compatible class.
    """
    direction = (transaction_type or "").strip().upper()
    if direction == "COMPRAS":
        return [i for i, code in enumerate(classes) if str(code).startswith("ING-")]
    if direction == "VENTAS":
        return [i for i, code in enumerate(classes) if not str(code).startswith("ING-")]
    return []
