# TEST CHECKLIST — proof, not claims

Nothing counts as done until the relevant block has been run and the actual
output recorded. "The script ran without error" is not evidence.

## Always

```bash
.venv-backend/bin/python -m pytest tests/ -q
```

98 tests. All must pass. Anything less is a regression — the suite went from
57 passed / 11 failed to 98 passed on 2026-08-12 and must not go backwards.
It briefly read 108 while the catalog prototype existed; those 10 tests were
deleted with it on 2026-08-18, so 98 is the floor again.

## Before a full Supabase re-load

1. Dry-run the write; its target count, amount, and “no final label on review”
   invariant must all pass before anything executes.
2. Run `scripts/81_backup_supabase.py`; every one of the five table row counts
   must match Supabase before continuing.
3. Execute the write over PostgREST, scoped to the rows it names — never a
   whole-database re-load. Writing must require an explicit flag.
4. Verify against live afterwards: row counts, category IDs, item names,
   decisions and final labels. The Supabase schema is deliberately not
   recreated or modified.

## Before accepting a retrain

Read the generated `model_card.json` and check, in this order:

1. **Income slice accuracy.** Currently 21 rows at 1.00. This is a **mandatory
   gate** — aggregate accuracy alone has already shipped one incident. v1.1.0
   reported 0.7441 over 340 validation rows containing **zero** income examples.
   The number was real and meaningless.
2. **Every trained class has validation support.** See D-008. Five of 66 classes
   had none in v1.1.0.
3. **No class with fewer than 2 examples was silently dropped.** It must fail
   loudly. `excluded_untrained` currently lists `ADM-1.9` and `ADM-2.3`.
4. **Weak-class list recomputed from the split.** Currently 26 classes under 15
   distinct examples.

## Calibration — the baseline to beat

Measured on the locked 312-row validation split for the v1.3.2 weights that
became v1.3.3. Re-run `scripts/77_model_trust_report.py` after any retrain and
compare against these.

**ECE 0.0517, MCE 0.202.** Every confidence band is *under*-confident — observed
accuracy exceeds the score in all seven bands. The score is a **floor** on
accuracy, not an overstatement:

| band | n | mean confidence | observed accuracy |
|---|---:|---:|---:|
| [0.00, 0.50) | 84 | 0.330 | 0.333 |
| [0.50, 0.60) | 23 | 0.547 | 0.652 |
| [0.60, 0.70) | 21 | 0.655 | **0.857** |
| [0.70, 0.75) | 22 | 0.723 | 0.727 |
| [0.75, 0.80) | 17 | 0.769 | **0.882** |
| [0.80, 0.90) | 32 | 0.851 | 0.938 |
| [0.90, 1.01) | 113 | 0.961 | **1.000** |

**The failure mode has inverted.** The model that started this recovery was
confidently wrong. This one is systematically under-confident. So the remaining
problem is no longer false positives — it is that a conservative threshold
rejects rows the model got right. The `[0.60, 0.70)` band is the striking case:
85.7% accurate while scoring 0.655, and currently all rejected.

**If a retrain pushes any gap positive, stop.** A positive gap means the score
has started overstating accuracy again — that is the incident's failure mode
returning, and no aggregate number will show it.

## Before accepting an INT8 export

The exporter enforces these and refuses by default. If you had to raise a
ceiling to ship, record the actual and allowed values in `DECISIONS.md` — see
D-017, where exactly that happened.

| Check | v1.3.3-int8 | Default ceiling |
|---|---|---|
| cosine mean vs FP32 | 0.99005 | — |
| top-1 disagreement | 0.0641 | 0.03 |
| threshold-decision disagreement | 0.04808 (15/312) | 0.0 |

**Read the direction of the flips, not just the count.** In v1.3.3, 13 of 15
were auto-accept → review (safe) and 2 were review → auto-accept and both
correct. Zero new false positives. A flip count that is flat but drifting toward
new false positives is worse than a higher count of safe downgrades.

**A cosine above 1.0 is impossible.** If you see one, the bug is in the parity
harness, not the model. See the 2026-08-12 gotcha in `STATE.md`.

## Before deploying

```bash
gcloud builds submit --config <...>     # must include .gcloudignore
```

Then against the live revision:

- `/artifact-check` → `model.onnx` byte count matches the local artifact and
  `looks_like_lfs_pointer: false`.
- `business_rule` path → `VENTA DE LECHE` under VENTAS returns `ING-0.1`,
  auto-accept. **This is the incident path.** It must be exact and it must be 0 ms.
- Direction guard → `VENTA DE LECHE` under COMPRAS returns **no** `ING-` code.
- `product_lookup` → returns `EXP-2.3`; `meter_lookup` → returns `EXP-9.1`.
- `/predict-batch` with 250 rows → 0 errors.

## Never

- Never release on aggregate accuracy alone.
- Never size Cloud Run from local Docker timings. Local measured 342 ms/row;
  the real vCPU does 103 ms/row — 3.3× pessimistic from macOS VM overhead.
- Never trust a green suite as evidence that a *display* is correct. The
  original incident was a correct `review_required` prediction rendered as a
  final answer by the frontend. No backend test could have caught it.
