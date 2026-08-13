# STATE — where this project is right now

Updated every session. Last 5 sessions only; anything older that still matters
lives in `DECISIONS.md`.

## Now

**v1.3.3 is live in production and the original incident is closed.** Revision
`mlmodel-00014-lrp` serves 100% of traffic on Cloud Run (`mlmodel`,
`europe-west1`), running `artifacts/v1.3.3-int8` (284 MB). All 11,766 invoice
lines across 5,195 invoices are uploaded to Supabase `nkdswofslslrumyraklv`:
6,583 auto-accepted with `final_code` set, 5,183 in review with `final_code`
NULL. The 47 `VENTA DE LECHE` lines (CLP 3.8bn) that production had filed as
*Road Maintenance* and *Freight* are now `ING-0.1`, auto-accepted via exact
business rule.

Branch `codex/transaction-aware-retrain-v2` is **dirty across 67 paths** — last
commit `2ed3a87`. Nothing from the v1.3.3 session *or* the doc restructure is
committed. Tests: 98 passing. Artifacts are gitignored and rebuildable from the
exporter.

## Next

1. **Commit — do this before starting new work.** Three suggested commits:
   the VENTAS-only business-rules change; the artifact/deploy tooling
   (`.gcloudignore`, exporter, `familiarity.py`, new tests); and the docs
   restructure. 67 dirty paths on one branch is hard to review or revert.
2. **Frontend fix — highest value available.** The UI renders `predicted_code`
   in the Category column on rows where `final_code` is NULL, so a CLP 45M "fat
   cow" displays as *Milking Parlour Maintenance*. Frontend only; no backend
   change. This is the same display error class as the original incident.
3. **Gold defect, fix before any retrain.** `FUNDO CHAPICAHUIN` and `FUNDO
   RAICES` are farm names sitting in gold as `EXP-6.3` (Cal); the model
   memorised them. Harmless today — only ever invoiced by SERVICIOS AGRICOLAS
   CORPAL — but it is the same shape as the `Item` row that once stamped 32
   invoices.
4. **On next retrain, re-measure INT8.** Flip count is a property of these
   specific weights and worsened from v1.3.1 (12/308) to v1.3.3 (15/312). The
   exporter refuses by default; ceilings must be passed explicitly.
5. **Stale summary badges** — the `VENTA DE LECHE` detail page reads "seen in 1
   other category" when live data has exactly one everywhere. Cache or history
   table. The catalog list shows 37 lines where the detail page shows 47
   invoices, so more than one aggregate is stale.
6. **DIFOR split rows** — 20 invoices where the money sits on a printed column
   header and the service name on a CLP 0 line. Fix is an UPDATE plus a DELETE;
   `invoice_line_number` does not need to change.
7. **Quantity parsing** — `GASOLINA 93` shows 62,648,532 litres. Chilean decimal
   format (`62.648,532`) read as thousands separators. Amounts are correct;
   quantity and average-unit-price columns are not.

## What the 5,183 review rows actually contain

| bucket | rows | share |
|---|---:|---:|
| Undertrained — often already correct | 3,529 | 68% |
| Genuine ambiguity in the wording | 867 | 17% |
| Context only the client knows | 423 | 8% |
| Meaningless item name (real spend, CLP 114M) | 254 | 5% |
| No valid category exists | 110 | 2% |

The largest group is **not** ambiguity. `"Traslado de terneras"` → Freight at
0.40; `"excavadora JCB"` → Machinery Maintenance at 0.23. Obvious to a human;
the model has simply never seen that phrasing. **This is what the client's next
labelled batch should target** — it is the highest-value input available.

Genuine ambiguity looks different: `"Reparación y mantencion"`, `"MATERIALES"`,
`"Ayuda en Moro chico"` — lines naming no object at all. More data will not fix
those.

Prediction-source spread on the live upload: model 6,238 · product_lookup 2,640
· meter_lookup 1,587 · client_evidence_backfill 720 · silver_audit_backfill 377
· business_rule 137.

## Open questions — blocked on the client

Each blocks rows that no amount of model work can fix.

1. **Which category receives livestock purchases?** 103 DTE-43 auction lines,
   CLP 254,529,000. The taxonomy has "Sale of Cows" but nothing for buying one.
2. **Where do asset disposals go?** 7 sales lines — truck, machinery, fixed
   assets. Only six income categories exist, all livestock or milk, and two of
   those have zero training examples.
3. **Is service-station fuel Bencina or Movilización?** 133 lines.
4. **Where do supermarket drinks go?** No gold either way.
5. **Are butane cartridges `EXP-11.5` or `EXP-16.2`?** Gold currently says both.
6. **Labelled examples of contractor free-text** — the highest-value input
   available. ~3,500 review rows are undertraining, not genuine ambiguity.

## Recent sessions

### 2026-08-13 — context architecture; 15 docs → 7

- **No code changed.** Docs, plus three doc-reference fixes in `training/`.
- Built the context architecture: repo-root `CLAUDE.md` (front door, auto-loads),
  `AGENTS.md` (one-line pointer so Codex loads the same thing), and this file.
  Deleted 15 overlapping docs across 4 locations — `MLMODEL.md`, `blueprint.md`,
  `CONTEXT_HANDOVER.md`, the field report, `FLOW.md`, both `HANDOVER_v1.3.x`,
  `guides/`, and the old `docs/README.md`.
