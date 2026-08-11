#!/usr/bin/env python3
"""Export the local v1.3.1 SetFit candidate to a parity-gated ONNX artifact."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "models/setfit_base_recovery_v1_3_1"
GOLD = ROOT / "Data/candidates/recovery_v1_3_1/master_gold.csv"
SPLIT = ROOT / "Data/candidates/recovery_v1_3_1/split_seed42.csv"
THRESHOLDS = ROOT / "reports/recovery_v1_3_1/selected_thresholds.json"
OUTPUT = ROOT / "artifacts/v1.3.1"
TAXONOMY = ROOT / "Data/current_context_2026_06_30/taxonomy_from_plan.csv"
EXCLUDED = ROOT / "Data/current_context_2026_06_30/excluded_categories.csv"
BASE_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mean_pool(last_hidden: np.ndarray, mask: np.ndarray) -> np.ndarray:
    expanded = mask[..., None].astype(np.float32)
    return (last_hidden * expanded).sum(1) / np.clip(expanded.sum(1), 1e-9, None)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, default=MODEL)
    parser.add_argument("--gold", type=Path, default=GOLD)
    parser.add_argument("--split", type=Path, default=SPLIT)
    parser.add_argument("--thresholds", type=Path, default=THRESHOLDS)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--version", default="v1.3.1")
    args = parser.parse_args()

    protected = {(ROOT / "artifacts/v1.0.0").resolve(), (ROOT / "artifacts/v1.1.0").resolve()}
    if args.output.resolve() in protected:
        raise SystemExit("refusing to overwrite protected baseline artifact")
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite existing artifact: {args.output}")

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    import joblib
    from sentence_transformers import SentenceTransformer

    body = SentenceTransformer(
        str(args.model.resolve()),
        tokenizer_kwargs={"fix_mistral_regex": False},
    )
    head = joblib.load(args.model / "model_head.pkl")
    classes = [str(value) for value in head.classes_]
    run = json.loads((args.model / "run_manifest.json").read_text())
    thresholds = json.loads(args.thresholds.read_text())
    split = read_csv(args.split)
    validation = [row for row in split if row["split"] == "validation"]
    if not validation:
        raise RuntimeError("locked split contains no validation rows")

    args.output.mkdir(parents=True)
    tmp = ROOT / "models/_onnx_tmp_recovery_v1_3_1"
    if tmp.exists():
        shutil.rmtree(tmp)
    subprocess.run([
        sys.executable, "-m", "optimum.exporters.onnx",
        "--model", str(args.model.resolve()),
        "--task", "feature-extraction",
        str(tmp),
    ], check=True, env={**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"})

    from onnxruntime.quantization import QuantType, quantize_dynamic

    quantize_dynamic(
        model_input=str(tmp / "model.onnx"),
        model_output=str(args.output / "model.onnx"),
        weight_type=QuantType.QInt8,
    )
    tokenizer_dir = args.output / "tokenizer"
    tokenizer_dir.mkdir()
    for path in tmp.iterdir():
        if path.name != "model.onnx" and path.is_file():
            shutil.copy(path, tokenizer_dir / path.name)
    shutil.rmtree(tmp)
    joblib.dump(head, args.output / "classifier.joblib")

    taxonomy = read_csv(TAXONOMY)
    excluded = read_csv(EXCLUDED)
    split_counts = Counter(row["category_code"] for row in split)
    labels = []
    for row in taxonomy:
        code = row["new_code"]
        count = split_counts.get(code, 0)
        labels.append({
            "code": code,
            "parent": row["parent"],
            "name": row["leaf"],
            "trained": code in classes,
            "weak": count < 15,
            "gold_examples": count,
        })
    (args.output / "labels.json").write_text(json.dumps({
        "classifier_classes": classes,
        "labels": labels,
        "excluded_categories": [row["leaf"] for row in excluded],
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (args.output / "taxonomy.json").write_text(json.dumps(taxonomy, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    shutil.copy(ROOT / "training/provider_giro_map.csv", args.output / "provider_giro_map.csv")

    import onnxruntime as ort
    from sklearn.metrics import accuracy_score, f1_score
    from transformers import AutoTokenizer

    texts = [row["text"] for row in validation]
    truth = [row["category_code"] for row in validation]
    reference_embeddings = body.encode(texts, batch_size=32, convert_to_numpy=True, show_progress_bar=False)
    tokenizer = AutoTokenizer.from_pretrained(
        str(tokenizer_dir), local_files_only=True, fix_mistral_regex=False
    )
    session = ort.InferenceSession(str(args.output / "model.onnx"), providers=["CPUExecutionProvider"])
    input_names = {item.name for item in session.get_inputs()}
    onnx_embeddings = []
    max_length = int(body.max_seq_length)
    for start in range(0, len(texts), 32):
        encoded = tokenizer(
            texts[start:start + 32],
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors="np",
        )
        hidden = session.run(None, {key: value for key, value in encoded.items() if key in input_names})[0]
        onnx_embeddings.append(mean_pool(hidden, encoded["attention_mask"]))
    onnx_embeddings = np.vstack(onnx_embeddings)
    cosine = np.sum(reference_embeddings * onnx_embeddings, axis=1) / (
        np.linalg.norm(reference_embeddings, axis=1) * np.linalg.norm(onnx_embeddings, axis=1)
    )
    reference_predictions = head.predict(reference_embeddings)
    onnx_predictions = head.predict(onnx_embeddings)
    disagreement = float(np.mean(reference_predictions != onnx_predictions))
    reference_accuracy = float(accuracy_score(truth, reference_predictions))
    onnx_accuracy = float(accuracy_score(truth, onnx_predictions))
    onnx_macro_f1 = float(f1_score(truth, onnx_predictions, average="macro", zero_division=0))
    if cosine.mean() < 0.99 or disagreement >= 0.03 or reference_accuracy - onnx_accuracy > 0.02:
        shutil.rmtree(args.output)
        raise SystemExit(
            f"parity gate failed: cosine={cosine.mean():.5f}, disagreement={disagreement:.4%}, "
            f"accuracy_drop={reference_accuracy - onnx_accuracy:+.4f}; candidate artifact removed"
        )

    gold_rows = read_csv(args.gold)
    card = {
        "model_version": args.version,
        "variant": "base_transaction_aware",
        "base_model": BASE_MODEL,
        "framework": "SetFit full-encoder contrastive fine-tune + sklearn LogisticRegression head",
        "artifact_format": "onnx-int8-dynamic (QInt8 weights; CPU deployment)",
        "trained_date": str(date.today()),
        "trained_classes": len(classes),
        "input_construction": {
            "template": "[transaction_type] | item_text | description | provider",
            "transaction_type_required": True,
            "rules": [
                "transaction_type is COMPRAS or VENTAS from the source DTE folder",
                "join non-empty fields with ' | '",
                "drop numeric-only description/product codes",
            ],
            "pooling": "mean pooling over last_hidden_state with attention mask, no L2 normalization",
            "max_length": max_length,
        },
        "thresholds": thresholds,
        "decision_policy": (
            "meter, taxonomy/alias, and client product lookups auto-accept; model-only inputs auto-accept "
            "only at top1 >= 0.75 and margin >= 0.50 outside weak classes and ambiguity guards"
        ),
        "metrics": run["metrics"],
        "excluded_untrained": run["excluded_lt2_classes"],
        "weak_classes_lt15_distinct": sorted(row["code"] for row in labels if row["weak"]),
        "parity_gate": {
            "cosine_mean": round(float(cosine.mean()), 5),
            "cosine_min": round(float(cosine.min()), 5),
            "top1_disagreement": round(disagreement, 5),
            "val_accuracy_torch_fp32": round(reference_accuracy, 4),
            "val_accuracy_int8_onnx": round(onnx_accuracy, 4),
            "val_macro_f1_int8_onnx": round(onnx_macro_f1, 4),
        },
        "gold_provenance_rows": len(gold_rows),
        "gold_distinct_model_inputs": len(split),
        "seed": run.get("seed", 42),
        "training_guards": {
            "full_encoder_trainable": run["full_encoder_trainable"],
            "trainable_encoder_parameters": run["trainable_encoder_parameters"],
            "total_encoder_parameters": run["total_encoder_parameters"],
            "tracked_token_embedding_max_abs_delta": run["tracked_token_embedding_max_abs_delta"],
            "fixed_length_padding": run["fixed_length_padding"],
            "optimizer": run["optimizer_observed"],
        },
    }
    (args.output / "model_card.json").write_text(json.dumps(card, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    shutil.copy(ROOT / "training/inference_example.py", args.output / "inference_example.py")
    card["artifacts_sha256"] = {
        str(path.relative_to(args.output)): sha256(path)
        for path in sorted(args.output.rglob("*"))
        if path.is_file() and path.name != "model_card.json"
    }
    (args.output / "model_card.json").write_text(json.dumps(card, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "artifact": str(args.output),
        "classes": len(classes),
        "thresholds": thresholds,
        "parity_gate": card["parity_gate"],
    }, indent=2))


if __name__ == "__main__":
    main()
