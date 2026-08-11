# ML recovery v1.3.1 — handoff and current truth

Date: 2026-08-11

Branch: `codex/transaction-aware-retrain-v2`
Scope: local only. Nothing was pushed, deployed, uploaded to Supabase, or tested through a live API.

## Executive status

The original milk/calf-sales incident is fixed in the clean data and in the backend routing. The newly retrained SetFit model also learned the sales direction and labels. It is a real full-encoder retrain, not frozen embeddings.

The FP32 model and production decision cascade passed their locked validation audit, and all 11,766 retained real XML lines were replayed afterward. That raw replay exposed provider/keyword shortcuts which validation missed: at least 171 of 1,570 ML auto-accepts are semantically likely wrong, with another 141 bank-lease rows materially ambiguous. The inferred data is therefore **not upload-ready**. The final Cloud Run ONNX artifact is also incomplete because INT8 quantization changes 12 of 308 threshold decisions. Do not deploy or upload the current outputs.

## Plain-language explanation of the original bug

Purchases (`COMPRAS`) and sales (`VENTAS`) were previously mixed or lost during deduplication/training. This allowed a purchase such as firewood to look like a firewood sale, and known sales such as milk or calves could be shown under the wrong frontend label. Folder-organized invoices were also treated too strongly even though one invoice can contain unrelated line items.

The recovery now puts the source transaction direction at the beginning of every model input:

`[COMPRAS|VENTAS] | item name | description | provider`

It also uses row-level client product evidence above invoice-folder placement. Folder-derived rows were manually audited instead of becoming runtime lookup rules.

## Original sales bug: direct proof

Raw sales data contains 125 rows:

- 118 have an authoritative exact sales phrase.
- 7 are genuinely unknown asset/other sales and must be reviewed.
- The 118 known rows are 47 milk, 18 cows, 2 heifers, 50 male calves, and 1 female-calf row.
- Both male and female calf phrases map to `ING-0.4` (Calf Sales).

Normal backend result:

- Milk -> `ING-0.1` Milk Sales.
- Cows -> `ING-0.2` Cow Sales.
- Heifers -> `ING-0.3` Heifer Sales.
- Male or female calves -> `ING-0.4` Calf Sales.
- All 118 known rows are protected by exact transaction-aware rules.
- The seven unknown sales are never auto-accepted by ML.

ML-only bypass result (exact rule deliberately disabled):

- 117/118 correct = **99.15%**.
- Milk: 47/47.
- Cows: 18/18.
- Heifers: 2/2.
- Calves: 50/51.
- The only miss was `VENTA DE TERNERAS`: ML predicted Heifer Sales, but at only 0.5449 top confidence and 0.1209 margin. It therefore would not pass the 0.75/0.50 auto-accept policy. The exact rule correctly returns Calf Sales.

This bypass mixes known training and validation history, so it proves the model learned the repaired sales pattern; it is not an independent production-accuracy estimate. Evidence: `sales_model_bypass_audit.json` and `.csv` in this directory.

## Clean data used for the selected retrain

- 1,821 authority-resolved gold rows.
- 1,566 distinct transaction-aware inputs after safe same-label deduplication.
- 1,711 COMPRAS gold rows and 110 VENTAS gold rows.
- 1,256 distinct train rows, 308 locked validation rows, 2 singleton rows excluded from ML splitting.
- 71 active client taxonomy categories.
- 67 categories are trainable in the ML model.
- Four active categories are not trainable: `ADM-1.9`, `ADM-2.3`, `ING-0.5`, `ING-0.6`.
- A separate seven accounting/no-XML categories are project-excluded; they are not part of the 71 active total.
- 56 training-label conflicts were corrected using higher-authority evidence.
- 97 unsafe/wrong rows were quarantined.
- All 399 folder-derived rows were audited: 277 kept, 34 corrected, 88 quarantined.
- 139 raw weak-category candidates were manually inspected; 83 were promoted, 38 rejected, 13 already existed, and 5 still need client clarification.
- Final cross-label contradiction count: zero.

