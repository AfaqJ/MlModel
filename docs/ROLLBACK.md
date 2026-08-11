# ROLLBACK — how to undo each step

Every step in the v1.2.0 recovery, and exactly how to reverse it.

## Ground truth that cannot be lost

These are never modified by any script in this phase. If everything else burns,
the project is recoverable from them:

```
Data/Raw_Data/                     raw XML, read-only
Data/silver/                       audit ledger, read-only in this phase
artifacts/v1.1.0/                  deployed model, never overwritten
Temp_Inference/snapshots/normalized_before_company_item_split/
                                   v1.1.0 predictions for 12,071 items
```

## Step-by-step reversal

### Gold promotion (dedup fix)

Before writing, the script copies the current master to:

```
Data/gold/_master_gold.backup_<timestamp>.csv
```

To undo:

```bash
cp Data/gold/_master_gold.backup_<timestamp>.csv Data/gold/_master_gold.csv
.venv-train/bin/python scripts/50_build_gold_views.py
```

The generated per-category views in `Data/gold/` are rebuilt from the master, so
restoring the master and rebuilding views fully reverses the change.

### Sales harvest / synthetic rows

Both are tagged in the `source` column (`raw_ventas_harvest`, `synthetic_*`).
To remove without touching anything else, filter them out of the master and
rebuild views. They carry no folio or row_id, so they cannot be confused with
real invoice rows.

### Training

New training writes to a **new** directory (`models/setfit_v1_2_0/`) and a new
artifact version (`artifacts/v1.2.0/`). `models/setfit_base/` and
`artifacts/v1.1.0/` are untouched.

To undo: delete the new directories. Nothing else changes.

### Local re-inference

The v1.1.0 baseline is copied to `Data/stale/inference_v1.1.0_<timestamp>/`
before any new inference run. New results are written to a separate path.

To undo: delete the new results directory. The baseline snapshot under
`Temp_Inference/snapshots/` is never written to at all.

## What cannot be rolled back from this repo

Nothing in this phase — no Supabase writes, no deploys, no pushes.
See CONSTRAINTS.md.

If a future phase does write to Supabase: take a fresh export first, and record
the row counts before and after in this file.

## Git

Pre-existing uncommitted work that must not be reset:

```
M .gitignore          protects Temp_Inference/.env.loader and generated reports
M tests/test_api.py   model version read from model card instead of hard-coded
?? Temp_Inference/    migration + loader tooling
?? call_graphs/       tracing tooling
```

Never run `git checkout .`, `git reset --hard`, or `git clean` in this repo
without checking these first.