- Recovered 11 decisions that were never recorded: D-016–D-024 from the v1.3.2
  and v1.3.3 sessions, D-025 (why SetFit/mpnet) and D-026 (why Cloud Run) from
  `MLMODEL.md` before deleting it. Fixed a duplicate `D-012`.
- **Decided:** context lives in the repo, superseded docs are deleted not
  archived, and memory never duplicates the repo (→ D-027).
- **Corrections found while auditing, all now in the docs:** gold is 1,837 rows
  / 67 classes / 26 weak (the docs said 1,604 / 66 / 31); `CONSTRAINTS.md` still
  banned the Supabase upload and Cloud Run deploy that had already happened;
  `Temp_Inference/README.md` claimed loader thresholds 0.80/0.10 against the
  code's 0.75/0.50.
- **Two real defects, not just doc rot:**
  1. `train_recovery_setfit.py` defaults to `recovery_v1_3_1/` while the
     exporter defaults to `recovery_v1_3_2/`. Retrain without explicit `--gold`
     and you silently train on the previous generation. Now in `CONSTRAINTS.md`.
  2. v1.3.3-int8 **did not meet** the exporter's default parity ceilings — it
     shipped by raising them from 0.03/0.0 to 0.07/0.05. Working as designed,
     but undocumented until now. See D-017.
- **Gotcha — an "obviously fine" doc is the dangerous one.** The files that
  called themselves context docs got audited; `guides/` and `reports/*.md` did
  not, and both were wrong. `review_ambiguity_analysis.md` claimed 6,927
  auto-accepts against the shipped 6,583. Audit by *content*, never by filename.

### 2026-08-12 — v1.3.3 INT8 artifact + Cloud Run deploy

- Narrowed business rules 95 → 28, **VENTAS-only**. `scripts/64` now emits
  `ING-*` leaves only and rejects expense-side aliases (→ D-015).
- Built two artifacts via a now-parameterised `training/export_recovery_onnx.py`:
  `v1.3.3` FP32 (1.1 GB, reference only) and `v1.3.3-int8` (284 MB, deployed).
- `app/core/model_loader.py` now hard-fails when `familiarity_index.npz` is
  missing — it was silently disabling the kNN gate.
- Tests went 57 passed / 11 failed → **98 passed**.
- **Decided:** INT8 over FP32 — FP32 peaks at 1.92 GiB and is OOM-killed in the
  2 GiB box (→ D-016). Weak-class guard kept (→ D-017). Familiarity gate kept
  (→ D-018). Concurrency 4 → 1, timeout 300 → 600 s (→ D-019).
- **Gotcha — parity gate failed 4× at `cosine=4.36`.** Impossible for a cosine,
  and that impossibility is the only reason it got investigated. Cause was not
  the model: `np.sum(ref * onnx, axis=1)` wrote its product back into `ref`, so
  the denominator read a squared buffer. Fixed with norms computed before the
  dot product, `np.einsum` with explicit output, float64 copies, and a hard
  `cosine > 1` check. **MPS, onnxruntime and subprocess timing are all ruled
  out — do not re-chase them.**
- **Gotcha — `.gcloudignore` is required.** Without it `gcloud builds submit`
  falls back to `.gitignore`, which excludes `artifacts/*`; the image builds
  successfully with **no model inside** and fails at first request instead of at
  build time. It also needs the `artifacts/*` re-exclude line or `!artifacts/`
  drags in the 1.1 GB FP32 build.
- **Gotcha — do not size Cloud Run from local Docker `--cpus 1`.** Local said
  342 ms/row; real Cloud Run vCPU does 103 ms/row. 3.3× pessimistic, macOS VM
  overhead. A 500-row batch takes 51 s.

### 2026-08-12 — v1.3.2 confident false positives

- v1.3.1 was blocked: the raw replay found ≥171 of 1,570 model auto-accepts
  (10.9%) semantically wrong while sitting above the 0.75/0.50 thresholds —
  biscuits as office supplies, soft drinks as natural gas, WD-40 as
  agrochemicals. Every one of those families is now at **zero**.
- Three measured causes: provider shortcut (`RENDIC → ADM-1.6` learned from 21
  gold rows), discarded client evidence plus wrong silver labels, and the fact
  that a closed-set logistic head must put every input *somewhere*.
- **Decided:** fix the data and the training, never the threshold — 0.75 stayed
  (→ D-020). Provider *dropout* in training rather than removing the provider
  or adding a runtime ablation gate (→ D-021). Relabel quarantined rows instead
  of dropping them (→ D-022).
- **Decided:** removed twelve hardcoded Spanish gates Claude had added — Afaq's
  call, and the most important correction of the round (→ D-023).

### 2026-08-11 — recovery v1.2.0 and the incident root cause

- Root-caused the production incident: the historical silver→gold promotion
  deduped on `(normalized_item_text, category_code)` while the model consumes
  `item_text | description | provider`. 47 distinct milk-sale rows collapsed to
  one; the trainer then excluded the 1-example class; the UI displayed the
  resulting low-confidence `review_required` suggestion as a final answer.
- Independent audit run and acted on. D-001 through D-014 recorded.
- Full narrative was `docs/ML_MODEL_INCIDENT_RECOVERY_FIELD_REPORT.md`, deleted 2026-08-13; recoverable from git history.