Authority order used during cleanup:

1. Exact row-level client product/service evidence.
2. Direct client examples.
3. Manually verified taxonomy reasoning.
4. Folder placement only after row-level audit.
5. Silver/Ollama labels last.

No folder-derived runtime lookup was added.

## Training performed

- SetFit multilingual MPNet base.
- Full transformer encoder trainable, including token embeddings.
- CPU AdamW, batch size 8, 1,500 contrastive steps.
- Approximately 42 minutes.
- Measured token-embedding maximum absolute change: `0.00195149`, proving embeddings were updated.
- MPS was rejected because its allocator repeatedly retained a roughly 732 MB optimizer-state block even at batch size 1. CPU training avoided freezing the encoder.

A later 300-step continuation experiment with extra proposed rows was rejected because it made confident false positives worse. The selected model remains `models/setfit_base_recovery_v1_3_1`.

## Model performance

Locked 308-row validation, model top prediction before deterministic routing:

- Top-1 accuracy: **76.30%**.
- Macro-F1: **69.82%**.
- Top-3 accuracy: **88.31%**.
- Income/sales accuracy: **95.24%** (20/21).
- Income/sales top-3: **100%** (21/21).

These overall numbers include many categories with very few examples. Macro-F1 is therefore more demanding than simple accuracy and exposes weak classes rather than letting large classes dominate.

## Threshold and false-positive/false-negative audit

The release policy stayed at the user-approved values:

- top confidence >= **0.75**;
- top1-minus-top2 margin >= **0.50**;
- weak classes and known semantic contradictions still go to review.

The threshold was **not increased** to hide bad training. Instead, authority conflicts were fixed, suspect rows were quarantined, the model was retrained, and the one remaining observed cascade lie was traced.

On the locked 308-row production cascade:

- 229 auto-accepted (74.35%).
- 229/229 correct.
- **0 false-positive auto-accepts.**
- 79 review-required.
- 44 review rows were actually predicted correctly. These are the measured conservative false negatives/review burden.
- 35 review rows were model errors, so review protected the client from them.

Within the 139 model-only COMPRAS validation rows:

- 60 passed 0.75/0.50 plus class/semantic gates.
- 60/60 were correct.
- Wilson 95% lower precision bound: 93.98%; this is evidence, not a guarantee on unseen data.

The 79 review reasons were:

- 51 low confidence.
- 18 weak class.
- 1 vehicle-vs-machinery inspection ambiguity.
- 2 glove taxonomy conflicts.
- 5 electricity lines lacking an exact meter/product resolution.
- 1 fertilizer-type ambiguity.
- 1 irrigation contradiction guard.

The irrigation case was `R.N.PIBOTE RIEGO R 24`, truth `EXP-9.2`, while ML confidently predicted motorcycle maintenance `EXP-13.2` (0.781 top1, 0.713 margin). An attempted training continuation made the broader audit worse and was rejected. A narrow semantic contradiction guard now sends explicit irrigation wording to review only when ML predicts a non-irrigation category; it does not assign a label or create a broad lookup.

Counterfactual audit—forcing ML even when an authoritative client product lookup exists:

- 112 would pass the model threshold.
- 109 correct, 3 wrong (97.32%).
- All three wrong rows are row-level client-product examples.
- Production is safe because the authoritative product lookup runs before ML and wins.

This distinction matters: there were zero observed false auto-accepts in the real cascade, but the ML score alone is not infallible.

## Deterministic backend architecture

Runtime order is deliberately small:

1. Electricity meter lookup, COMPRAS only.
2. Exact active taxonomy name or approved alias, transaction-aware.
3. Original row-level product/service lookup, COMPRAS only.
4. Direction-masked SetFit model.

There is no folder lookup and no generic client-example lookup. Product hits short-circuit ML. Known sales exact phrases short-circuit ML. Unknown sales require review. DTE-43 liquidation purchases require review until the client provides a purchase-side livestock category.

## Raw inference data and zero-price cleanup

Local XML inventory:

