# TEST CHECKLIST — proof, not claims

Nothing counts as done until the relevant block below has been run and the actual
output recorded. "The script ran without error" is not evidence.

## After the gold promotion

```bash
.venv-train/bin/python scripts/56_promote_silver_to_gold.py          # dry run
```

Check, before committing:

- [ ] total gold rows before → after matches the dry-run projection
- [ ] no row was added whose `category_code` is absent from the taxonomy
- [ ] no row was added with an empty `item_text`
- [ ] the 77 conflicting-verdict names contributed **zero** rows
- [ ] `ING-0.1` count goes 1 → ~51
- [ ] per-category counts printed and eyeballed for anything absurd
      (a class jumping from 3 to 400 is a bug, not a win)

```bash
.venv-train/bin/python scripts/55_contradiction_audit.py
.venv-train/bin/python scripts/50_build_gold_views.py
```

- [ ] contradiction audit reports no new contradictions introduced
- [ ] view files regenerate without error

## After the sales harvest

- [ ] every harvested row came from a `VENTAS` document
- [ ] no harvested row carries a folio / row_id / source_file
      (harvest rows are training data, not invoices)
- [ ] the held-out ~20% per class is recorded and is **excluded** from training
- [ ] no synthetic row appears in any validation split

## Before export — the release gates

These are the gates that would have caught BUG-001.

- [ ] **every trained class has ≥ 1 validation row** — export fails otherwise
- [ ] `ING-0.1` appears in `artifacts/v1.2.0/labels.json` `classifier_classes`
- [ ] income slice accuracy reported separately from aggregate accuracy
- [ ] the count of classes with < 2 examples is printed, named, and explained —
      not silently skipped
- [ ] PyTorch ↔ ONNX parity gate passes
- [ ] `artifacts/v1.1.0/` unmodified (`git status`, file mtimes)

## Behavioral checks on the new model

Run against held-out rows the model never trained on:

- [ ] `VENTA DE LECHE` → `ING-0.1`
- [ ] `VENTA DE VACAS` → `ING-0.2`
- [ ] `VENTA DE VAQUILLAS` → `ING-0.3`
- [ ] `VENTAS TERNEROS` → `ING-0.4`
- [ ] `VENTA DE TERNERAS` → `ING-0.4`
- [ ] a COMPRAS row (e.g. `vacas preñadas` purchased) does **not** land in `ING-*`

## After local re-inference

- [ ] baseline v1.1.0 predictions copied to `Data/stale/` before the run
- [ ] new run covers the same row count as the baseline (12,071 comparable)
- [ ] all 125 sales rows compared before → after, individually listed
- [ ] count of rows that changed category reported
- [ ] count of rows that moved from `review_required` to `auto_accept` reported
- [ ] **rows that got worse** reported too — a change that only lists wins is
      not a comparison

## Backend smoke tests

```bash
.venv-backend/bin/python -m pytest tests -q
```

- [ ] passes (was 6 passed before this work started)
