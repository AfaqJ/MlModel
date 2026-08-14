# STATE — where this project is right now

Updated every session. Last 5 sessions only; anything older that still matters
lives in `DECISIONS.md`.

## Now

**The labelled dataset is corrected and live.** Supabase `nkdswofslslrumyraklv`
holds **11,746 invoice lines — 7,014 auto-accepted, 4,732 in review**, with zero
rows showing a label while awaiting review. Three categories the client created
on 2026-08-14 are populated: `AF-1.1` Compras de Animales (113 lines, CLP
529,541,100), `AF-2.1` Compras de Activo Fijo (19 lines, CLP 339,658,011),
`ING-0.7` Ventas de Activo Fijo (6 lines, CLP 112,474,790). The live `categories`
table now has 74 rows; **the deployed model still emits only the original 71** —
these three are rule-assigned, see D-028.

v1.3.3 remains live on Cloud Run (`mlmodel-00014-lrp`). No model change this
session. Branch `codex/transaction-aware-retrain-v2`, last commit on the session's
work is `ea46b49`; the only uncommitted paths are pre-existing (`call_graphs/`
deletions and a `Temp_Inference/README.md` edit that were dirty at session start).
Tests: 98 passing.

## Next

1. **Send the client email.** Three questions, drafted: the bank leases, farmland
   rental, and Shell/ENEX fuel. See `docs/CLIENT_CONVENTIONS.md` "Still open".
2. **Frontend fix — still the highest-value item and still untouched.** The UI
   renders `predicted_code` on rows awaiting review. Lower risk than it was now
   that `final_code` is NULL on every review row, but the UI still reads the
   wrong column. Same error class as the original incident.
3. **Gold defect before any retrain.** `FUNDO CHAPICAHUIN` and `FUNDO RAICES` are
   farm names sitting in gold as `EXP-6.3` (Cal); the model memorised them.
4. **On next retrain, handle the three new categories.** They have gold rows but
   the model cannot emit them. Also re-measure INT8 flip count — it worsened from
   12/308 (v1.3.1) to 15/312 (v1.3.3).
5. **Quantity parsing** — `GASOLINA 93` shows 62,648,532 litres. Chilean decimal
   format (`62.648,532`) read as thousands separators. Amounts are correct.
6. **Stale summary badges** — catalog list and detail page disagree on counts.

## What the review rows contain

Measured at 5,183 rows before the 2026-08-14 corrections; the shape holds at
4,732. Fuel is now fully triaged — everything left in fuel review is a genuine
client question, which is **not** true of the rest of the queue.

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

### 2026-08-14 — client conventions applied; dataset corrected and re-pushed

- **No model change.** Data, gold, docs and a new re-load script. 98 tests pass.
- **Petrol solved by a field we were never reading.** The client said invoices
  distinguish vehicle fuel from farm fuel; they do, in `<Transporte><Patente>`,
  which holds either the plate or the word "bidon". Resolved 676 of 753 petrol
  lines and corrected 236 labels — wrong in *both* directions, so no
  supplier-level rule could have caught it (-> D-029).
- **Three categories created and populated** — `AF-1.1`, `AF-2.1`, `ING-0.7`
  (-> D-028). Live `categories` is now 74 rows; the model still emits 71.
- **The scale of the missing-category damage was far larger than recorded.**
  Animal purchases were documented as 103 auction lines / CLP 254,529,000. Actual:
  **113 lines / CLP 529,541,100** — cows, heifers and calves bought direct from
  breeders, filed as *teat dip*, *veterinary services* and *mineral salts*. The
  model was 87-90% confident on those; only the familiarity gate kept them out of
  auto-accept. Found by grouping the review queue by total value, not by keyword.
- **CLP 377M of lease payments have no home** — Banco BICE, Santander, and a
  farmland lease, two of the three sitting in *Road Maintenance* because that
  category's own description contains the word "arriendo".
- **DIFOR merge** — 20 invoices where a printed table header parsed as the line
  item and carried the whole amount while the service name sat on a CLP 0 line.
  Merged; the money line survives and keeps its line number, so no renumbering.
- **Pushed live** via the new `scripts/82_apply_label_corrections.py` (-> D-031).
  Backup first: `backups/supabase_20260814T110447Z_pre_corrections/`.
- **Decided:** client authority outranks row volume (-> D-030). Written up in the
  new `docs/CLIENT_CONVENTIONS.md`.
- **Gotcha — a theory about the data is not a finding.** Claimed the co-op's
  plates were their delivery trucks, reasoning from what `<Transporte>` is *for*
  in the DTE schema. Afaq pushed back. One query killed it: **41 of the co-op's 47
  plate lines carry the same plates seen at the service stations** — Antillanca's
  own vehicles. A delivery fleet would be a disjoint set. That removed a client
  question that was about to be sent. **Method: when a field might mean two things
  depending on the supplier, check whether the values overlap across suppliers.**
- **Gotcha — PostgREST upsert is `INSERT ... ON CONFLICT`.** A partial-column
  payload fails the insert arm on every NOT NULL column it omits. Send whole rows
  or `PATCH`. Also `categories_id` is database-generated, so locally-invented
  UUIDs are meaningless — read ids back from live and remap.
- **Gotcha — Chilean RUTs can end in `K`.** A filename regex matching only digits
  before `.xml` silently dropped 11 invoices from an index and made them look like
  missing raw data. They were on disk the whole time.
- **Gotcha — `CAFE` is usually the colour brown.** `BOTIN NORSEG PRO CAFE 42` is
  a boot, not coffee. Nearly swept 14 rows into a food category.
- **Two scripts were numbered 81.** `81_backup_supabase.py` already existed; the
  new one was renamed to `82_`. `scripts/` is gitignored with ~22 files
  force-added, so `git ls-files` does not show what is on disk — check `ls`.


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
