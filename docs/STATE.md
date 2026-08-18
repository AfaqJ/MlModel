# STATE — where this project is right now

Updated every session. Last 5 sessions only; anything older that still matters
lives in `DECISIONS.md`.

## Now

**The client's 2026-08-17 reply and the confirmed post-recovery corrections are
applied locally and live.** The payload in
`reports/recovery_v1_3_3/supabase_upload/` holds **11,746 lines — 7,143
auto-accepted and 4,603 in review**, with zero rows showing a label while
awaiting review. **Live Supabase now matches exactly:** 11,746 lines, 77
categories, 7,143 auto / 4,603 review. A complete verified pre-write backup is
`backups/supabase_20260817T105217Z/`.

Categories are now **77**. Three were added this session from the client's reply
(`scripts/83_apply_client_reply_2026_08_17.py`): `EXP-15.8` Leasing (158 lines,
CLP 343,684,709), `EXP-15.7` Arriendo Otros Predios (14 lines, CLP 33,432,633),
`EXP-15.6` Arriendo Predio Lecheria (**0 lines** — the client named it, but no
invoice can be assigned to it without him naming the property; see
`CLIENT_CONVENTIONS.md` §7). The three from 2026-08-14 are populated: `AF-1.1`
(113 lines, CLP 529,541,100), `AF-2.1` (22 lines, CLP 366,238,095 — 19 plus the
3 lease buyouts added this session, which stay in review), `ING-0.7` (6 lines,
CLP 112,474,790).

**The deployed model emits 67** — verified against
`artifacts/v1.3.3-int8/labels.json` → `classifier_classes` (67 entries) and
`model_card.json` → `trained_classes: 67`. Everything else is rule- or
lookup-assigned, see D-028. The three new codes are rule-assigned and cannot be
predicted.

v1.3.3 remains live on Cloud Run (`mlmodel-00014-lrp`). No model change this
session. Branch `codex/transaction-aware-retrain-v2`. Tests: **98 passing**
(was 108; the 10 catalog-prototype tests were deleted with the prototype).

**Item-catalog cleanup is PARKED, waiting on a client meeting.** All prototype
code, generated preview data and its design doc were deleted on 2026-08-18 —
the schema was our assumption and the meeting may invalidate it (D-036).
Nothing was ever applied: no Supabase, staged-payload, raw-XML or frontend
change was made at any point. The measured findings survive in the client brief
(below); the code does not, and should not be rebuilt from memory.

**All correction scripts are now tracked in git.** `scripts/` is gitignored with
files force-added individually, and `80`, `81`, `83`, `84`, `85` had been left
untracked — the scripts that loaded Supabase, back it up, and applied the client
reply and the confirmed triage corrections. A `git clean -fdx` would have
destroyed them. Force-added 2026-08-18; 29 scripts tracked. **When adding a
script under `scripts/`, `git add -f` it in the same commit.**

## Next

1. **Item catalog — hold until the client answers.** The brief published
   2026-08-18 states the position: live `item_catalog` has **5,411 entries for
   11,746 invoice lines**, because the item name is the key and often carries a
   changing value. Measured breakdown: 950 entries are billing values in the
   name (→ 68 groups); 132 are placeholder names like `Item`/`DETALLE` (120
   rescuable from their description); ~300 are wording variants of the same
   product; 765 are spec variants (→ 297 groups) and are the client's call;
   4,168 entries appear on exactly one invoice line, ~3,544 of them with no
   sibling to merge with at all. Safe cleanup alone gets 5,411 → ~4,300;
   collapsing specs too gets ~3,850.

   **Seven questions went to the client**: pack sizes (WD-40 226g vs 458ml);
   size-as-the-product (clamps, needle gauges); shoe/garment sizes; pipe and
   fitting diameters (349 entries → 129 groups, the largest block); cattle sale
   lots (30 entries, 30 lines); freight by destination (43 entries, 60 lines);
   flavour and colour variants. **Do not start any implementation until these
   are answered** — and then build from the answers, not from the old design.

   Settled already, by Afaq: **licence plates stay part of an item's identity.**
   Maintenance on truck A is a different item from truck B, so the client can
   see one vehicle's cost history. Only the wording around the plate is
   normalised. The deleted prototype did the opposite.
2. **Work the 4,603 review rows — Afaq's stated next task.** Resume label
   cleanup: get final labels onto the rows sitting in review. Start from the
   bucket table below — **~3,529 (68%) are undertrained, not ambiguous**, so
   they are mostly already correct and just need confirming; the ~32% that are
   genuine ambiguity, client-only context, meaningless names or no-valid-category
   cannot be solved by any model. Rank by total value, not keyword: that is how
   the CLP 529M animal-purchase gap was found. Corrections go through a new
   numbered script, dry-run first, then script 82 — never a direct write.
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
6. **On next retrain, handle the six new categories.** `AF-1.1`, `AF-2.1`,
   `ING-0.7` (2026-08-14) have gold rows; `EXP-15.6`, `EXP-15.7`, `EXP-15.8`
   (2026-08-17) do **not** — no gold was written for them, deliberately, because
   nobody asked for it. Decide before retraining: `EXP-15.7`/`EXP-15.8` have
   learnable wording (`ARRIENDO FUNDO …`, `Renta de Arrendamiento … del contrato
   …`), `EXP-15.6` has no rows at all and would trip the "fewer than 2 examples
   must fail loudly" limit. Also re-measure INT8 flip count — it worsened from
   12/308 (v1.3.1) to 15/312 (v1.3.3).
