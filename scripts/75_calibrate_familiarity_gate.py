#!/usr/bin/env python3
"""Calibrate and build the nearest-neighbour familiarity gate.

The gate exists because SetFit confidence cannot distinguish "this looks like
the training data for that class" from "the head had to pick something". This
script measures both sides of that trade on the locked validation split:

- cost: correct model auto-accepts the gate would push into review
  (new false negatives, i.e. extra client work);
- benefit: wrong model auto-accepts the gate would catch
  (the confident lies this whole pass is about).

The index is built from train rows only, exactly as production sees it, so a
validation row can never match itself.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.inference.business_rules import direction_mask  # noqa: E402
from app.inference.familiarity import FamiliarityIndex  # noqa: E402

DEFAULT_MODEL = ROOT / "models/setfit_base_recovery_v1_3_2"
DEFAULT_GOLD = ROOT / "Data/candidates/recovery_v1_3_2/master_gold.csv"
DEFAULT_SPLIT = ROOT / "Data/candidates/recovery_v1_3_2/split_seed42.csv"
DEFAULT_REPORT = ROOT / "reports/recovery_v1_3_2/familiarity_calibration.json"

K_GRID = (3, 5, 7, 10)
AGREEMENT_GRID = (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_model(path: Path):
    import transformers.training_args as training_args
    if not hasattr(training_args, "default_logdir"):
        from transformers.integrations.integration_utils import default_logdir
        training_args.default_logdir = default_logdir
    from setfit import SetFitModel

    return SetFitModel.from_pretrained(str(path), local_files_only=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--split", type=Path, default=DEFAULT_SPLIT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--accept-top1", type=float, default=0.75)
    parser.add_argument("--accept-margin", type=float, default=0.50)
    parser.add_argument(
        "--max-correct-loss",
        type=float,
        default=0.01,
        help="max fraction of correct model auto-accepts the gate may send to review",
    )
    parser.add_argument(
        "--pin",
        metavar="K,AGREEMENT",
        help=(
            "write this setting instead of the sweep's pick, e.g. 5,0.4. The sweep "
            "can select a gate that loses correct auto-accepts and catches nothing "
            "(v1.4.1: k=3/0.6 lost 3 and caught 0), which is strictly worse than no "
            "gate; pinning keeps the shipped setting when that happens."
        ),
    )
    parser.add_argument("--write-index", action="store_true")
    args = parser.parse_args()

    pinned = None
    if args.pin:
        k_text, agreement_text = args.pin.split(",")
        pinned = {"k": int(k_text), "min_agreement": float(agreement_text)}

    split_rows = read_csv(args.split)
    gold_by_id = {row["gold_id"]: row for row in read_csv(args.gold)}
    train = [row for row in split_rows if row["split"].startswith("train")]
    validation = [row for row in split_rows if row["split"] == "validation"]
    if not train or not validation:
        raise SystemExit("split manifest has no train/validation rows")

    distinct_by_label: defaultdict[str, set[str]] = defaultdict(set)
    for row in train:
        distinct_by_label[row["category_code"]].add(row["text_sha256"])
    weak_classes = {code for code, keys in distinct_by_label.items() if len(keys) < 15}

    model = load_model(args.model)
    classes = np.asarray([str(value) for value in model.labels])

    def embed(rows):
        return np.asarray(
            model.model_body.encode(
                [row["text"] for row in rows], batch_size=64,
                convert_to_numpy=True, show_progress_bar=False,
            )
        )

    train_embeddings = embed(train)
    validation_embeddings = embed(validation)
    train_labels = np.asarray([row["category_code"] for row in train], dtype=object)

    proba = np.asarray(model.model_head.predict_proba(validation_embeddings))

    # Reproduce the model-only decision the gate sits behind: direction mask,
    # weak-class veto, then the fixed 0.75/0.50 policy. Thresholds are not
    # touched by this script.
    candidates = []
    for index, row in enumerate(validation):
        direction = gold_by_id[row["gold_id"]]["direction"]
        scores = proba[index].copy()
        masked = direction_mask(classes, direction)
        if masked:
            scores[masked] = 0.0
            total = scores.sum()
            if total > 0:
                scores = scores / total
        order = np.argsort(-scores)
        if masked:
            blocked = set(masked)
            order = np.asarray([i for i in order if i not in blocked])
        code1 = str(classes[order[0]])
        top1 = float(scores[order[0]])
        margin = top1 - (float(scores[order[1]]) if len(order) > 1 else 0.0)
        if code1 in weak_classes or top1 < args.accept_top1 or margin < args.accept_margin:
            continue
        candidates.append({
            "gold_id": row["gold_id"],
            "truth": row["category_code"],
            "predicted": code1,
            "correct": code1 == row["category_code"],
            "top1": round(top1, 4),
            "margin": round(margin, 4),
            "embedding_index": index,
            "text": row["text"],
        })

    correct = [row for row in candidates if row["correct"]]
    wrong = [row for row in candidates if not row["correct"]]

    results = []
    for k in K_GRID:
        index = FamiliarityIndex(train_embeddings, train_labels, k=k, min_agreement=1.0)
        agreements = np.asarray([
            index.evaluate(validation_embeddings[row["embedding_index"]], row["predicted"]).agreement
            for row in candidates
        ])
        is_correct = np.asarray([row["correct"] for row in candidates])
        for threshold in AGREEMENT_GRID:
            rejected = agreements < threshold
            correct_lost = int(np.sum(rejected & is_correct))
            wrong_caught = int(np.sum(rejected & ~is_correct))
            results.append({
                "k": k,
                "min_agreement": threshold,
                "correct_auto_accepts_lost": correct_lost,
                "correct_loss_rate": round(correct_lost / len(correct), 4) if correct else 0.0,
                "wrong_auto_accepts_caught": wrong_caught,
                "wrong_total": len(wrong),
            })

    eligible = [
        row for row in results
        if row["correct_loss_rate"] <= args.max_correct_loss
    ]
    if not eligible:
        raise SystemExit(
            f"no (k, threshold) keeps correct loss at or below {args.max_correct_loss}; "
            "inspect the sweep before relaxing it"
        )
    # Selection is deliberately not "catch the most validation errors". Every
    # validation row is a gold row, so the split contains no out-of-distribution
    # input at all and cannot measure what this gate is for. Validation is used
    # only to bound the cost in extra review; among settings inside that budget
    # we take the strictest gate, and only break ties on validation catches.
    selected = sorted(
        eligible,
        key=lambda row: (-row["min_agreement"], -row["k"], -row["wrong_auto_accepts_caught"]),
    )[0]
    if pinned:
        selected = next(
            row for row in results
            if row["k"] == pinned["k"] and abs(row["min_agreement"] - pinned["min_agreement"]) < 1e-9
        )
        selected = {**selected, "pinned": True}

    report = {
        "model": str(args.model.relative_to(ROOT)),
        "train_rows_in_index": len(train),
        "validation_rows": len(validation),
        "weak_classes": sorted(weak_classes),
        "model_only_auto_accepts": len(candidates),
        "model_only_correct": len(correct),
        "model_only_wrong": len(wrong),
        "max_correct_loss": args.max_correct_loss,
        "selected": selected,
        "sweep": results,
        "wrong_auto_accepts": [
            {key: row[key] for key in ("gold_id", "truth", "predicted", "top1", "margin", "text")}
            for row in wrong
        ],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.write_index:
        FamiliarityIndex(
            train_embeddings, train_labels,
            k=selected["k"], min_agreement=selected["min_agreement"],
        ).save(args.model)
        print(f"wrote familiarity index into {args.model}")

    print(json.dumps({key: report[key] for key in (
        "model_only_auto_accepts", "model_only_correct", "model_only_wrong", "selected"
    )}, indent=2))


if __name__ == "__main__":
    main()
