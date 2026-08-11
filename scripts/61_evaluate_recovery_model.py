#!/usr/bin/env python3
"""Compare the local recovery SetFit model with v1.1 on the locked split."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics import accuracy_score, classification_report, f1_score


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPLIT = ROOT / "Data/candidates/recovery_v1_3_1/split_seed42.csv"
DEFAULT_CANDIDATE = ROOT / "models/setfit_base_recovery_v1_3_1"
DEFAULT_PREVIOUS = ROOT / "models/setfit_base_recovery_v1_2_0"
PREVIOUS_SPLIT = ROOT / "Data/candidates/recovery_v1_2_0/split_seed42.csv"
DEFAULT_BASELINE = ROOT / "models/setfit_base"
DEFAULT_REPORT = ROOT / "reports/recovery_v1_3_1/model_comparison_fair.json"
ORIGINAL_GOLD = ROOT / "Data/gold/_master_gold.backup_20260811_104643.csv"
BASELINE_VALIDATION = DEFAULT_BASELINE / "val_split.csv"
NUMERIC_RE = re.compile(r"[\d\s.,\-/]+$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_validation(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["split"] == "validation"]
    if not rows:
        raise RuntimeError(f"no validation rows in {path}")
    hashes = [row["text_sha256"] for row in rows]
    if len(hashes) != len(set(hashes)):
        raise RuntimeError("locked validation split contains duplicate normalized model inputs")
    return rows


def normalize(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", (value or "").lower())
    value = value.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def build_text(row: dict[str, str]) -> str:
    description = (row.get("description") or "").strip()
    if not description or NUMERIC_RE.fullmatch(description):
        description = ""
    return " | ".join(
        value
        for value in (
            (row.get("item_text") or "").strip(),
            description,
            (row.get("provider") or "").strip(),
        )
        if value
    )


def build_shared_blind_rows(
    split_path: Path,
    *,
    require_previous_recovery_blind: bool,
) -> tuple[list[dict[str, str]], dict]:
    """Rows held out by v1.1 and absent from the candidate's training split.

    v1.1's validation itself leaked duplicate model inputs. Requiring the input
    to occur once in the original gold removes any possible duplicate copy from
    v1.1 training. Requiring absence from the candidate train hashes makes the
    resulting subset blind for both models.
    """
    original = read_csv(ORIGINAL_GOLD)
    original_frequency = Counter(normalize(build_text(row)) for row in original)
    candidate_split = read_csv(split_path)
    candidate_train_hashes = {
        row["text_sha256"]
        for row in candidate_split
        if row["split"].startswith("train")
    }
    previous_train_hashes = {
        row["text_sha256"]
        for row in read_csv(PREVIOUS_SPLIT)
        if row["split"].startswith("train")
    }
    baseline_validation = read_csv(BASELINE_VALIDATION)
    kept = []
    excluded = Counter()
    seen = set()
    for row in baseline_validation:
        key = normalize(row["text"])
        text_hash = hashlib.sha256(key.encode()).hexdigest()
        direction = "VENTAS" if row["label"].startswith("ING-") else "COMPRAS"
        candidate_text = f"[{direction}] | {row['text']}"
        candidate_hash = hashlib.sha256(normalize(candidate_text).encode()).hexdigest()
        if key in seen:
            excluded["duplicate_in_v1_1_validation"] += 1
            continue
        seen.add(key)
        if original_frequency[key] != 1:
            excluded["not_unique_in_original_gold"] += 1
            continue
        if require_previous_recovery_blind and text_hash in previous_train_hashes:
            excluded["present_in_previous_recovery_training"] += 1
            continue
        if candidate_hash in candidate_train_hashes:
            excluded["present_in_candidate_training"] += 1
            continue
        kept.append({
            "text": row["text"],
            "candidate_text": candidate_text,
            "category_code": row["label"],
        })
    return kept, {
        "v1_1_validation_rows": len(baseline_validation),
        "shared_blind_rows": len(kept),
        "excluded": dict(sorted(excluded.items())),
        "income_rows": sum(row["category_code"].startswith("ING-") for row in kept),
        "previous_recovery_blind_required": require_previous_recovery_blind,
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def evaluate_model(
    model_dir: Path,
    rows: list[dict[str, str]],
    device: str,
    text_field: str = "text",
) -> dict:
    model_dir = model_dir.resolve()
    # Transformers 4.57.6 emits a Mistral-regex warning for locally saved
    # XLM-R tokenizers because their detection branch only exempts <=4.57.2.
    # Explicit False preserves the XLM-R pre-tokenizer and suppresses that
    # inapplicable warning; True would incorrectly replace it with Mistral's.
    body = SentenceTransformer(
        str(model_dir),
        device=device,
        tokenizer_kwargs={"fix_mistral_regex": False},
    )
    head = joblib.load(model_dir / "model_head.pkl")
    classes = [str(value) for value in head.classes_]
    texts = [row[text_field] for row in rows]
    truth = [row["category_code"] for row in rows]
    embeddings = body.encode(texts, batch_size=64, show_progress_bar=False)
    probabilities = np.asarray(head.predict_proba(embeddings))
    ranked = np.argsort(-probabilities, axis=1)
    predictions = [classes[index] for index in ranked[:, 0]]
    top3 = [[classes[index] for index in order[:3]] for order in ranked]

    def slice_metrics(indices: list[int]) -> dict:
        if not indices:
            return {"rows": 0, "accuracy": None, "top3_accuracy": None}
        return {
            "rows": len(indices),
            "accuracy": round(float(np.mean([truth[i] == predictions[i] for i in indices])), 4),
            "top3_accuracy": round(float(np.mean([truth[i] in top3[i] for i in indices])), 4),
        }

    report = classification_report(truth, predictions, output_dict=True, zero_division=0)
    income_indices = [i for i, label in enumerate(truth) if label.startswith("ING-")]
    expense_indices = [i for i, label in enumerate(truth) if not label.startswith("ING-")]
    return {
        "model_dir": str(model_dir.relative_to(ROOT)),
        "classes": len(classes),
        "trained_income_classes": sorted(label for label in classes if label.startswith("ING-")),
        "validation_rows": len(rows),
        "accuracy": round(float(accuracy_score(truth, predictions)), 4),
        "macro_f1": round(float(f1_score(truth, predictions, average="macro", zero_division=0)), 4),
        "top3_accuracy": round(float(np.mean([label in choices for label, choices in zip(truth, top3)])), 4),
        "income": slice_metrics(income_indices),
        "non_income": slice_metrics(expense_indices),
        "per_class": {
            label: {
                "precision": round(values["precision"], 4),
                "recall": round(values["recall"], 4),
                "f1": round(values["f1-score"], 4),
                "support": int(values["support"]),
            }
            for label, values in report.items()
            if label not in {"accuracy", "macro avg", "weighted avg"}
        },
        "prediction_counts": dict(sorted(Counter(predictions).items())),
        "artifacts_sha256": {
            "model.safetensors": sha256(model_dir / "model.safetensors"),
            "model_head.pkl": sha256(model_dir / "model_head.pkl"),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", type=Path, default=DEFAULT_SPLIT)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--previous", type=Path, default=DEFAULT_PREVIOUS)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--device", choices=["mps", "cpu"], default="mps")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    locked_rows = load_validation(args.split)
    shared_rows, shared_audit = build_shared_blind_rows(
        args.split,
        require_previous_recovery_blind=False,
    )
    if len(shared_rows) < 50:
        raise RuntimeError(f"v1.1/candidate shared blind comparison is too small: {len(shared_rows)} rows")
    three_way_rows, three_way_audit = build_shared_blind_rows(
        args.split,
        require_previous_recovery_blind=True,
    )
    baseline = evaluate_model(args.baseline, shared_rows, args.device)
    candidate = evaluate_model(args.candidate, shared_rows, args.device, text_field="candidate_text")
    three_way = None
    if three_way_rows:
        three_way = {
            "warning": "descriptive only; too few genuinely blind rows for a release claim",
            "sufficient_for_release_claim": len(three_way_rows) >= 50,
            "baseline": evaluate_model(args.baseline, three_way_rows, args.device),
            "previous_recovery": evaluate_model(args.previous, three_way_rows, args.device),
            "candidate": evaluate_model(
                args.candidate,
                three_way_rows,
                args.device,
                text_field="candidate_text",
            ),
        }
    candidate_run = json.loads((args.candidate / "run_manifest.json").read_text())
    candidate_locked = candidate_run["metrics"]
    comparison = {
        "locked_split": str(args.split.relative_to(ROOT)),
        "locked_split_sha256": sha256(args.split),
        "candidate_locked_validation": candidate_locked,
        "candidate_locked_truth_class_counts": dict(
            sorted(Counter(row["category_code"] for row in locked_rows).items())
        ),
        "shared_blind_audit": shared_audit,
        "shared_blind_truth_class_counts": dict(
            sorted(Counter(row["category_code"] for row in shared_rows).items())
        ),
        "shared_blind_baseline": baseline,
        "shared_blind_candidate": candidate,
        "shared_blind_deltas": {
            key: round(candidate[key] - baseline[key], 4)
            for key in ("accuracy", "macro_f1", "top3_accuracy")
        },
        "three_model_blind_audit": three_way_audit,
        "three_model_blind_descriptive_only": three_way,
        "release_checks": {
            "shared_blind_candidate_beats_baseline_accuracy": candidate["accuracy"] > baseline["accuracy"],
            "shared_blind_candidate_beats_baseline_macro_f1": candidate["macro_f1"] > baseline["macro_f1"],
            "shared_blind_candidate_beats_baseline_top3": candidate["top3_accuracy"] > baseline["top3_accuracy"],
            "candidate_locked_accuracy_at_least_70_percent": candidate_locked["accuracy"] >= 0.70,
            "candidate_locked_income_accuracy_at_least_90_percent": candidate_locked["income"]["accuracy"] >= 0.90,
        },
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(comparison, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({
        "shared_blind_audit": shared_audit,
        "baseline": {key: baseline[key] for key in ("accuracy", "macro_f1", "top3_accuracy")},
        "candidate": {key: candidate[key] for key in ("accuracy", "macro_f1", "top3_accuracy")},
        "shared_blind_deltas": comparison["shared_blind_deltas"],
        "three_model_blind_audit": three_way_audit,
        "three_model_blind_descriptive_only": None if three_way is None else {
            "warning": three_way["warning"],
            "sufficient_for_release_claim": three_way["sufficient_for_release_claim"],
            "baseline": {key: three_way["baseline"][key] for key in ("accuracy", "macro_f1", "top3_accuracy")},
            "previous_recovery": {key: three_way["previous_recovery"][key] for key in ("accuracy", "macro_f1", "top3_accuracy")},
            "candidate": {key: three_way["candidate"][key] for key in ("accuracy", "macro_f1", "top3_accuracy")},
        },
        "candidate_locked_validation": {
            key: candidate_locked[key] for key in ("validation_rows", "accuracy", "macro_f1", "top3_accuracy", "income")
        },
        "release_checks": comparison["release_checks"],
        "report": str(args.report),
    }, indent=2))


if __name__ == "__main__":
    main()
