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

## Retraining loop
1. Export audited human corrections from Supabase into `Data/gold/_master_gold.csv` per docs/LABELING_RULES.md.
2. `python scripts/50_build_gold_views.py && python scripts/55_contradiction_audit.py`
3. `python training/train_setfit.py --variant base` → check metrics.json (macro-F1, top-3, threshold sweep)
4. `python training/export_onnx.py --variant base --version vX.Y.Z`
5. Ship `artifacts/vX.Y.Z/` (bake into Docker image; image tag == model version).
