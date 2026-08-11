# HANDOVER — where things stand right now

**Living file. Update at the end of every session.**
Deep background lives in `../CONTEXT_HANDOVER.md` (large, written 2026-08-11).
This file is the short answer to "where were we?".

---

## Last updated

2026-08-11 · session: dedup fix + v1.2.0 retrain · model: Claude Opus 5

## What we are doing and why

The client (Antillanca, a dairy company) saw their milk-sale invoices labeled as
road-maintenance expenses. Root cause is fully traced in
`BUG-001-milk-sales-misclassification.md`: the milk category was never a class in
the deployed model, because a dedup bug collapsed 47 training rows to 1 and the
trainer then silently dropped any class with fewer than 2 examples.

Current job: fix the training data, retrain as v1.2.0, and measure the
improvement locally. **Nothing is pushed anywhere this phase** (see CONSTRAINTS.md).

## The numbers that matter

```
raw XML documents                          5,195   (5,166 produced line items)
extracted line items                      12,103   (11,978 purchases + 125 sales)
distinct item names                        5,349   (4,115 appear exactly once)

Ollama-labeled (qwen3:14b)                 4,135
  routed into audit ledger                 1,672
    got a verdict                          1,076   (1,012 accepted, 64 REJECT)
    never verified                           596
never Ollama-labeled                      ~8,000

gold (training source of truth)            1,733
  from the client                            712
  from our own audits                      1,021

deployed v1.1.0: 66 trained classes, ING-0.1 ABSENT
```

## State of the work

**Done**
- Root cause confirmed against the artifacts, not inferred from docs.
- Doc set created (this directory).
- `scripts/56_promote_silver_to_gold.py` — dedup fix. **+519 rows** (not the 680
  I first quoted; that figure predated the decision to skip the 77
  conflicting-verdict names). Gold 1,733 → 2,252. Milk 1 → 48.
- `scripts/57_harvest_sales_gold.py` — harvested 59 sales rows from raw VENTAS,
  quarantined 6 purchase-rows-labeled-as-sales, added 4 synthetic floor rows,
  marked 10 holdout rows. Gold 2,252 → **2,309**.
- `training/train_setfit.py` — holdout/synthetic-aware split, balanced head,
  income slice metrics, loud excluded/unvalidated reporting, refuses to
  overwrite an existing model dir.
- `scripts/58_local_inference_compare.py` — written, not yet run.
- v1.1.0 inference baseline preserved to
  `Data/stale/inference_v1.1.0_baseline_*`.

**Training data state after the fix**

```
gold rows                 1,733 -> 2,309
trainable classes (>=2)      66 -> 69
classes with >=15 gold       43 -> 48
excluded (<2 examples)        5 -> 1   (only ADM-1.9 Asesoria Legal)

ING-0.1 milk      1 -> 48   train 38 / val 10
ING-0.2 cows      3 -> 15   train 13 / val  2
ING-0.3 heifers   1 ->  3   train  3 / val  0   (2 real + 1 synthetic)
ING-0.4 calves    2 -> 46   train 38 / val  8
ING-0.5 other     0 ->  0   NO REAL EXAMPLES — see below
ING-0.6 firewood  1 ->  3   train  3 / val  0   (0 real + 3 synthetic)
```

**Done (cont.)**
- v1.2.0 trained (11.5 min, frozen embeddings per D-011) and re-inferenced over
  all 12,071 baseline rows. **Full results: `RESULTS-v1.2.0.md`.**
  Headline: 120 of 125 sales lines now predicted as income; milk went from
  `EXP-14.1` @ 0.1545 to `ING-0.1` @ 0.9731 with 47/47 auto-accepted; held-out
  income slice 20/20. Two regressions documented there — one wrong auto-accept
  (`VENTA DE ACTIVO FIJO` → `ING-0.1` @ 0.841) and 471 fewer auto-accepts
  overall, 83% of which is confidence flattening rather than label change.

**Next**
- Reboot, then retrain with `--no-freeze-embeddings --batch-size 8` for an
  exactly like-for-like comparison against v1.1.0.
- Run `scripts/58_local_inference_compare.py` over the 12,071 baseline rows.
- Export ONNX as v1.2.0 once a training run is accepted.

**Deliberately not doing** — see CONSTRAINTS.md "Scope discipline".

## Two things needing a decision

1. **`ING-0.5 VENTA DE OTROS ANIMALES` has zero real examples.** The two rows
   the silver promotion added were beef cuts on COMPRAS invoices (purchases) and
   were quarantined. No raw sales line carries this name. Deliberately NOT
   synthesized: it is a catch-all category, and a synthetic class with no real
   signal would compete for probability against the genuine cow/calf/heifer
   classes. Left untrained pending client confirmation that it is unused.

2. **`ADM-1.9 Asesoria Legal` has 1 example** (`Representacion Casub RBM`) and no
   other raw material. Not a name==category case, so no synthetic rows. It stays
   excluded from the model.

## Traps a new session will fall into

1. **`ING-0.1` was never trained.** Not undertrained — absent from
   `classifier_classes`. Do not go looking for a threshold or embedding problem.
2. **The head never sees category names.** Labels are codes; `coef_` is learned
   from examples. A zero-example class cannot be rescued by naming it well.
3. **There are two confidence thresholds** (backend 0.70, loader 0.80). Always
   say which one.
4. **`Data/silver/` holds three different file schemas.** The audit ledger is the
   1,672-row one with a `verdict` column. Summing all files gives a meaningless
   number — this has already caused one wrong figure in this project.
5. **Folio is not unique.** A folio is the seller's own invoice number; 132 folio
   numbers are reused across different sellers. Identity is (seller, folio).
6. **`Data/` and `Temp_Inference/` are capitalized.** Some scripts use lowercase
   `data/`, which works on macOS and breaks on Linux.
7. **Uncommitted work exists that must not be reset** — see ROLLBACK.md.

## Open questions for the client

1. How should sales of fixed assets / vehicles / machinery be categorized?
   (7 rows: 3 `VENTA CAMIONETA`, 2 `VENTA DE ACTIVO FIJO`, 1 `maquinaria`,
   1 `OTROS INGRESOS`.) Selling a truck is not dairy revenue.
2. What is the correct category for *purchases* of cows and pregnant heifers?
   The `ING-*` categories are sales-oriented, and old gold contains purchase rows
   mislabeled as sales.
3. Which taxonomy categories does the client accept as genuinely having no
   examples in this dataset?
