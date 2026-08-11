#!/usr/bin/env python3
"""Fail-closed validation for the v1.3 transaction-aware data/rule candidate."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.inference.business_rules import BusinessRules
from app.inference.model_input import build_model_text


CANDIDATE = ROOT / "Data/candidates/recovery_v1_3_1"
RAW = ROOT / "Data/processed/line_items.csv"
TAXONOMY = ROOT / "Data/current_context_2026_06_30/taxonomy_from_plan.csv"
EXCLUDED = ROOT / "Data/current_context_2026_06_30/excluded_categories.csv"
RULES = ROOT / "app/data/business_rules.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def main() -> None:
    manifest = json.loads((CANDIDATE / "manifest.json").read_text())
    for filename, expected in manifest["outputs"].items():
        require(sha256(CANDIDATE / filename) == expected, f"hash mismatch: {filename}")

    master = read_csv(CANDIDATE / "master_gold.csv")
    audit = read_csv(CANDIDATE / "starving_category_manual_audit.csv")
    quarantine = read_csv(CANDIDATE / "quarantined_wrong_labels.csv")
    folder_audit = read_csv(CANDIDATE / "folder_line_audit.csv")
    taxonomy = read_csv(TAXONOMY)
    excluded = read_csv(EXCLUDED)
    require(len(taxonomy) == 71, "active taxonomy is not 71 rows")
    require(len(excluded) == 7, "separate excluded taxonomy is not 7 rows")
    require(len(master) == 1821, "unexpected candidate row count")
    require(len(audit) == 139, "manual audit row count changed")
    require(Counter(row["verdict"] for row in audit) == {"promote": 83, "reject": 38, "already_gold": 13, "needs_client": 5},
            "manual audit verdict counts changed")
    require(len(quarantine) == 97, "wrong-label quarantine count changed")
    require(len(folder_audit) == 399, "folder audit must cover all 399 rows")
    require(Counter(row["disposition"] for row in folder_audit) == {"keep": 277, "quarantine": 88, "correct": 34},
            "folder audit dispositions changed")
    require(not any(row["source"].startswith("synthetic") for row in master), "synthetic data present")
    require(all(row["direction"] in {"COMPRAS", "VENTAS"} for row in master), "missing direction")
    require(all((row["direction"] == "VENTAS") == row["category_code"].startswith("ING-") for row in master),
            "category/direction mismatch")

    labels_by_text = defaultdict(set)
    distinct_counts = Counter()
    seen = set()
    for row in master:
        text = build_model_text(row["item_text"], row["description"], row["provider"], row["direction"])
        normalized = normalize(text)
        labels_by_text[normalized].add(row["category_code"])
        key = (normalized, row["category_code"])
        if key not in seen:
            distinct_counts[row["category_code"]] += 1
            seen.add(key)
    require(not any(len(labels) > 1 for labels in labels_by_text.values()), "cross-label contradiction")
    eligible = {code for code, count in distinct_counts.items() if count >= 2}
    active = {row["new_code"] for row in taxonomy}
    require(len(eligible) == 67, f"expected 67 model-eligible categories, got {len(eligible)}")
    require(active - eligible == {"ADM-1.9", "ADM-2.3", "ING-0.5", "ING-0.6"}, "unexpected active categories missing from model")

    rules = BusinessRules(RULES)
    require(len(rules.entries) == 95, "expected 71 canonical rules plus 24 aliases")
    for row in taxonomy:
        direction = "VENTAS" if row["new_code"].startswith("ING-") else "COMPRAS"
        hit = rules.match(row["leaf"], direction)
        require(hit is not None and hit.category_code == row["new_code"], f"canonical rule missing: {row['new_code']}")

    raw_sales = [row for row in read_csv(RAW) if row["source"] == "VENTAS"]
    matched = [row for row in raw_sales if rules.match(row["nmb_item"], "VENTAS")]
    unknown = [row for row in raw_sales if not rules.match(row["nmb_item"], "VENTAS")]
    require(len(matched) == 118 and len(unknown) == 7, "raw sales routing count changed")
    require(Counter(row["nmb_item"] for row in unknown) == {
        "VENTA CAMIONETA": 3,
        "VENTA DE ACTIVO FIJO": 2,
        "OTROS INGRESOS": 1,
        "maquinaria": 1,
    }, "unknown sales set changed")

    print(json.dumps({
        "status": "pass",
        "active_taxonomy": len(active),
        "model_eligible": len(eligible),
        "active_not_model_eligible": sorted(active - eligible),
        "separately_excluded": len(excluded),
        "candidate_rows": len(master),
        "distinct_inputs": len(labels_by_text),
        "manual_audit": dict(Counter(row["verdict"] for row in audit)),
        "quarantined_wrong_labels": len(quarantine),
        "exact_rules": len(rules.entries),
        "raw_sales_exact": len(matched),
        "raw_sales_unknown_review": len(unknown),
    }, indent=2))


if __name__ == "__main__":
    main()
