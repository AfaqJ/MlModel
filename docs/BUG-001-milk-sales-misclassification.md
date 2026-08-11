# BUG-001 — All 125 sales lines classified as expenses

**Status:** root-caused, fix in progress
**Found:** 2026-08 by the client, in production
**Severity:** critical — client's core revenue lines shown as road-maintenance
expenses; project credibility damaged

---

## Symptom

All 125 `VENTAS` (sales) line items received an `EXP-*` (expense) prediction.
The client — a dairy company — saw milk-sale invoices labeled
`EXP-14.1 Mantencion Caminos` (road maintenance).

```
VENTA DE LECHE     44 → EXP-14.1 Mantencion Caminos      top1 0.12–0.22
VENTA DE LECHE      3 → EXP-15.3 Fletes
VENTA DE VACAS     18 → EXP-14.1 Mantencion Caminos      top1 0.24–0.40
VENTAS TERNEROS    50 → EXP-1.1  Otros Gastos RRHH       top1 0.39–0.57
VENTA DE VAQUILLAS  2 → EXP-14.1 Mantencion Caminos
VENTA DE TERNERAS   1 → EXP-14.1 Mantencion Caminos
```

## What was NOT wrong

- Not ONNX quantization — reproduced with the original PyTorch body and head.
- Not Cloud Run or GCP.
- Not a confidence-threshold failure — every one of the 125 was correctly scored
  low and marked `review_required` with `final_code = null`.
- Not an Ollama failure — all 47 milk rows were audited `Y` with verdict
  `ING-0.1` at 0.98–0.99 confidence.
- Not a database constraint failure.

## Root cause

**`ING-0.1` was not a class in the deployed model.** Verified in
`artifacts/v1.1.0/labels.json`: `classifier_classes` contains 66 entries; the
only income classes present are `ING-0.2` and `ING-0.4`.

The model could not output "milk sale" under any input. Softmax must sum to 1
over the classes that *do* exist, so probability mass went to the nearest wrong
class. The 0.15 top-1 score *was* the model correctly signalling "I have no
class for this."

### The causal chain

1. **Dedup key too narrow.**
   `Data/stale/scripts_labeling_pipeline_2026_07_03/48_promote_starving_audit.py`
   deduped promotions on `(normalized_item_text, category_code)`, ignoring
   `description` and `provider` — both of which are inside the model's input.
   47 milk rows with 47 distinct descriptions collapsed to 1 gold row.
   The same script pre-seeded `seen` with existing gold, so once one milk row
   existed no other could ever enter.

2. **Silent class exclusion.** `training/train_setfit.py:76` drops any class with
   `< 2` examples (SetFit needs a positive pair). Correct in isolation — but it
   logged the exclusion and trained anyway, deleting a revenue class without
   failing.

3. **No validation coverage.** The 340-row validation split contained zero
   income examples, and 5 of 66 trained classes had no validation support.
   Aggregate accuracy of 0.7441 was real and said nothing about revenue.

4. **Unweighted head.** Contrastive pairs used oversampling; the LR head used
   `class_weight=None`. `ING-0.2` (3 examples) and `ING-0.4` (2) were trained but
   hopeless.

5. **Poisoned class.** 2 of `ING-0.2`'s 3 gold rows are `vacas` /
   `vacas preñadas` purchased on COMPRAS invoices — purchases labeled as sales.
   `_master_gold.csv` has no direction column, so the schema could not express
   the constraint it was violating.

6. **Display contract ignored.** The consumer showed `predicted_name` even when
   `decision=review_required` and `final_code=null`, and did not show confidence.
   The client saw a rejected suggestion presented as an answer, with no signal
   that the system was unsure. *(Out of scope this phase; recorded here because
   it is what turned a contained ML gap into a trust incident.)*

## Evidence

```
raw VENTA DE LECHE line items                     47
  in silver audit ledger                          47   (audited=Y, all ING-0.1)
  distinct descriptions among them                47
  reached Data/gold/_master_gold.csv               1
  present in deployed classifier                   no
```

Calves and heifers were never routed into the audit at all —
`TERNERO`: 1 ledger row, blank verdict; `VAQUILLA`: 0 rows. So the dedup fix
alone does not repair `ING-0.3` / `ING-0.4`; they need the raw harvest (D-003).

## Fix

1. Re-promote audited silver with key
   `(item_text, description, provider, category_code)` — D-001, D-002.
2. Harvest sales rows directly from raw VENTAS — D-003.
3. Synthetic floor-clearing where a class still has < 2 real rows — D-005.
4. Add a direction column; quarantine purchase rows sitting in `ING-*` — D-003.
5. Retrain as `v1.2.0` with `class_weight="balanced"` — D-007.
6. Export gate on zero-validation classes — D-008.

## Verification

See TEST_CHECKLIST.md. The specific bar for this bug:

- `ING-0.1` present in `artifacts/v1.2.0/labels.json` `classifier_classes`;
- held-out milk / cow / calf / heifer rows classified correctly, and those rows
  were never in training;
- re-inference over all 12,103 local line items shows the sales rows moving from
  `EXP-*` to `ING-*` with materially higher confidence.
