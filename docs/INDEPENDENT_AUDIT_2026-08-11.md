# Independent audit — 2026-08-11

## Verdict

Do not deploy, export, push, or write the current candidate results to Supabase.

The original production incident is correctly root-caused: the historical
silver-to-gold promotion collapsed 47 Milk Sales rows to one, the trainer then
excluded the one-example class, and the UI displayed a low-confidence,
`review_required` suggestion as a final classification.

The proposed architectural direction is also correct: deterministic rules for
canonical sales phrases, explicit handling for taxonomy gaps, transaction-aware
safety constraints, and SetFit only for the long tail.

The current implementation is not integrated end to end and is not release
safe. A canonical Milk Sales API request currently returns HTTP 500, the
production loader never sends transaction direction, the database schema cannot
store the new response type, and the 12,071-row comparison does not execute the
new rules or direction mask.

## Rollback state established before this audit

No remote operation was performed.

- `main` remains at `a60e43f` (`Package v1.1.0 backend and model`).
- Safety branch: `codex/pre-fix-audit-20260811`.
- Commit `76a3f76` snapshots the visible Claude code/docs state.
- Commit `78d44f2` snapshots the previously ignored training code, labeling
  rules, current gold/silver/processed data, and local database recovery
  snapshot.
- The original pre-session gold is still available at
  `Data/gold/_master_gold.backup_20260811_104643.csv` (1,733 rows).
- The deployed baseline `artifacts/v1.1.0/` and local reference
  `models/setfit_base/` were not modified.

Generated candidate model directories remain ignored by Git because each is
about 1.1 GB. They are additive and have not overwritten the reference model.

## What the previous agent got right

1. It identified the real Milk Sales causal chain rather than blaming ONNX,
   Cloud Run, or the confidence threshold.
2. It discovered that the first re-promotion introduced identical inputs with
   different labels. Rebuilding from the pre-session backup and rejecting
   conflicting promotions restored zero exact cross-label model-input groups in
   the current master.
3. It discovered exact-input train/validation leakage. The deployed v1.1.0
   split has 57 of 340 validation rows whose exact built text appears in its
   training rows (30 distinct leaked texts). The current deduplicated split has
   zero exact or normalized input overlap.
4. It preserved backups before rewriting gold and wrote new model candidates to
   separate directories.
5. It corrected the claim that 20/20 sales validation rows prove unseen-wording
   generalization. All 20 reuse an item phrase and label present in training.

## Critical failures in the current “better fix”

### 1. The new API route fails on the exact incident case

`Predictor` returns `source="business_rule"`, but the response schema only
allows `model`, `product_lookup`, and `meter_lookup`.

Reproduced locally:

```text
POST /predict
{"item_text":"VENTA DE LECHE","transaction_type":"VENTAS"}

HTTP 500 Internal Server Error
```

The ordinary test suite still reports `6 passed` because it contains no
business-rule, asset-sale, direction-mask, or response-contract test.

### 2. The production caller never activates the fix

`Temp_Inference/classify_raw_invoices_to_supabase.py::to_predict_request()`
does not put `row.transaction_type` in the API payload. The field exists on the
parsed row but is dropped before inference. The old broken behavior therefore
remains active for the real loader.

The API also accepts any short string for transaction type. Misspellings such
as `VENTA` silently disable all protection. The contract should validate the
allowed values, and production classification should not silently continue
without direction.

### 3. The persistence contract cannot represent the new result

The new `review` action intentionally returns no predictions for an asset sale.
The loader rejects empty predictions, while the current SQL schema requires
non-null predicted category/code and restricts `prediction_source` to the three
old values. A `business_rule` response cannot currently pass from API to
storage.

### 4. The reported full-data replay did not test the new fix

`scripts/58_local_inference_compare.py` implements only:

```text
meter lookup -> product lookup -> model
```

It reads transaction direction but never applies `BusinessRules` or
`direction_mask`. Its latest output therefore cannot substantiate claims about
the new architecture.

Latest completed replay (`models/setfit_base_v120`):

```text
rows                         12,071
changed predictions           3,928
auto-accept old -> new     6,356 -> 5,813
sales predicted income        0 -> 120 of 125
purchases predicted income    9 -> 5
```

These are behavior counts, not accuracy: the 12,071 rows do not have a trusted
gold label for every row.

### 5. The clean candidate is materially weaker than the handover said

The run left in flight did finish at `models/setfit_base_v120`:

```text
master gold rows                         2,262
distinct normalized model inputs         2,009
train / validation                   1,613 / 395
accuracy                                 0.6329
macro-F1                                 0.5940
top-3 accuracy                           0.8025
income phrase slice                      20/20
```

Eight trained classes have no validation row:

```text
ADM-1.3, EXP-10.2, EXP-15.1, EXP-6.3,
EXP-6.4, EXP-8.3, ING-0.3, ING-0.6
```

This contradicts the documented claim that export refuses every trained class
without validation. The export code contains no such gate.

The new metrics cannot be directly compared with v1.1.0's `0.7441`: the splits
and data differ, and 57/340 v1.1.0 validation rows leaked from its training
data. There is no locked, independent test set shared by both models.

### 6. The “exact model input” dedup is not exact

