#!/usr/bin/env python3
"""Export a local SetFit candidate to a parity-gated ONNX artifact.

FP32 BY DEFAULT, AND WHY
------------------------
FP32 is the reference: it reproduces the trained SetFit encoder exactly (cosine
1.0, zero threshold-decision disagreement) and is what the gate defaults to
demanding. INT8 is roughly a quarter of the size but perturbs decisions, so it
is never silently substituted.

Measured on the v1_3_2 weights, INT8 vs the FP32 reference:
  cosine 0.99005 · top-1 disagreement 6.41% (20/312) ·
  threshold-decision disagreement 4.81% (15/312) · val accuracy 0.7532 -> 0.7468
Of those 15 decision flips, 13 are auto-accept -> review (safe: more review, no
bad data) and 2 are review -> auto-accept, both of which were correct. No new
false positive appeared on the locked split.

Both ceilings are therefore explicit, defaulted tight, and recorded in
model_card.json: `--allow-top1-disagreement` (default 0.03) and
`--allow-threshold-decision-disagreement` (default 0.0). Shipping INT8 requires
raising both on the command line, so the trade is always a deliberate act with
the measured cost written into the artifact. The reason it is taken here is
memory: FP32 peaks at 1.92 GiB and is OOM-killed in the 2 GiB Cloud Run
instance this service runs on.

The export deliberately runs across two interpreters. The parent must be an
environment whose sentence-transformers can read the trained model directory;
ONNX_TOOLS_PYTHON points at the environment that owns the optimum exporter.
No package download or model conversion happens outside those two.
"""
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
# The v1.3.3 release stamp is carried by the v1_3_2 weights; that pairing is
# intentional and recorded in docs/HANDOVER_v1.3.3.md.
MODEL = ROOT / "models/setfit_base_recovery_v1_3_2"
GOLD = ROOT / "Data/candidates/recovery_v1_3_2/master_gold.csv"
SPLIT = ROOT / "Data/candidates/recovery_v1_3_2/split_seed42.csv"
THRESHOLDS = ROOT / "reports/recovery_v1_3_2/selected_thresholds.json"
OUTPUT = ROOT / "artifacts/v1.3.3"
VERSION = "v1.3.3"
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


def masked_probabilities(probabilities: np.ndarray, classes: list[str], texts: list[str]) -> np.ndarray:
    """Apply the same transaction-direction defense used by the backend."""
    result = probabilities.copy()
    for index, text in enumerate(texts):
        direction = "VENTAS" if text.startswith("[VENTAS]") else "COMPRAS"
        impossible = [
            class_index for class_index, code in enumerate(classes)
            if (direction == "COMPRAS" and code.startswith("ING-"))
            or (direction == "VENTAS" and not code.startswith("ING-"))
        ]
        result[index, impossible] = 0.0
        total = result[index].sum()
        if total > 0:
            result[index] /= total
    return result


