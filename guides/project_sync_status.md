# Project Sync Status

Last synced: July 5, 2026.

## Current Truth

- The model is trained.
- The shipped model package is `artifacts/v1.0.0`.
- The production artifact uses ONNX int8 dynamic quantization, not fp16.
- The backend skeleton now exists in `app/`.
- Product lookup rules are generated into `app/data/product_lookup.csv`.
- The project is still not deployed.

## Fresh / Active

- `Data/gold/_master_gold.csv`: audited gold source.
- `training/train_setfit.py`: trains SetFit.
- `training/export_onnx.py`: exports int8 ONNX package.
- `artifacts/v1.0.0/`: current model package.
- `app/`: new FastAPI backend.
- `guides/`: beginner learning docs and notebooks.

## Stale Or Historical

- `Data/stale/`: old recovery and labeling work. Keep it, but do not use it as active truth.
- Older fp16 wording in old notes should be ignored if it appears outside the synced docs.
- Raw data should not be promoted into gold directly.

## Still To Do

- Install backend runtime dependencies.
- Run full FastAPI tests.
- Build Docker image.
- Benchmark 1 vCPU / 2GB behavior.
- Deploy to Cloud Run staging.
- Run shadow mode before enabling auto-accept.
- Build the frontend/Supabase workflow.