- 5,195 XML invoices.
- 12,206 genuine XML detail lines before junk filtering.
- 5,166 standard `Documento` invoices.
- 29 DTE-43 `Liquidacion` invoices containing 103 genuine nonzero livestock-purchase lines. The old parser silently skipped these.
- 497 explicit zero-value lines.
- 440 manually/audit-rule-confirmed junk notes, headers, separators, totals, references, and template metadata excluded.
- 57 zero-value lines retained because they may be real/free/bundled/correction items.
- Expected retained inference lines: **11,766**.
- Parser errors: zero.

Actual FP32 real-data replay through the entire backend cascade:

- 1,587 meter-lookup rows.
- 137 exact taxonomy/alias business-rule rows.
- 2,640 product/service lookup rows.
- 7,402 ML rows.
- 5,934 total auto-accepts.
- 5,832 total review-required.
- 50.43% overall auto-accept rate.
- 1,570 ML-source auto-accepts.
- 118 known sales auto-accepted by exact rule; 7 unknown sales reviewed.
- Zero purchase-to-income or sale-to-expense direction violations.
- 207 auto-accepted rows with authoritative exact truth, all 207 consistent.

Independent semantic inspection found a conservative minimum 171 likely-wrong ML auto-accepts (10.9% of ML auto-accepts), plus 141 ambiguous Banco BICE lease rows. Important families include:

- 89 food/drink lines mapped to `ADM-1.6` office/cleaning supplies.
- 27 non-machinery rentals mapped to machinery/vehicle rental.
- 23 soda/refrigerant/appliance/fitting lines mapped to natural gas.
- 15 bottled-water minimum-charge lines mapped to mobilization.
- Two diesel containers mapped to diesel fuel because two silver gold rows are wrong.
- WD-40 mapped to agrochemicals.
- A waist bag mapped to food/lodging.

The main causes are provider overfitting, literal keyword shortcuts, sparse coverage across 67 classes, and a small number of wrong lower-authority silver labels. A SetFit logistic score is not a calibrated guarantee that an unfamiliar row is correct.

The review audit also found at least 685 repeated likely-correct rows that could be recovered with user-approved, authoritative aliases/product-family rules: 447 gasoline rows, 78 rodent-control rows, 60 Biolact rows, 34 lime rows, 15 Oracid rows, 14 milk-filter rows, 24 animal-lab rows, and 13 collective-insurance rows.

Zero value alone is never used as a deletion rule. The 440 exclusions have explicit reconciliation keys so a future Supabase update can delete only those known stale junk rows.

The 103 DTE-43 lines are retained but force review. They are COMPRAS livestock settlements, and mapping them into sales categories would recreate a direction bug.

## What is and is not ready for Supabase

The five-table local bundle builder exists for `categories`, `companies`, `item_catalog`, `invoices`, and `invoice_items`. It preserves all 5,195 invoice headers and the 11,766 retained lines, and produces 440 explicit junk reconciliation keys.

The current FP32 replay files exist under `reports/recovery_v1_3_1/local_replay/`, but they must not be uploaded because the raw semantic audit found confident false positives. The final five-table bundle must be generated only after data correction, retraining, safety-policy approval, and a clean rerun. No remote upload has occurred. Do not use the old flat `line_item_predictions` loader; remote writes are disabled except dry-run because that schema is obsolete.

## Packaging blocker discovered at handoff

The FP32 model is valid, but `artifacts/v1.3.1` is not ready:

1. The global Python environment has SentenceTransformer 5.5.1, matching the trained model, but lacks the ONNX exporter.
2. `.venv-train` has the local ONNX tools but SentenceTransformer 3.4.1.
3. Exporting the underlying transformer directly is numerically close: manual INT8 audit found mean embedding cosine 0.99526 and the same 76.30% top-1 accuracy.
4. Nevertheless, INT8 changed which 12/308 rows cross the fixed threshold (3.90% decision disagreement), even though FP32 and INT8 each accepted 134 model-only validation rows in that raw comparison.
5. Maximum probability delta was 0.14317. Therefore the strict parity gate correctly refuses the artifact.

