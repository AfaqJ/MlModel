# training/ — MCT-37 model training & export

Offline pipeline that produces the deployment package in `../artifacts/<version>/`.
PyTorch lives here only; it never ships to production.

## Setup
```bash
/opt/homebrew/bin/python3.11 -m venv ../.venv-train
../.venv-train/bin/pip install -r requirements-train.txt
```
Python 3.11 required (setfit 1.1.1 breaks on 3.14; datasets pinned <4 for a setfit
model-card bug). On Apple Silicon export/train with `PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0`.

## Files
| File | Purpose |
|---|---|
| `train_setfit.py` | SetFit fine-tune + LR head. `--variant base\|giro\|both`. Stratified split, oversampling, excludes <2-example classes, writes metrics.json + val_split.csv per variant to `../models/setfit_<variant>/` |
| `export_onnx.py` | fp32 ONNX export → int8 dynamic quant → parity gate → assembles `../artifacts/<version>/` with model card |
| `inference_example.py` | Reference inference (also copied into each package) |
| `provider_giro_map.csv` | provider → giro (business activity) from raw DTE XML, for the `giro` variant |
| `requirements-train.txt` | Pinned training environment |

## Input decision (2026-07-03 raw-data audit)
Semantic fields: `item_text`, `description` (blanked when numeric-only — product codes),
`provider`, and optionally `giro`. All other DTE XML fields (RUTs, Acteco codes, quantities,
prices, units, amounts, addresses, folio/dates) rejected — no classification signal.
The **base** variant (no giro) won: top-3 0.907 vs 0.869 and macro-F1 0.631 vs 0.618. giro
raised top-1 marginally but collapsed top-3 diversity and hurt rare classes. See
`../models/_comparison_archive/`.

## Retraining loop (as run for v1.4.0, 2026-09-16)

`train_setfit.py` / `export_onnx.py` belong to the v1.1 experiments. The live
path is the recovery pair below.

```bash
# 1. build the candidate + locked split from gold (D-098)
.venv-backend/bin/python scripts/100_build_retrain_candidate.py

# 2. train (CPU, ~1.5 h for 1,500 steps; run one at a time — two runs swap and
#    take 6x longer). --body-cap-per-class caps the contrastive stage only.
D=Data/candidates/retrain_2026_09_15
.venv-train/bin/python training/train_recovery_setfit.py \
  --gold $D/master_gold.csv --split-from $D/split.csv \
  --output models/setfit_retrain_<stamp> --device cpu --batch-size 8 --max-steps 1500

# 3. recalibrate + write the familiarity index (D-096); needs an absolute --model
.venv-train/bin/python scripts/75_calibrate_familiarity_gate.py \
  --model $PWD/models/setfit_retrain_<stamp> --gold $D/master_gold.csv \
  --split $D/split_compat.csv --report reports/<run>/familiarity_calibration.json --write-index

# 4. export INT8 (2 GiB Cloud Run; FP32 does not fit). Ceilings are deliberate: D-097
.venv-train/bin/python training/export_recovery_onnx.py \
  --model $PWD/models/setfit_retrain_<stamp> --gold $D/master_gold.csv \
  --split $D/split_compat.csv --thresholds reports/recovery_v1_3_2/selected_thresholds.json \
  --output artifacts/vX.Y.Z-int8 --version vX.Y.Z --quantize int8 \
  --allow-top1-disagreement 0.09 --allow-threshold-decision-disagreement 0.05

# 5. compare every build on the same locked test rows
.venv-train/bin/python scripts/101_evaluate_retrain.py \
  --model live=artifacts/v1.3.3-int8 --model new=artifacts/vX.Y.Z-int8

# 6. point Dockerfile, .dockerignore, .gcloudignore and app/core/config.py at the
#    new artifact, run pytest, then build the image and deploy (docs/ROLLBACK.md).
```

`scripts/75` and `training/export_recovery_onnx.py` read a split whose held-out
rows are labelled `validation`; `split_compat.csv` is that view of `split.csv`.

**Gotchas.** A freshly trained directory needs `_name_or_path` in `config.json`
before SetFit's model-card helper will load it. Weights saved by
sentence-transformers 5.x will not load under the 3.4.1 in `.venv-train` —
`scripts/101` sidesteps this by loading transformers + mean pooling + the joblib
head directly.
