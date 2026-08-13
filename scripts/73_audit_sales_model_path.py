#!/usr/bin/env python3
"""Check memorization of known historical sales when exact rules are bypassed.

This mixes historical training and held-out rows, so it is not a deployment
accuracy estimate. Its narrow purpose is to prove the trained model learned the
known milk/cattle/calf labels rather than relying only on runtime exact rules.
"""
from __future__ import annotations

import argparse
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, default=ROOT / "artifacts/v1.3.3")
    parser.add_argument("--report", type=Path, default=ROOT / "reports/recovery_v1_3_3")
    args = parser.parse_args()
    artifact = args.artifact
    report = args.report
    report.mkdir(parents=True, exist_ok=True)
    raw = [row for row in read_csv(ROOT / "Data/processed/line_items.csv") if row["source"] == "VENTAS"]
    rules = BusinessRules(ROOT / "app/data/business_rules.csv")
    texts = [
        build_model_text(row["nmb_item"], row["dsc_item"], row["rzn_soc_emisor"], "VENTAS")
        for row in raw
    ]
    if artifact.exists():
        encoder = OnnxEncoder(artifact)
        head = LogisticHead(artifact)
        classes = np.asarray([str(code) for code in head.classes_])
        probabilities = np.asarray(head.predict_proba(encoder.embed(texts)))
        backend = json.loads((artifact / "model_card.json").read_text())["artifact_format"]
    else:
        # This fallback keeps the incident proof available before packaging.
        # The final release reruns the same audit against the ONNX artifact.
        import transformers.training_args as transformers_training_args
        if not hasattr(transformers_training_args, "default_logdir"):
            from transformers.integrations.integration_utils import default_logdir
            transformers_training_args.default_logdir = default_logdir
        from setfit import SetFitModel

        model = SetFitModel.from_pretrained(
            str(ROOT / "models/setfit_base_recovery_v1_3_2"), local_files_only=True
        )
        classes = np.asarray([str(code) for code in model.labels])
        probabilities = np.asarray(model.predict_proba(texts))
        backend = "setfit-fp32"
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
        "audit_type": "known-history memorization check; not blind deployment accuracy",
        "inference_backend": backend,
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