def model_acceptance(probabilities: np.ndarray, classes: list[str], weak: set[str], thresholds: dict) -> np.ndarray:
    accepted = []
    for row in probabilities:
        order = np.argsort(-row)
        top1 = float(row[order[0]])
        top2 = float(row[order[1]]) if len(order) > 1 else 0.0
        code = classes[order[0]]
        accepted.append(
            code not in weak
            and top1 >= float(thresholds["accept_top1"])
            and top1 - top2 >= float(thresholds["accept_margin"])
            and thresholds.get("model_auto_accept") is not False
        )
    return np.asarray(accepted, dtype=bool)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, default=MODEL)
    parser.add_argument("--gold", type=Path, default=GOLD)
    parser.add_argument("--split", type=Path, default=SPLIT)
    parser.add_argument("--thresholds", type=Path, default=THRESHOLDS)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--version", default=VERSION)
    parser.add_argument(
        "--quantize",
        choices=["none", "int8"],
        default="none",
        help="none ships FP32 (default); int8 is smaller but perturbs threshold decisions",
    )
    parser.add_argument(
        "--allow-top1-disagreement",
        type=float,
        default=0.03,
        metavar="FRACTION",
        help="ceiling on rows whose top-1 category differs from the FP32 reference (default 0.03)",
    )
    parser.add_argument(
        "--allow-threshold-decision-disagreement",
        type=float,
        default=0.0,
        metavar="FRACTION",
        help=(
            "deliberately accept a non-zero fraction of flipped auto-accept/review decisions "
            "versus the FP32 reference. Default 0.0 refuses any. Must be passed explicitly; "
            "the measured value is recorded in model_card.json"
        ),
    )
    args = parser.parse_args()

    protected = {(ROOT / "artifacts/v1.0.0").resolve(), (ROOT / "artifacts/v1.1.0").resolve()}
    if args.output.resolve() in protected:
        raise SystemExit("refusing to overwrite protected baseline artifact")
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite existing artifact: {args.output}")

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    # This process deliberately never imports torch or onnxruntime. Both sides
    # of the parity comparison are produced by subprocesses that write .npy
    # files; see training/torch_reference_embed.py for what happens when the
    # heavy runtimes and the comparison arithmetic share one interpreter.
    import joblib

    # Refuse before doing 20 minutes of work: a missing index means the runtime
    # familiarity gate would silently disable itself, and the model_loader now
    # refuses to boot without it.
    familiarity_index = args.model / "familiarity_index.npz"
    if not familiarity_index.exists():
        raise SystemExit(
            f"familiarity index missing: {familiarity_index}\n"
            "run scripts/75_calibrate_familiarity_gate.py --write-index first"
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
    tmp = ROOT / f"models/_onnx_tmp_recovery_{args.version.replace('.', '_')}"
    if tmp.exists():
        shutil.rmtree(tmp)
    onnx_tools_python = Path(
        os.environ.get("ONNX_TOOLS_PYTHON", ROOT / ".venv-train/bin/python")
    )
    if not onnx_tools_python.exists():
        onnx_tools_python = Path(sys.executable)
    subprocess.run([
        str(onnx_tools_python), "-m", "optimum.exporters.onnx",
        "--model", str(args.model.resolve()),
        "--task", "feature-extraction",
        "--library-name", "transformers",
        str(tmp),
    ], check=True, env={**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"})

    if args.quantize == "int8":
        # The training environment owns the local quantizer; keeping this as a
        # subprocess lets the parent process load the trained model while the
        # Python 3.11 tools emit the portable artifact. Kept for measurement
        # only — this is what the gate refused for this generation.
        subprocess.run([
            str(onnx_tools_python),
            "-c",
            (
                "from onnxruntime.quantization import QuantType, quantize_dynamic; "
                "import sys; quantize_dynamic(model_input=sys.argv[1], "
                "model_output=sys.argv[2], weight_type=QuantType.QInt8)"
            ),
            str(tmp / "model.onnx"),
            str(args.output / "model.onnx"),
        ], check=True)
    else:
        shutil.move(str(tmp / "model.onnx"), str(args.output / "model.onnx"))
    tokenizer_dir = args.output / "tokenizer"
    tokenizer_dir.mkdir()
    for path in tmp.iterdir():
        if path.name != "model.onnx" and path.is_file():
            shutil.copy(path, tokenizer_dir / path.name)
    shutil.rmtree(tmp)
    joblib.dump(head, args.output / "classifier.joblib")
    # The kNN familiarity gate is part of the decision path, so its index is
    # part of the artifact. Shipping the model without it would quietly change
    # what the service accepts.
    shutil.copy(familiarity_index, args.output / familiarity_index.name)

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

    from sklearn.metrics import accuracy_score, f1_score

    texts = [row["text"] for row in validation]
    truth = [row["category_code"] for row in validation]

    # Preferring the deployment virtualenv means the artifact is verified
    # against the onnxruntime and transformers versions Cloud Run actually runs.
    parity_python = Path(os.environ.get("PARITY_PYTHON", ROOT / ".venv-backend/bin/python"))
    if not parity_python.exists():
        parity_python = onnx_tools_python
    texts_path = args.output / "_parity_texts.json"
    reference_path = args.output / "_parity_reference.npy"
    embeddings_path = args.output / "_parity_onnx.npy"
    texts_path.write_text(json.dumps(texts, ensure_ascii=False), encoding="utf-8")

    reference_run = subprocess.run([
        sys.executable, str(ROOT / "training/torch_reference_embed.py"),
        "--model", str(args.model.resolve()),
        "--texts", str(texts_path),
        "--output", str(reference_path),
    ], check=True, capture_output=True, text=True)
    reference_report = json.loads(reference_run.stdout.strip().splitlines()[-1])
    print("  reference worker:", json.dumps(reference_report))
    max_length = int(reference_report["max_seq_length"])

    subprocess.run([
        str(parity_python), str(ROOT / "training/onnx_parity_embed.py"),
        "--artifact", str(args.output),
        "--texts", str(texts_path),
        "--output", str(embeddings_path),
        "--max-length", str(max_length),
    ], check=True)

    # float64 owned copies. Both sides are near-identical by construction (that
    # is what parity means), and in float32 the elementwise product below was
    # observed writing its result back into `reference_embeddings`: the gate's
    # own forensics dump proved the "corrupted" reference was bit-for-bit
    # `onnx_embeddings ** 2`. The cosine numerator then read good data and the
    # denominator read the squared buffer, giving exactly |onnx|/|onnx^2| =
    # 4.36 — a value a cosine cannot take, which is the only reason this was
    # caught instead of silently shipped. float64 also removes the spurious
    # "overflow encountered in matmul" warnings from the float32 Accelerate
    # path; predict_proba agrees with float32 to 2.3e-06.
    reference_embeddings = np.array(np.load(reference_path), dtype=np.float64)
    onnx_embeddings = np.array(np.load(embeddings_path), dtype=np.float64)
    texts_path.unlink()
    reference_path.unlink()
    embeddings_path.unlink()

    # Norms first, then an einsum with an explicit output signature. Order is
    # deliberate: computing the norms before the dot product means they are
    # already correct even if a ufunc aliases an input buffer, and einsum never
    # writes into its operands.
    reference_norms = np.linalg.norm(reference_embeddings, axis=1)
    onnx_norms = np.linalg.norm(onnx_embeddings, axis=1)
    dot = np.einsum("ij,ij->i", reference_embeddings, onnx_embeddings)
    cosine = dot / np.clip(reference_norms * onnx_norms, 1e-12, None)
    if cosine.max() > 1.0 + 1e-6:
        raise SystemExit(
            f"cosine exceeded 1.0 (max={cosine.max():.5f}); the comparison is unsound, "
            "not the artifact — refusing to judge the export on it"
        )
    reference_probabilities = masked_probabilities(
        np.asarray(head.predict_proba(reference_embeddings)), classes, texts
    )
    onnx_probabilities = masked_probabilities(
        np.asarray(head.predict_proba(onnx_embeddings)), classes, texts
    )
    def describe(name: str, matrix) -> None:
        array = np.asarray(matrix)
        norms = np.linalg.norm(array, axis=1)
        print(
            f"  {name:22s} type={type(matrix).__name__} dtype={array.dtype} shape={array.shape} "
            f"finite={bool(np.isfinite(array).all())} norm[min/mean/max]="
            f"{norms.min():.4f}/{norms.mean():.4f}/{norms.max():.4f}"
        )

    print("parity inputs (torch reference: cpu fp32, subprocess):")
    describe("reference_embeddings", reference_embeddings)
    describe("onnx_embeddings", onnx_embeddings)

    reference_predictions = np.asarray(classes)[np.argmax(reference_probabilities, axis=1)]
    onnx_predictions = np.asarray(classes)[np.argmax(onnx_probabilities, axis=1)]
    disagreement = float(np.mean(reference_predictions != onnx_predictions))
    reference_accuracy = float(accuracy_score(truth, reference_predictions))
    onnx_accuracy = float(accuracy_score(truth, onnx_predictions))
    onnx_macro_f1 = float(f1_score(truth, onnx_predictions, average="macro", zero_division=0))
    weak_codes = {row["code"] for row in labels if row["weak"]}
    reference_accept = model_acceptance(reference_probabilities, classes, weak_codes, thresholds)
    onnx_accept = model_acceptance(onnx_probabilities, classes, weak_codes, thresholds)
    decision_disagreement = float(np.mean(reference_accept != onnx_accept))
    probability_max_abs_delta = float(np.max(np.abs(reference_probabilities - onnx_probabilities)))
    print(
        f"  val accuracy: torch_fp32={reference_accuracy:.4f} onnx={onnx_accuracy:.4f} "
        f"| cosine mean={cosine.mean():.5f} min={cosine.min():.5f}"
    )
    decision_budget = float(args.allow_threshold_decision_disagreement)
    if decision_budget > 0:
        print(
            f"  NOTE: accepting up to {decision_budget:.2%} threshold-decision disagreement "
            f"by explicit request; measured {decision_disagreement:.2%} "
            f"({int(round(decision_disagreement * len(texts)))} of {len(texts)} validation rows "
            "would land on the opposite side of auto-accept vs review)"
        )
    if (
        cosine.mean() < 0.99
        or disagreement > float(args.allow_top1_disagreement)
        or reference_accuracy - onnx_accuracy > 0.02
        or decision_disagreement > decision_budget
    ):
        # Keep the evidence. Deleting the candidate without it makes a gate
        # failure impossible to diagnose without a full re-export.
        forensics = ROOT / "reports/recovery_v1_3_3/parity_gate_failure.npz"
        forensics.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            forensics,
            reference_embeddings=np.asarray(reference_embeddings),
            onnx_embeddings=np.asarray(onnx_embeddings),
            cosine=cosine,
            texts=np.asarray(texts),
        )
        shutil.rmtree(args.output)
        raise SystemExit(
            f"parity gate failed: cosine={cosine.mean():.5f}, disagreement={disagreement:.4%}, "
            f"accuracy_drop={reference_accuracy - onnx_accuracy:+.4f}, "
            f"decision_disagreement={decision_disagreement:.4%}; candidate artifact removed, "
            f"embeddings saved to {forensics.relative_to(ROOT)}"
        )

    gold_rows = read_csv(args.gold)
    card = {
        "model_version": args.version,
        "variant": "base_transaction_aware",
        "base_model": BASE_MODEL,
        "framework": "SetFit full-encoder contrastive fine-tune + sklearn LogisticRegression head",
        "artifact_format": (
            "onnx-int8-dynamic (QInt8 weights; CPU deployment)"
            if args.quantize == "int8"
            else "onnx-fp32 (CPU deployment)"
        ),
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
            "only at top1 >= 0.75 and margin >= 0.50 outside weak classes and ambiguity guards; "
            "DTE-43 Liquidacion rows always require review until a client purchase-side category exists"
        ),
        "metrics": run["metrics"],
        "excluded_untrained": run["excluded_lt2_classes"],
        "weak_classes_lt15_distinct": sorted(row["code"] for row in labels if row["weak"]),
        "parity_gate": {
            "cosine_mean": round(float(cosine.mean()), 5),
            "cosine_min": round(float(cosine.min()), 5),
            "top1_disagreement": round(disagreement, 5),
            "top1_disagreement_allowed": float(args.allow_top1_disagreement),
            "val_accuracy_torch_fp32": round(reference_accuracy, 4),
            "val_accuracy_onnx": round(onnx_accuracy, 4),
            "val_macro_f1_onnx": round(onnx_macro_f1, 4),
            "threshold_decision_disagreement": round(decision_disagreement, 5),
            "threshold_decision_disagreement_allowed": decision_budget,
            "threshold_decisions_flipped": int(round(decision_disagreement * len(texts))),
            "validation_rows": len(texts),
            "probability_max_abs_delta": round(probability_max_abs_delta, 6),
        },
        "familiarity_gate": {
            "index": familiarity_index.name,
            "k": int(np.load(args.output / familiarity_index.name)["k"]),
            "min_agreement": float(np.load(args.output / familiarity_index.name)["min_agreement"]),
            "rows": int(len(np.load(args.output / familiarity_index.name)["labels"])),
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
