"""MCT-37 — Export the trained SetFit model to the ONNX int8 deployment package.

Pipeline (per docs/archive/blueprint.md §2.4 — archived; superseded by export_recovery_onnx.py):
  1. Load trained SetFit model (models/setfit_<variant>).
  2. Export the sentence-transformer body to ONNX via optimum, then dynamic-quantize to int8.
  3. Dump the sklearn LogisticRegression head to classifier.joblib.
  4. Build labels.json (full taxonomy with trained/weak flags), taxonomy.json, model_card.json.
  5. PARITY GATE: embeddings cosine(torch, onnx-int8) — mean must be > 0.99 —
     and end-to-end top-1 prediction disagreement on the val split must be < 3%.
     The package is deleted if the gate fails.

Usage:
  .venv-train/bin/python training/export_onnx.py --variant giro --version v1.0.0
Output: artifacts/<version>/
"""
from __future__ import annotations
import argparse, csv, hashlib, json, shutil, subprocess, sys
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
TAXONOMY = ROOT / "Data/current_context_2026_06_30/taxonomy_from_plan.csv"
EXCLUDED = ROOT / "Data/current_context_2026_06_30/excluded_categories.csv"
GOLD = ROOT / "Data/gold/_master_gold.csv"
BASE_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
THRESHOLDS = {"accept_top1": 0.70, "accept_margin": 0.10}  # overridden by calibration below if sweep exists


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def mean_pool(last_hidden: np.ndarray, mask: np.ndarray) -> np.ndarray:
    m = mask[..., None].astype(np.float32)
    return (last_hidden * m).sum(1) / np.clip(m.sum(1), 1e-9, None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", required=True)
    ap.add_argument("--version", default="v1.0.0")
    a = ap.parse_args()

    model_dir = ROOT / f"models/setfit_{a.variant}"
    out = ROOT / "artifacts" / a.version
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    import joblib
    from sentence_transformers import SentenceTransformer
    print("loading SetFit model…")
    # Load body/head directly — SetFitModel.from_pretrained's model-card inference
    # crashes on locally-saved models (no HF repo id). We only need body + head.
    body = SentenceTransformer(str(model_dir))  # SentenceTransformer
    head = joblib.load(model_dir / "model_head.pkl")  # sklearn LogisticRegression trained by SetFit
    classes = list(head.classes_)
    metrics = json.loads((model_dir / "metrics.json").read_text())

    # --- 1. ONNX export (fp32) → int8 dynamic quantization ----------------
    # int8 dynamic quant is the CPU-optimal choice for Cloud Run (1 vCPU, no GPU):
    # ~280MB RAM AND faster than fp32 via VNNI/AVX2 int8 GEMM. fp16 was rejected
    # because ONNX Runtime has no native fp16 CPU compute (cast-emulated → no speedup).
    print("exporting ONNX (fp32)…")
    tmp = ROOT / "models/_onnx_tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    subprocess.run([sys.executable, "-m", "optimum.exporters.onnx",
                    "--model", str(model_dir), "--task", "feature-extraction",
                    str(tmp)], check=True)
    print("quantizing to int8 (dynamic)…")
    from onnxruntime.quantization import quantize_dynamic, QuantType
    quantize_dynamic(model_input=str(tmp / "model.onnx"),
                     model_output=str(out / "model.onnx"),
                     weight_type=QuantType.QInt8)

    # tokenizer files
    tok_dir = out / "tokenizer"
    tok_dir.mkdir()
    for f in tmp.iterdir():
        if f.name != "model.onnx" and f.is_file():
            shutil.copy(f, tok_dir / f.name)
    shutil.rmtree(tmp)

    # --- 2. classifier head ------------------------------------------------
    joblib.dump(head, out / "classifier.joblib")

    # --- 3. labels.json / taxonomy.json ------------------------------------
    gold_counts = Counter(r["category_code"].strip() for r in csv.DictReader(open(GOLD)))
    taxonomy = list(csv.DictReader(open(TAXONOMY)))
    excluded = list(csv.DictReader(open(EXCLUDED)))
    labels = []
    for t in taxonomy:
        code = t["new_code"].strip()
        n = gold_counts.get(code, 0)
        labels.append({"code": code, "parent": t["parent"], "name": t["leaf"],
                       "trained": code in classes, "weak": 0 < n < 15 or code not in classes,
                       "gold_examples": n})
    (out / "labels.json").write_text(json.dumps({
        "classifier_classes": classes,  # exact order of predict_proba columns
        "labels": labels,
        "excluded_categories": [e["leaf"] for e in excluded],
    }, indent=2, ensure_ascii=False))
    (out / "taxonomy.json").write_text(json.dumps(taxonomy, indent=2, ensure_ascii=False))
    shutil.copy(ROOT / "training/provider_giro_map.csv", out / "provider_giro_map.csv")

    # --- 4. parity gate -----------------------------------------------------
    print("parity gate…")
    import onnxruntime as ort
    from transformers import AutoTokenizer
    val = list(csv.DictReader(open(model_dir / "val_split.csv")))
    texts = [r["text"] for r in val]
    ref = body.encode(texts, batch_size=32, convert_to_numpy=True, show_progress_bar=False)
    tok = AutoTokenizer.from_pretrained(str(tok_dir))
    sess = ort.InferenceSession(str(out / "model.onnx"), providers=["CPUExecutionProvider"])
    onnx_emb = []
    for i in range(0, len(texts), 32):
        enc = tok(texts[i:i + 32], padding=True, truncation=True, max_length=128, return_tensors="np")
        feed = {k: v for k, v in enc.items() if k in {i.name for i in sess.get_inputs()}}
        hidden = sess.run(None, feed)[0]
        onnx_emb.append(mean_pool(hidden, enc["attention_mask"]))
    onnx_emb = np.vstack(onnx_emb)
    cos = np.sum(ref * onnx_emb, 1) / (np.linalg.norm(ref, axis=1) * np.linalg.norm(onnx_emb, axis=1))
    pred_ref = head.predict(ref)
    pred_onnx = head.predict(onnx_emb)
    disagree = float(np.mean(pred_ref != pred_onnx))
    # accuracy of the quantized pipeline vs ground-truth labels (the number that matters)
    y_true = [r["label"] for r in val]
    from sklearn.metrics import accuracy_score, f1_score
    acc_onnx = accuracy_score(y_true, pred_onnx)
    acc_ref = accuracy_score(y_true, pred_ref)
    f1_onnx = f1_score(y_true, pred_onnx, average="macro", zero_division=0)
    print(f"cosine mean={cos.mean():.5f} min={cos.min():.5f} | top1 disagreement={disagree:.4%}")
    print(f"val accuracy  torch={acc_ref:.4f}  int8-onnx={acc_onnx:.4f}  (Δ={acc_ref-acc_onnx:+.4f}) | int8 macroF1={f1_onnx:.4f}")
    # int8 gate: quantization introduces expected drift; require cosine>0.99, disagreement<3%,
    # and accuracy drop <2 points. Package is deleted if the gate fails.
    if cos.mean() < 0.99 or disagree >= 0.03 or (acc_ref - acc_onnx) > 0.02:
        shutil.rmtree(out)
        sys.exit(f"PARITY GATE FAILED (cos={cos.mean():.5f}, disagree={disagree:.4%}, "
                 f"acc_drop={acc_ref-acc_onnx:+.4f}) — package deleted")

    # --- 5. calibrated thresholds + model card ------------------------------
    thresholds = dict(THRESHOLDS)
    best = None
    for s in metrics.get("threshold_sweep", []):
        if s["accepted_acc"] >= 0.95 and (best is None or s["accept_rate"] > best["accept_rate"]):
            best = s
    if best:
        thresholds = {"accept_top1": best["top1"], "accept_margin": best["margin"],
                      "calibration": {"val_accept_rate": best["accept_rate"],
                                      "val_accepted_accuracy": best["accepted_acc"]}}
    card = {
        "model_version": a.version,
        "variant": a.variant,
        "base_model": BASE_MODEL,
        "framework": "SetFit (contrastive fine-tune) + sklearn LogisticRegression head",
        "artifact_format": "onnx-int8-dynamic (QInt8 weights; CPU-optimal for Cloud Run)",
        "trained_date": str(date.today()),
        "trained_classes": len(classes),
        "input_construction": {
            "template": "item_text | description | provider" + (" | giro" if a.variant == "giro" else ""),
            "rules": [
                "join non-empty fields with ' | '",
                "description dropped when numeric-only (product codes carry no semantics)",
                "giro = provider business activity (GiroEmis in DTE XML); at inference pass it "
                "from the invoice XML, or fall back to provider_giro_map.csv" if a.variant == "giro" else
                "giro not used by this variant",
            ],
            "pooling": "mean pooling over last_hidden_state with attention mask, NO L2 normalization",
            "max_length": 128,
        },
        "thresholds": thresholds,
        "decision_policy": "auto_accept iff top1>=accept_top1 AND (top1-top2)>=accept_margin AND class not weak",
        "metrics": {k: metrics[k] for k in ("val_n", "accuracy", "macro_f1", "top3_accuracy",
                                            "confidence_buckets", "threshold_sweep")},
        "per_class_f1": metrics["per_class"],
        "excluded_untrained": metrics["excluded_classes"],
        "weak_classes_lt15_gold": metrics["weak_classes_lt15"],
        "parity_gate": {"cosine_mean": round(float(cos.mean()), 5),
                        "cosine_min": round(float(cos.min()), 5),
                        "top1_disagreement": round(disagree, 5),
                        "val_accuracy_torch_fp32": round(float(acc_ref), 4),
                        "val_accuracy_int8_onnx": round(float(acc_onnx), 4),
                        "val_macro_f1_int8_onnx": round(float(f1_onnx), 4)},
        "gold_rows": sum(gold_counts.values()),
        "seed": metrics["seed"],
    }
    (out / "model_card.json").write_text(json.dumps(card, indent=2, ensure_ascii=False))
    card["artifacts_sha256"] = {str(p.relative_to(out)): sha256(p)
                                for p in sorted(out.rglob("*"))
                                if p.is_file() and p.name != "model_card.json"}
    (out / "model_card.json").write_text(json.dumps(card, indent=2, ensure_ascii=False))
    shutil.copy(ROOT / "training/inference_example.py", out / "inference_example.py")
    print(f"package ready: {out}")
    for p in sorted(out.rglob("*")):
        if p.is_file():
            print(f"  {p.relative_to(out)}  {p.stat().st_size/1e6:.1f} MB")


if __name__ == "__main__":
    main()
