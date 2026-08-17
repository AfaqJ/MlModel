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
table now has 74 rows; **the deployed model emits 67** — verified against
`artifacts/v1.3.3-int8/labels.json` → `classifier_classes` (67 entries) and
`model_card.json` → `trained_classes: 67`. Everything else is rule- or
lookup-assigned, see D-028.

v1.3.3 remains live on Cloud Run (`mlmodel-00014-lrp`). No model change this
session. Branch `codex/transaction-aware-retrain-v2`, last commit on the session's
work is `ea46b49`; the only uncommitted paths are pre-existing (`call_graphs/`
deletions and a `Temp_Inference/README.md` edit that were dirty at session start).
Tests: 98 passing.

## Next

1. **Process the client's reply.** The 2026-08-17 email was sent and Cristian has
   answered; the reply has **not** been read or applied. Four questions were
   asked — bank leases, farmland rental, the no-tag fuel default, COPEC `DETALLE`
   renaming. Start by reading it against `docs/CLIENT_CONVENTIONS.md` "Still
   open", and remember D-030: his answer outranks our row counts.
2. **One lease line is wrongly auto-accepted.** `Pago Vencido de renta de
   Arrendamiento Nº12 del contrato Nº…`, CLP 2,816,710, sits in `ADM-1.7` at
   confidence **0.7528** against a 0.75 threshold. The other 171 lease lines are
   all `review_required`. Flip this one to review — a data fix via
   `scripts/82_apply_label_corrections.py`, not a model change. Do it before any
   lease answer is applied, or it will be silently skipped.
3. **Frontend fix — still the highest-value item and still untouched.** The UI
   renders `predicted_code` on rows awaiting review. Lower risk than it was now
   that `final_code` is NULL on every review row, but the UI still reads the
   wrong column. Same error class as the original incident.
4. **Gold defect before any retrain.** `FUNDO CHAPICAHUIN` and `FUNDO RAICES` are
   farm names sitting in gold as `EXP-6.3` (Cal); the model memorised them.
5. **Run the `giro` variant — scaffolded but never trained.** `train_setfit.py`
   already accepts `--variant base|giro|both`, `training/provider_giro_map.csv`
   exists (440 providers), and `export_onnx.py` ships it into every artifact.
   But only `models/setfit_base/metrics.json` exists — there is **no
   `models/setfit_giro/`**, so the variant has never been measured. The deployed
   template is `[transaction_type] | item_text | description | provider`; giro is
   absent. Cheap to test, and it targets a real weakness: the supplier's declared
   line of business separates purchase from maintenance from rental where the
   item name alone cannot (`Excavadora` CLP 13,275,000 from a supplier whose giro
   is `ARRIENDO DE MAQUINARIAS`). Baseline to beat: base = 0.7441 accuracy /
   0.6768 macro-F1 / 0.8765 top-3 on 340 val rows.
6. **On next retrain, handle the three new categories.** They have gold rows but
   the model cannot emit them. Also re-measure INT8 flip count — it worsened from
   12/308 (v1.3.1) to 15/312 (v1.3.3).
7. **Quantity parsing** — `GASOLINA 93` shows 62,648,532 litres. Chilean decimal
   format (`62.648,532`) read as thousands separators. Amounts are correct.
8. **Stale summary badges** — catalog list and detail page disagree on counts.

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

**Single source: `docs/CLIENT_CONVENTIONS.md` → "Still open".** Do not maintain a
second list here; the copy that used to live in this file drifted and was still
naming livestock purchases, asset disposals, supermarket drinks and butane
cartridges as open after all four had been answered on 2026-08-14.

Status as of 2026-08-17: four questions asked by email, **reply received and
unread**. One question deliberately never asked and still worth asking — the
July 2026 onward invoices, which are the highest-value input available, because
~3,529 review rows are undertrained rather than genuinely ambiguous.

## Recent sessions

### 2026-08-17 — client email sent; barn and lease questions verified against data

- **No code changed. No data changed.** Working tree is exactly as it was at
  session start (`call_graphs/` deletions, `Temp_Inference/README.md`). Doc
  edits only: this file and `CLIENT_CONVENTIONS.md`.
- **The client email was drafted, fact-checked line by line, and sent.** Cristian
  has replied; **the reply is unread** — that is where the next session starts.
- **Every figure in the email was verified against `invoice_items.jsonl` before
  sending.** All matched except one Afaq had drafted from memory: BICE has **16
  distinct contract numbers, not 60**. Caught by grouping the 141 lines on the
  contract number in the item string.
- **The barn premise was wrong, and checking it changed the email.** The client
  worried a barn arrives as wood + nails across many invoices needing a project
  code. It does not: 5 contract-stage lines from one builder, CLP 152,521,235,
  already in `AF-2.1` and auto-accepted. The question became a statement.
- **Nearly sent a question that would have looked careless.** Two `Días galpon`
  lines were about to be cited as barn work. They are dated 21 and 31 January
  2025; the barn contract runs 6 May to 5 August 2025. Different building.
  **Method: on any claim that two invoices belong to the same job, check the
  dates before the words.**
- **Found one lease line wrongly auto-accepted** at 0.7528 against a 0.75
  threshold — see Next #2. 171 of 172 lease lines are correctly in review.
- **Corrected two claims I had made confidently in the same session:**
  1. Told Afaq the deployed model emits 71 categories (this file said so).
     It emits **67** — `labels.json` → `classifier_classes` and `model_card.json`
     → `trained_classes` both say 67. `CLAUDE.md` was right; STATE was wrong.
     Fixed. **The artifact is the authority on what the model can emit, not
     arithmetic on the category table.**
  2. Told Afaq the supplier `giro` was unread data, "like the Patente". Wrong —
     the training plumbing exists and the map ships in every artifact. What is
     true is that it has **never been trained or measured**. See Next #5.
- **Costed an LLM pass over the corpus, since Afaq's stated blocker was price.**
  Batched, terse output: ~$2 Haiku 4.5, ~$4 Sonnet 5, ~$9 Opus 5 for all 11,746
  lines — one-time, not recurring. With per-line thinking, ~8× that. **Not
  decided**; no D- entry. Deferred behind settling the data ambiguities first.
- **Argued the reasoning-vs-data point and it held up under the data.** Of the
  4,732 review rows, ~32% (ambiguity, client-only context, meaningless names, no
  valid category) are unsolvable by *any* model including an LLM. The 68%
  undertrained bucket is where an LLM would genuinely win, zero-shot.

### 2026-08-14 — client conventions applied; dataset corrected and re-pushed

- **No model change.** Data, gold, docs and a new re-load script. 98 tests pass.
- **Petrol solved by a field we were never reading.** The client said invoices
  distinguish vehicle fuel from farm fuel; they do, in `<Transporte><Patente>`,
  which holds either the plate or the word "bidon". Resolved 676 of 753 petrol
  lines and corrected 236 labels — wrong in *both* directions, so no
  supplier-level rule could have caught it (-> D-029).
- **Three categories created and populated** — `AF-1.1`, `AF-2.1`, `ING-0.7`
  (-> D-028). Live `categories` is now 74 rows; the model emits 67 (this entry
  originally said 71 — corrected 2026-08-17 against the artifact).
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

<!-- 2026-08-11 (recovery v1.2.0 / incident root cause) dropped 2026-08-17 at the
5-session limit. Nothing lost: the root cause is D-001 and the dedup rule it
produced is a hard limit in CLAUDE.md. Full narrative in git history. -->
