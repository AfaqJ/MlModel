#!/usr/bin/env python3
"""Score several classifier builds on the same locked test rows.

Each `--model NAME=PATH` is either a SetFit directory (PyTorch, run in
.venv-train) or an exported artifact directory containing `model.onnx` — the
INT8 file Cloud Run actually serves. Only the model is scored: no lookups, no
rules, no familiarity gate. The COMPRAS/VENTAS mask is applied exactly as the
service applies it, and the auto-accept numbers use the unchanged 0.75/0.50
thresholds outside each model's weak classes.

A test row whose category the model cannot emit counts as wrong.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.inference.business_rules import direction_mask

ACCEPT_TOP1, ACCEPT_MARGIN, WEAK_BELOW = 0.75, 0.50, 15


def load(path: Path):
    """Return (predict_proba(texts) -> ndarray, classes, weak_classes)."""
    if (path / "model.onnx").exists():
        from app.inference.classifier import LogisticHead
        from app.inference.onnx_encoder import OnnxEncoder

        encoder, head = OnnxEncoder(path), LogisticHead(path)
        weak = set(json.loads((path / "model_card.json").read_text()).get("weak_classes_lt15_distinct", []))
        return lambda texts: head.predict_proba(encoder.embed(texts)), [str(c) for c in head.classes_], weak

    # Load the SetFit directory without SetFit/SentenceTransformers: their saved
    # module configs differ across library versions, while the maths the
    # service runs is fixed — transformer, attention-masked mean pooling, no L2
    # normalisation, logistic head (model_card input_construction).
    import joblib
    import torch
    from transformers import AutoModel, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(str(path))
    body = AutoModel.from_pretrained(str(path)).eval()
    head = joblib.load(path / "model_head.pkl")
    counts = json.loads((path / "run_manifest.json").read_text())["train_class_counts"]
    weak = {code for code, count in counts.items() if count < WEAK_BELOW}

    def predict(texts):
        pooled = []
        with torch.no_grad():
            for start in range(0, len(texts), 64):
                enc = tokenizer(texts[start:start + 64], padding=True, truncation=True, max_length=64, return_tensors="pt")
                hidden = body(**enc).last_hidden_state
                mask = enc["attention_mask"].unsqueeze(-1).float()
                pooled.append(((hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-9)).numpy())
        return head.predict_proba(np.vstack(pooled))

    return predict, [str(c) for c in head.classes_], weak


def score(rows, proba, classes, weak) -> dict:
    from sklearn.metrics import f1_score

    truth = [row["category_code"] for row in rows]
    predictions, top3, accepted = [], [], []
    for row, p in zip(rows, proba):
        p = p.copy()
        masked = direction_mask(classes, row["direction"])
        p[masked] = 0.0
        p = p / p.sum() if p.sum() > 0 else p
        order = [int(i) for i in np.argsort(-p) if i not in set(masked)]
        predictions.append(classes[order[0]])
        top3.append([classes[i] for i in order[:3]])
        top1, top2 = float(p[order[0]]), float(p[order[1]]) if len(order) > 1 else 0.0
        accepted.append(top1 >= ACCEPT_TOP1 and top1 - top2 >= ACCEPT_MARGIN and classes[order[0]] not in weak)

    def block(indices):
        if not indices:
            return None
        acc = [truth[i] == predictions[i] for i in indices]
        auto = [i for i in indices if accepted[i]]
        return {
            "rows": len(indices),
            "accuracy": round(float(np.mean(acc)), 4),
            "macro_f1": round(float(f1_score([truth[i] for i in indices], [predictions[i] for i in indices],
                                             labels=sorted({truth[i] for i in indices}), average="macro",
                                             zero_division=0)), 4),
            "top3_accuracy": round(float(np.mean([truth[i] in top3[i] for i in indices])), 4),
            "auto_accept_rate": round(len(auto) / len(indices), 4),
            "auto_accept_precision": round(float(np.mean([truth[i] == predictions[i] for i in auto])), 4) if auto else None,
            "auto_accept_wrong": sum(1 for i in auto if truth[i] != predictions[i]),
        }

    everything = list(range(len(rows)))
    per_class = {}
    for code in sorted(set(truth)):
        indices = [i for i in everything if truth[i] == code]
        per_class[code] = {"support": len(indices), "recall": round(float(np.mean([predictions[i] == code for i in indices])), 4)}
    return {
        "all": block(everything),
        "income": block([i for i in everything if truth[i].startswith("ING-")]),
        "old_v1_3_3_validation": block([i for i in everything if rows[i]["previously"] == "validation"]),
        "new_rows": block([i for i in everything if rows[i]["previously"] != "validation"]),
        "rows_with_class_unknown_to_model": sum(1 for code in truth if code not in classes),
        "per_class": per_class,
        "predictions": predictions,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", type=Path, default=ROOT / "Data/candidates/retrain_2026_09_15/split.csv")
    parser.add_argument("--model", action="append", required=True, help="NAME=PATH, repeatable")
    parser.add_argument("--report-dir", type=Path, default=ROOT / "reports/retrain_2026_09_15")
    args = parser.parse_args()

    with args.split.open(encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["split"] == "test"]
    for row in rows:
        row["direction"] = row["text"].split("]", 1)[0].lstrip("[")
    texts = [row["text"] for row in rows]

    results = {}
    for spec in args.model:
        name, path = spec.split("=", 1)
        predict, classes, weak = load(Path(path))
        results[name] = score(rows, predict(texts), classes, weak)
        print(name, json.dumps(results[name]["all"]))

    args.report_dir.mkdir(parents=True, exist_ok=True)
    with (args.report_dir / "test_predictions.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["gold_id", "previously", "truth", *results, "text"])
        for i, row in enumerate(rows):
            writer.writerow([row["gold_id"], row["previously"], row["category_code"],
                             *(r["predictions"][i] for r in results.values()), row["text"]])
    for r in results.values():
        r.pop("predictions")
    (args.report_dir / "evaluation.json").write_text(json.dumps(results, indent=2) + "\n")

    names = list(results)
    lines = ["| slice | metric | " + " | ".join(names) + " |", "|---|---|" + "---|" * len(names)]
    for slice_name in ["all", "income", "old_v1_3_3_validation", "new_rows"]:
        for metric in ["rows", "accuracy", "macro_f1", "top3_accuracy", "auto_accept_rate", "auto_accept_precision", "auto_accept_wrong"]:
            values = [results[n][slice_name][metric] if results[n][slice_name] else "" for n in names]
            lines.append(f"| {slice_name} | {metric} | " + " | ".join(str(v) for v in values) + " |")
    lines.append("| all | rows_with_class_unknown_to_model | " + " | ".join(str(results[n]["rows_with_class_unknown_to_model"]) for n in names) + " |")
    (args.report_dir / "evaluation.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(Counter(row["previously"] for row in rows))


if __name__ == "__main__":
    main()