7. **Quantity parsing** — `GASOLINA 93` shows 62,648,532 litres. Chilean decimal
   format (`62.648,532`) read as thousands separators. Amounts are correct.
8. **Stale summary badges** — catalog list and detail page disagree on counts.

## What the review rows contain

Measured at 5,183 rows before the 2026-08-14 corrections; the broad shape holds
at the current 4,603. Fuel is largely triaged; 24 rows with unrecognised
plate-field values were deliberately moved to review rather than guessed.

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

Status as of 2026-08-17: all four emailed questions **answered and applied**.
Nothing from that round is waiting on him. What his answers left behind — the
missing default rule for untagged petrol, which farms have a milking shed, and
whether the three lease buyouts are asset purchases — is in that same list.

One question deliberately never asked and still worth asking — the July 2026
onward invoices, which are the highest-value input available, because ~3,529
review rows are undertrained rather than genuinely ambiguous.

## Recent sessions

### 2026-08-18 (later) — catalog measured for the client, then prototype deleted

- **Deleted all catalog-prototype work at Afaq's instruction, before the client
  meeting.** Removed `scripts/86_build_catalog_prototype.py`,
  `tests/test_catalog_prototype.py`, `docs/PRODUCT_CATALOG_PROTOTYPE.md`, the
  20 MB `reports/catalog_prototype_2026_08_17/` preview, and the prototype's
  `.gitignore` block. None of it was ever committed, so it is gone for good —
  deliberately, because the schema was our assumption and the client's answers
  may imply a different shape. Tests back to **98 passing**. Labelling work,
  the staged v1.3.3 payload and all other uncommitted changes were untouched.
- **Measured the live catalog first, and that survives.** Against
  `item_catalog.jsonl` (not the prototype): 5,411 entries for 11,746 lines. The
  full breakdown and worked examples are in `Next` #1 and the published brief.
- **Corrected a rule Afaq reversed.** The prototype stripped licence plates into
  an attribute, merging four trucks' inspections into one item. He decided the
  plate stays part of the item's identity, so each vehicle keeps its own cost
  history. Any future build must follow the new rule.
- **Gotcha — number-stripping alone does not find the real duplicates.** It
  catches `Gasolina 93` variants but misses `WD-40 226 GRS` vs `LUBRICANTE
  ANTICORROSIVO WD 40 187 GRS`, where the words differ too. Whatever gets built
  after the meeting needs both, plus human inspection.
- **Gotcha — a flat embedding cluster is unsafe as a grouping.** It confidently
  places Gasolina 93 beside Gasolina 95, and pipe fittings across sizes. Useful
  as a work queue, never as the answer.
- **Gotcha — five correction scripts were one `git clean` from being lost.**
  Checking whether earlier Codex work was preserved revealed that `scripts/80`,
  `81`, `83`, `84`, `85` were untracked *and* gitignored. Only `82` had been
  force-added. Fixed. Verified no hardcoded credentials before adding.
- **Decided:** client answers gate all catalog work; prototype deleted, not
  parked (→ D-036).

### 2026-08-17 — confirmed recovery corrections and verified Supabase re-load

- **Applied 43 exact invoice-line corrections via
  `scripts/85_apply_confirmed_triage_corrections.py`, then re-loaded all five
  tables with `scripts/82_apply_label_corrections.py`; no model change.** 15
  client-rule labels are auto-accepted (13 supermarket foods
  → `EXP-1.1`, two restaurant/cafe meals → `ADM-1.5`). 28 rows are now review:
  13 unrecognised container values, 11 unrecognised plate values, and four
  items that are clearly not confirmed food but have no certain final category.
  Payload is now **7,143 auto / 4,603 review**; the invariant “review has no
  final label” passes. Backup first:
  `backups/supabase_20260817T105217Z/`; full live/local comparison passed with
  zero missing, extra, or different rows.
- **DTE-43 auction rows are not a defect.** A recovered audit claimed 103
  auction rows were cattle sales. Afaq verified they are all `COMPRAS`; they
  remain `AF-1.1` auto-accepted (103 rows, CLP 254,529,000). Do not reverse them
  on DTE type or supplier semantics alone.
- **Gotcha — recovered summaries can combine evidence with speculation.** The
  “28 junk plates” claim yielded only 11 exact raw-XML matches (CLP 459,408).
  The other 17 targets were not discoverable, so were not changed. `ENV000` was
  the missing spelling required to reproduce the 13-row container group.
- The remaining explicitly logged work is still `Next` #1–8. The newly ranked
  review clusters and client-question batch are deferred to the discussion that
  follows this correction pass; no new data rule was invented from them.
- **Documented the reload contract:** the staged local five-table JSONL payload,
  live schema ownership, latest backup, and required full-reload checks are now
  explicit in `CLAUDE.md`, `ARCHITECTURE.md`, `ROLLBACK.md`, and
  `TEST_CHECKLIST.md`.

### 2026-08-17 — client email sent; barn and lease questions verified against data

- **No code changed. No data changed.** Working tree is exactly as it was at
  session start (`call_graphs/` deletions, `Temp_Inference/README.md`). Doc
  edits only: this file and `CLIENT_CONVENTIONS.md`.
- **The client email was drafted, fact-checked line by line, and sent.** Cristian
  has replied, and the reply was read and applied later the same day.
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