Training builds raw text, then deduplicates a lowercased, accent-stripped,
punctuation-collapsed version. This is a defensible grouping policy, but it is
not the exact string the model consumes as the comments claim. The policy must
be named and tested explicitly so meaningful distinctions are not silently
discarded.

The current split has zero overlap under both raw and normalized text, which is
an improvement. It still measures variation in description/provider for sales
phrases already present in training, not generalization to unseen item wording.

### 7. Synthetic data creates a class with no real evidence

All three current `ING-0.6` training rows are synthetic. There is no Firewood
Sale row in the 125 raw sales lines; the one old real-looking gold row was a
purchase and was quarantined. This conflicts with the standing labeling rule
to wait for client data rather than fabricate income coverage.

A literal, client-approved phrase can be a deterministic rule without pretending
the ML class has learned a distribution. `ING-0.6` should not be described as a
validated trained class on this evidence.

### 8. Gold views and reports are stale

The source-of-truth master was written at 12:37 and contains 2,262 rows, but the
generated coverage and per-category views are still from July 14. For example,
the master has 48 Milk Sales rows while the generated file remains
`ING-0.1 VENTA DE LECHE (1).csv` with one row. The saved contradiction report
also predates the latest master.

No data consumer should read the per-category views until they are regenerated
from the accepted master and checked.

### 9. The export command can package the wrong model and delete artifacts

`training/export_onnx.py` derives its input only as
`models/setfit_<variant>`. It cannot select tagged candidates such as
`models/setfit_base_v120`. Running the documented command with
`--variant base --version v1.2.0` would load the old `models/setfit_base` model
and label that package v1.2.0.

It also recursively deletes an existing artifact directory before validation.
Passing `--version v1.1.0` would delete the deployed local baseline. This
violates the project's rollback constraints.

### 10. Direction safety is applied too narrowly

The mask only changes model probabilities. A lookup can still return an
impossible direction/category combination. For unknown `VENTAS` phrases, the
safer invariant is not “force an income answer”; it is “an expense suggestion
can be shown only as review-required.” Direction constraints should be applied
to the final routed result, across every source.

## Recommended repair order

### Phase A — make the deterministic safety layer real

1. Add `business_rule` to the API and persistence enums.
2. Make transaction direction a validated contract and include it in every
   loader/batch payload. In the production path, missing direction must force
   review or fail validation rather than silently disabling safety.
3. Define a storable abstention response for `no_category_in_taxonomy`:
   nullable predicted category/code, empty suggestions allowed, explicit reason
   and rule version.
4. Make authoritative `assign` rules short-circuit the model. If model
   disagreement is wanted for monitoring, record it separately; do not let an
   older model veto a deterministic client rule.
5. Apply direction invariants after all routing sources:
   - COMPRAS + income result -> review/error;
   - VENTAS + expense result -> review, never auto-accept;
   - known asset/other-income phrases -> abstain and review.
6. Add end-to-end tests through FastAPI, batch payload construction, loader
   conversion, and schema-compatible persistence.

### Phase B — stabilize and adjudicate the data

1. Freeze the current 2,262-row master while the 53 skipped label conflicts are
   manually adjudicated using the documented trust hierarchy. “First existing
   row wins” is not enough.
2. Remove synthetic-only `ING-0.6` from model training. Keep any approved exact
   phrase in the deterministic rule table.
3. Review the six quarantined purchase-as-sale rows and record explicit human
   decisions rather than relying permanently on absence/presence of a name in
   today's raw folders.
4. Regenerate coverage/category views and the contradiction report only after
   the master is accepted; verify generated counts against the master.
5. Version the accepted training manifest with row count, source counts, hash,
   transformation version, and split hash.

### Phase C — build an evaluation that can answer the actual question

Use two separate suites:

1. **Deterministic business regression suite:** canonical sales phrases,
   direction violations, asset sales, missing/invalid direction, final-code
   behavior, and all database serialization paths.
2. **Locked ML test set:** human-labeled examples not used in promotion,
   training, threshold selection, or rule authoring. Group related item phrases
   so near-duplicates cannot cross train/test. Report per-class support,
   macro-F1, top-3, calibrated accepted accuracy, and business-critical slices.

On one frozen data/split manifest, compare:

- current v1.1.0 baseline;
- full SetFit vs frozen token embeddings;
- LogisticRegression `class_weight=None` vs `balanced` using the same
  embeddings;
- confidence calibration and accepted-accuracy curves.

Do not choose a model based on the number of auto-accepts alone.

### Phase D — make export non-destructive and unambiguous

1. Require an explicit `--model-dir` and explicit new output directory/version.
2. Refuse to overwrite any existing model/artifact directory by default.
3. Verify the selected model's manifest, version, split hash, class list, and
   input length before export.
4. Enforce gates before writing the final package: no unexplained unvalidated
   production class, locked-test results present, deterministic regression
   suite green, PyTorch/ONNX parity green, and v1.1.0 hashes unchanged.
5. Write to a temporary candidate directory and atomically rename only after
   every gate succeeds.

## Release decision

The current branch is an investigation snapshot, not a release candidate. Keep
v1.1.0 as the untouched rollback baseline, fix the customer-facing review/final
contract first, then implement and test the deterministic safety layer before
spending more time retraining SetFit.
