# MCT-37 Invoice Classifier — Deployment Package `v1.0.0`

Self-contained inference artifact for the Antillanca invoice line-item classifier.
Runs with **no PyTorch, no SetFit, no sentence-transformers** — production deps only.

## Contents
| File | Purpose |
|---|---|
| `model.onnx` | SetFit-fine-tuned mpnet body, **int8-quantized** (278 MB) |
| `tokenizer/` | XLM-RoBERTa sentencepiece tokenizer files |
| `classifier.joblib` | sklearn LogisticRegression head (66 classes) |
| `labels.json` | `classifier_classes` (predict_proba column order), full 72-cat taxonomy with `trained`/`weak` flags, excluded categories |
| `taxonomy.json` | Full category metadata (code, parent, leaf, description) |
| `provider_giro_map.csv` | provider → business-activity lookup (unused by this variant; shipped for reference) |
| `model_card.json` | Version, metrics, thresholds, decision policy, parity gate, sha256 of every file |
| `inference_example.py` | Reference implementation — **copy this logic into the FastAPI service** |

## Production dependencies
```
onnxruntime  numpy  scikit-learn  joblib  transformers  (tokenizers)
```
No torch. `transformers` is used only for `AutoTokenizer`.

## Model facts (see model_card.json for full detail)
- **Base:** sentence-transformers/paraphrase-multilingual-mpnet-base-v2, SetFit contrastive fine-tune + LR head
- **Input template:** `item_text | description | provider` — description dropped when numeric-only (product codes); fields joined with ` | `; mean-pooled, **no L2 norm**, max_length 128
- **Format:** ONNX int8 dynamic (QInt8 weights) — chosen over fp16 because CPU (Cloud Run, no GPU) has no native fp16 compute; int8 is smaller *and* faster on CPU
- **Trained classes:** 66 (untrained: ADM-1.9, ING-0.1, ING-0.3, ING-0.5, ING-0.6)
- **Validation (313 rows):** top-1 0.728 (int8) / 0.738 (fp32) · **top-3 0.907** · macro-F1 0.632
- **Auto-accept policy:** `top1 ≥ 0.70 AND (top1−top2) ≥ 0.10 AND class not weak` → else review.
  Calibrated on val: **55.6% auto-accepted at 95.4% accuracy**. 30 classes with <15 gold examples are flagged `weak` and always routed to review.

## Quick test
```bash
python inference_example.py "VACUNA CLOSTRIBAC 8 GOLD X 50 DOS." --provider COOPRINSEM
```

## Rebuild
```bash
.venv-train/bin/python training/train_setfit.py --variant base --max-steps 1500
.venv-train/bin/python training/export_onnx.py --variant base --version v1.0.0
```