Do not weaken the parity gate. Recommended next choice: export FP32 ONNX (larger but faithful), measure threshold-decision parity, and use it if decision disagreement is zero. Only attempt INT8 calibration-aware quantization later if Cloud Run size/latency truly requires it.

## Exact next steps

1. Correct/quarantine the two wrong silver diesel-container labels and audit the weak/silver natural-gas rows.
2. Decide whether to add the eight narrowly evidenced aliases/product-family expansions that recover approximately 685 reviews. The user must approve this runtime expansion.
3. Prevent provider/keyword shortcuts from auto-accepting unfamiliar semantics; compare provider ablation or an embedding-neighbor/OOD agreement gate on the locked validation and real raw data rather than trusting confidence alone.
4. Retrain the full encoder on the corrected data and rerun locked validation plus the complete raw semantic audit.
5. Modify `training/export_recovery_onnx.py` to support a non-quantized FP32 ONNX artifact and keep the strict zero threshold-decision-disagreement gate.
6. Export to `artifacts/v1.3.1`; do not overwrite v1.0.0 or v1.1.0.
7. Run final ONNX calibration:
   `python3 scripts/66_calibrate_and_audit_model.py --artifact artifacts/v1.3.1`
8. Rerun the sales bypass audit against ONNX:
   `python3 scripts/73_audit_sales_model_path.py`
9. Replay all local rows:
   `python3 scripts/67_local_transaction_replay.py`
10. Manually inspect every flagged auto-accept risk and review-burden group. Trace any confident error to training authority before considering a threshold change.
11. Build the five-table bundle:
   `python3 scripts/72_build_supabase_five_table_bundle.py`
12. Verify all manifest invariants are true: 5,195 invoices, 11,766 retained items, 440 junk keys, 29 DTE-43 headers, 103 DTE-43 lines.
13. Run `python3 -m pytest -q`. Do not run a live API path.
14. Build the local Docker image only; do not push or deploy.

## Important files

- Clean gold: `Data/candidates/recovery_v1_3_1/master_gold.csv`
- Data manifest: `Data/candidates/recovery_v1_3_1/manifest.json`
- Folder audit: `Data/candidates/recovery_v1_3_1/folder_line_audit.csv`
- Quarantine: `Data/candidates/recovery_v1_3_1/quarantined_wrong_labels.csv`
- Weak raw audit: `Data/candidates/recovery_v1_3_1/starving_category_manual_audit.csv`
- Locked split: `Data/candidates/recovery_v1_3_1/split_seed42.csv`
- Selected FP32 model: `models/setfit_base_recovery_v1_3_1`
- Validation audit: `reports/recovery_v1_3_1/calibration_and_validation_audit.json`
- Validation rows: `reports/recovery_v1_3_1/validation_predictions.csv`
- Sales bypass proof: `reports/recovery_v1_3_1/sales_model_bypass_audit.json`
- Zero-value audit: `reports/recovery_v1_3_1/zero_value_audit/inventory_summary.json`

## Git and rollback

Current local branch: `codex/transaction-aware-retrain-v2`.

Existing rollback commits:

- `6960eef` — pre-round recovery anchor.
- `09f0f51` — authority audit and transaction-aware v1.3.1 preparation.
- `44cbec4` — acceptance hardening and local release-audit preparation.

The final uncommitted work at this handoff includes the DTE-43 parser/replay protection, zero-line correction, threshold fixes, irrigation contradiction guard, exporter investigation, sales bypass proof, and this document. Do not stage the modified tracked `.pyc` file or the unrelated old `reports/recovery_v1_3_0/` directory.

## Remaining client decisions

- Which purchase-side category, if any, should receive the 103 DTE-43 livestock settlement lines?
- How should the seven unknown sales (vehicles/fixed assets/other income/machinery) be categorized?
- Resolve the five weak raw candidates marked `needs_client`.
- Supply examples for the four active but untrained categories if those categories must be predicted by ML.

Until those answers exist, review is the correct behavior for those specific rows—not a sign that the original milk/calf incident remains unfixed.
