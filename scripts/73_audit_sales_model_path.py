#!/usr/bin/env python3
"""Verify the ONNX ML path on sales phrases even when exact rules bypass it."""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.inference.business_rules import BusinessRules, direction_mask
from app.inference.classifier import LogisticHead
from app.inference.model_input import build_model_text
from app.inference.onnx_encoder import OnnxEncoder


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    artifact = ROOT / "artifacts/v1.3.1"
    report = ROOT / "reports/recovery_v1_3_1"
    raw = [row for row in read_csv(ROOT / "Data/processed/line_items.csv") if row["source"] == "VENTAS"]
    rules = BusinessRules(ROOT / "app/data/business_rules.csv")
    encoder = OnnxEncoder(artifact)
    head = LogisticHead(artifact)
    classes = np.asarray([str(code) for code in head.classes_])
    texts = [
        build_model_text(row["nmb_item"], row["dsc_item"], row["rzn_soc_emisor"], "VENTAS")
        for row in raw
    ]
    probabilities = np.asarray(head.predict_proba(encoder.embed(texts)))
    masked = direction_mask(classes, "VENTAS")
    probabilities[:, masked] = 0.0
    probabilities /= probabilities.sum(axis=1, keepdims=True)

    rows = []
    for source, proba in zip(raw, probabilities):
        order = np.argsort(-proba)
        prediction = str(classes[order[0]])
        top1 = float(proba[order[0]])
        top2 = float(proba[order[1]]) if len(order) > 1 else 0.0
        rule = rules.match(source["nmb_item"], "VENTAS")
        expected = rule.category_code if rule else ""
        rows.append({
            "row_id": source["row_id"],
            "item_text": source["nmb_item"],
            "provider": source["rzn_soc_emisor"],
            "exact_rule_truth": expected,
            "ml_prediction_with_rule_bypassed": prediction,
            "top1": round(top1, 6),
            "margin": round(top1 - top2, 6),
            "correct_where_exact_truth_exists": "" if not expected else prediction == expected,
        })

    fields = list(rows[0])
    with (report / "sales_model_bypass_audit.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    known = [row for row in rows if row["exact_rule_truth"]]
    summary = {
        "sales_rows": len(rows),
        "rows_with_exact_rule_truth": len(known),
        "unknown_sales_without_exact_truth": len(rows) - len(known),
        "ml_direct_correct": sum(row["correct_where_exact_truth_exists"] is True for row in known),
        "ml_direct_accuracy": round(
            sum(row["correct_where_exact_truth_exists"] is True for row in known) / len(known), 4
        ),
        "by_truth": {
            code: {
                "rows": sum(row["exact_rule_truth"] == code for row in known),
                "correct": sum(
                    row["exact_rule_truth"] == code and row["correct_where_exact_truth_exists"] is True
                    for row in known
                ),
            }
            for code in sorted({row["exact_rule_truth"] for row in known})
        },
        "unknown_prediction_counts": dict(sorted(Counter(
            row["ml_prediction_with_rule_bypassed"] for row in rows if not row["exact_rule_truth"]
        ).items())),
    }
    (report / "sales_model_bypass_audit.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
