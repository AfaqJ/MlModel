#!/usr/bin/env python3
"""Calibrate v1.3 decisions and audit held-out false positives/negatives.

This evaluates the same local cascade used by the backend on the locked split:

    exact taxonomy/alias rule -> product lookup -> direction-masked SetFit

Meter lookup is not applied here because the gold rows do not retain the XML
CdgIntRecep; the full raw replay script parses that value from the XML files.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import unicodedata
import re
from collections import Counter, defaultdict
from pathlib import Path

import joblib
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.inference.business_rules import BusinessRules, direction_mask
from app.inference.model_input import build_model_text
from app.inference.product_lookup import ProductLookup
from app.inference.ambiguity_guard import model_review_guard_reason


MODEL = ROOT / "models/setfit_base_recovery_v1_3_1"
ARTIFACT = ROOT / "artifacts/v1.3.1"
GOLD = ROOT / "Data/candidates/recovery_v1_3_1/master_gold.csv"
SPLIT = ROOT / "Data/candidates/recovery_v1_3_1/split_seed42.csv"
REPORT_DIR = ROOT / "reports/recovery_v1_3_1"
# The user explicitly prioritised avoiding confidently wrong auto-accepts over
# coverage. Require zero observed model false positives on the locked holdout;
# deterministic exact lookups remain independently auditable.
TARGET_ACCEPTED_ACCURACY = 1.00
MIN_CALIBRATION_ACCEPTS = 20
RELEASE_TOP1 = 0.75
RELEASE_MARGIN = 0.50


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def wilson_lower(correct: int, total: int, z: float = 1.96) -> float:
    if total == 0:
        return 0.0
    p = correct / total
    denominator = 1 + z * z / total
    centre = p + z * z / (2 * total)
    adjustment = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total)
    return (centre - adjustment) / denominator


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, default=MODEL)
    parser.add_argument("--artifact", type=Path, help="Use the exported ONNX artifact for the final backend-parity audit.")
    parser.add_argument("--gold", type=Path, default=GOLD)
    parser.add_argument("--split", type=Path, default=SPLIT)
    parser.add_argument("--report-dir", type=Path, default=REPORT_DIR)
    parser.add_argument("--device", choices=["mps", "cpu"], default="cpu")
    args = parser.parse_args()

    gold_by_id = {row["gold_id"]: row for row in read_csv(args.gold)}
    validation_split = [row for row in read_csv(args.split) if row["split"] == "validation"]
    validation = [gold_by_id[row["gold_id"]] for row in validation_split]

    if args.artifact:
        from app.inference.onnx_encoder import OnnxEncoder
        from app.inference.classifier import LogisticHead
        body = OnnxEncoder(args.artifact)
        head = LogisticHead(args.artifact)
        backend = "onnx_int8"
    else:
        from sentence_transformers import SentenceTransformer
        body = SentenceTransformer(
            str(args.model.resolve()),
            device=args.device,
            tokenizer_kwargs={"fix_mistral_regex": False},
        )
        head = joblib.load(args.model / "model_head.pkl")
        backend = "setfit_fp32"
    classes = np.asarray([str(value) for value in head.classes_])
    texts = [
        build_model_text(row["item_text"], row["description"], row["provider"], row["direction"])
        for row in validation
    ]
    embeddings = (
        body.embed(texts, batch_size=64)
        if args.artifact
        else body.encode(texts, batch_size=64, show_progress_bar=True)
    )
    probabilities = np.asarray(head.predict_proba(embeddings))

    rules = BusinessRules(ROOT / "app/data/business_rules.csv")
    products = ProductLookup(ROOT / "app/data/product_lookup.csv")

    distinct_by_label: defaultdict[str, set[str]] = defaultdict(set)
    for row in gold_by_id.values():
        text = build_model_text(row["item_text"], row["description"], row["provider"], row["direction"])
        distinct_by_label[row["category_code"]].add(normalize(text))
    distinct_counts = {code: len(values) for code, values in distinct_by_label.items()}
    weak_classes = {code for code, count in distinct_counts.items() if count < 15}
    weak_classes.update(set(distinct_counts) - set(classes))

    rows = []
    for index, (gold, text) in enumerate(zip(validation, texts)):
        proba = probabilities[index].copy()
        masked = direction_mask(classes, gold["direction"])
        if masked:
            proba[masked] = 0
            if proba.sum() > 0:
                proba /= proba.sum()
        order = np.argsort(-proba)
        code1 = str(classes[order[0]])
        top1 = float(proba[order[0]])
        top2 = float(proba[order[1]]) if len(order) > 1 else 0.0
        rule = rules.match(gold["item_text"], gold["direction"])
        product = products.match(gold["item_text"], gold["provider"]) if not rule and gold["direction"] == "COMPRAS" else None
        source = "business_rule" if rule else "product_lookup" if product else "model"
        final_code = rule.category_code if rule else product.category_code if product else code1
        lookup_conflict = False
        guard_reason = model_review_guard_reason(gold["item_text"], gold["description"]) if source == "model" else None
        rows.append({
            "gold_id": gold["gold_id"],
            "truth": gold["category_code"],
            "item_text": gold["item_text"],
            "description": gold["description"],
            "provider": gold["provider"],
            "direction": gold["direction"],
            "model_text": text,
            "source": source,
            "prediction": final_code,
            "model_prediction": code1,
            "top1": top1,
            "margin": top1 - top2,
            "lookup_conflict": lookup_conflict,
            "guard_reason": guard_reason or "",
            "correct": final_code == gold["category_code"],
            "top3": ";".join(str(classes[i]) for i in order[:3]),
        })

    calibration_rows = [row for row in rows if row["source"] == "model" and row["direction"] == "COMPRAS"]
    sweep = []
    for top1_threshold in np.arange(0.50, 0.981, 0.02):
        for margin_threshold in np.arange(0.05, 0.501, 0.05):
            accepted = [
                row for row in calibration_rows
                if row["prediction"] not in weak_classes
                and not row["guard_reason"]
                and row["top1"] >= top1_threshold
                and row["margin"] >= margin_threshold
            ]
            correct = sum(row["correct"] for row in accepted)
            sweep.append({
                "top1": round(float(top1_threshold), 2),
                "margin": round(float(margin_threshold), 2),
                "accepted": len(accepted),
                "accept_rate": round(len(accepted) / len(calibration_rows), 4) if calibration_rows else 0.0,
                "accepted_accuracy": round(correct / len(accepted), 4) if accepted else None,
                "wilson_95_lower": round(wilson_lower(correct, len(accepted)), 4),
            })

    eligible = [
        point for point in sweep
        if point["accepted"] >= MIN_CALIBRATION_ACCEPTS
        and point["accepted_accuracy"] is not None
        and point["accepted_accuracy"] >= TARGET_ACCEPTED_ACCURACY
    ]
    fixed_accepted = [
        row for row in calibration_rows
        if row["prediction"] not in weak_classes
        and not row["guard_reason"]
        and row["top1"] >= RELEASE_TOP1
        and row["margin"] >= RELEASE_MARGIN
    ]
    fixed_correct = sum(row["correct"] for row in fixed_accepted)
    selected = {
        "top1": RELEASE_TOP1,
        "margin": RELEASE_MARGIN,
        "accepted": len(fixed_accepted),
        "accept_rate": round(len(fixed_accepted) / len(calibration_rows), 4) if calibration_rows else 0.0,
        "accepted_accuracy": round(fixed_correct / len(fixed_accepted), 4) if fixed_accepted else None,
        "wilson_95_lower": round(wilson_lower(fixed_correct, len(fixed_accepted)), 4),
    }
    selection_reason = "user-approved staged release threshold; weak classes and ambiguity guards still require review"

    for row in rows:
        if row["source"] in {"business_rule", "product_lookup"}:
            decision, reason = "auto_accept", ""
        elif row["direction"] == "VENTAS":
            decision, reason = "review_required", "unknown_sales_item"
        elif row["guard_reason"]:
            decision, reason = "review_required", row["guard_reason"]
        elif row["prediction"] in weak_classes:
            decision, reason = "review_required", "weak_class"
        elif row["top1"] < selected["top1"]:
            decision, reason = "review_required", "low_confidence"
        elif row["margin"] < selected["margin"]:
            decision, reason = "review_required", "small_margin"
        else:
            decision, reason = "auto_accept", ""
        row["decision"] = decision
        row["reason"] = reason

    accepted = [row for row in rows if row["decision"] == "auto_accept"]
    false_positives = [row for row in accepted if not row["correct"]]
    review = [row for row in rows if row["decision"] == "review_required"]
    review_false_negatives = [row for row in review if row["correct"]]
    review_errors = [row for row in review if not row["correct"]]

    fields = [
        "gold_id", "truth", "prediction", "model_prediction", "source", "decision", "reason",
        "correct", "top1", "margin", "direction", "item_text", "description", "provider",
        "lookup_conflict", "top3", "model_text",
        "guard_reason",
    ]
    args.report_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.report_dir / "validation_predictions.csv", rows, fields)
    write_csv(args.report_dir / "auto_accept_false_positives.csv", false_positives, fields)
    write_csv(args.report_dir / "review_false_negatives.csv", review_false_negatives, fields)
    write_csv(args.report_dir / "review_errors.csv", review_errors, fields)

    report = {
        "inference_backend": backend,
        "locked_validation_rows": len(rows),
        "classes": len(classes),
        "weak_classes_lt15_distinct": sorted(weak_classes),
        "weak_class_distinct_counts": {code: distinct_counts.get(code, 0) for code in sorted(weak_classes)},
        "calibration_model_purchase_rows": len(calibration_rows),
        "target_accepted_accuracy": TARGET_ACCEPTED_ACCURACY,
        "selected_thresholds": {
            "accept_top1": selected["top1"],
            "accept_margin": selected["margin"],
            "model_auto_accept": True,
        },
        "selected_calibration_point": selected,
        "selection_reason": selection_reason,
        "cascade": {
            "source_counts": dict(sorted(Counter(row["source"] for row in rows).items())),
            "decision_counts": dict(sorted(Counter(row["decision"] for row in rows).items())),
            "reason_counts": dict(sorted(Counter(row["reason"] or "accepted" for row in rows).items())),
            "auto_accept_rows": len(accepted),
            "auto_accept_rate": round(len(accepted) / len(rows), 4),
            "auto_accept_correct": len(accepted) - len(false_positives),
            "auto_accept_false_positives": len(false_positives),
            "auto_accept_precision": round((len(accepted) - len(false_positives)) / len(accepted), 4) if accepted else None,
            "review_rows": len(review),
            "review_correct_predictions_false_negatives": len(review_false_negatives),
            "review_misclassifications": len(review_errors),
        },
        "false_positive_by_source": dict(sorted(Counter(row["source"] for row in false_positives).items())),
        "false_positive_by_truth": dict(sorted(Counter(row["truth"] for row in false_positives).items())),
        "review_false_negative_by_category": dict(sorted(Counter(row["truth"] for row in review_false_negatives).items())),
        "review_error_by_category": dict(sorted(Counter(row["truth"] for row in review_errors).items())),
        "threshold_sweep": sweep,
    }
    (args.report_dir / "calibration_and_validation_audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (args.report_dir / "selected_thresholds.json").write_text(
        json.dumps(report["selected_thresholds"], indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({key: report[key] for key in [
        "locked_validation_rows", "classes", "calibration_model_purchase_rows",
        "selected_thresholds", "selected_calibration_point", "selection_reason", "cascade",
        "false_positive_by_source", "review_false_negative_by_category", "review_error_by_category",
    ]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
