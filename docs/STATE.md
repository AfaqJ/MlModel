# STATE — where this project is right now

Updated every session. Last 5 sessions only; anything older that still matters
lives in `DECISIONS.md`.

## Now

**Canonical catalog migration is ready locally and deliberately not applied.**
The approved payload has **11,746 invoice lines, 4,029 catalog rows and 8
aliases**, reducing the current 5,411-row catalog by 1,382. The raw item-name and
description SHA-256 is identical before/after. The guarded transaction passed
against a disposable PostgreSQL copy. Production Supabase remains unchanged.

Backend branch: `codex/canonical-catalog-migration`, local and unpushed.
Frontend branch: `codex/canonical-catalog-frontend`, local and unpushed. The
frontend production build passes and history now displays original invoice item
name and line description below the canonical catalog grouping.

The live accounting-category payload remains **11,746 lines: 7,335
auto-accepted and 4,411 in review**, 77 categories. No category or classifier
logic changed in this catalog work.

**The `manual_recategorisation` migration is APPLIED to production.**
`002_add_manual_recategorisation_source.sql` was run in the Supabase SQL editor
by Afaq and confirmed by a probe that set and restored one row. Live now carries
all 8 `prediction_source` values. That file is the record of a schema change that
has actually shipped — do not lose it.

v1.3.3 remains live on Cloud Run (`mlmodel-00014-lrp`). No model change. Branch
base `codex/transaction-aware-retrain-v2` is unchanged. Tests there remain 98
passing.

## Next

1. **Afaq inspects the catalog payload and frontend branch.** Nothing goes to
   Supabase or Git remotes until he explicitly approves it.
2. **If approved, take a fresh production backup/snapshot.** Rebuild if any
   item ID, old catalog ID, `item_text` or description changed; do not weaken
   the SQL preflight guard. Then apply the one transaction and independently
   verify 4,029 / 11,746 / 8 plus raw-field invariants.
3. **Push/merge the frontend only after separate approval.** Runtime alias and
   pattern matching remains deferred until the actual online ingestion writer
   is identified (D-044).
4. **The `prediction_source` consolidation (→ D-042).** Merge the two `manual*`
   tags, rename or retire `client_evidence_backfill`, and delete the dead
   `COLLAPSE_TO_SCHEMA` block in `scripts/78_prepare_supabase_upload.py`. Needs
   its own migration and its own dry run — deliberately not bundled with a label
   upload.
5. **Work the remaining 4,411 review rows.** The D-040 sweep is only partly
   done: a general pass over *all* consistent client folder conventions was
   measured (51 candidates) but only the judged ones were applied. Re-run it with
   the D-040 limits and read each family before promoting.
6. **The 141 vague-named rows the description rescues, CLP 106,758,176.** Review
   rows whose `item_text` is `Item`/`SERVICIOS`/`ANTICIPO` but whose
   `description` names the job outright — `FLETE MAICILLO`, `CONFECCION CAMINO
   YUTRECO`, `RETIRO DE PURINES`, `MANTENCION GRUPO ELECTROGENO`. Only **14
   rows, CLP 1,450,281** are genuinely blind. This is the largest readable block
   left and it was nearly written off as unreadable.
7. **Frontend category-review fix — still untouched.** The UI renders `predicted_code` on rows
   awaiting review. Same error class as the original incident.
8. **Gold defect before any retrain.** `FUNDO CHAPICAHUIN` and `FUNDO RAICES` are
   farm names sitting in gold as `EXP-6.3` (Cal); the model memorised them. Also
   the four client-vs-silver contradictions recorded 2026-08-18.
9. **Run the `giro` variant — scaffolded but never trained.** Baseline to beat:
   base = 0.7441 accuracy / 0.6768 macro-F1 / 0.8765 top-3 on 340 val rows.
10. **On next retrain, handle the six added categories.** `EXP-15.6` still has
   **0 rows** and would trip the "fewer than 2 examples must fail loudly" limit.
   Also re-measure INT8 flip count — it worsened from 12/308 to 15/312.
11. **Quantity parsing** — `GASOLINA 93` shows 62,648,532 litres; Chilean decimal
   format read as thousands separators. Amounts are correct.

## What the review rows contain

Measured at 5,183 rows before the 2026-08-14 corrections; the broad shape holds
at the current 4,461. Fuel is largely triaged; 24 rows with unrecognised
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

### 2026-08-25 — canonical catalog payload and frontend history branch prepared

- Afaq and colleagues approved one canonical ID per real product/recurring
  service, including merging non-functional sizes/months while preserving raw
  invoice names and descriptions (D-044). D-036 is unparked; D-034's evidence
  rule remains; D-035 now allows inspected non-functional spec merges.
- Fresh read-only snapshot: 11,746 lines and 5,411 catalog rows. The final
  reviewed payload has 4,029 catalog rows and 8 real wording aliases. It does
  not store OT numbers, months, sizes, case-only variants or junk placeholders
  as aliases.
- Generated the complete catalog, full invoice-item payload, per-line mapping
  ledger, manifest, schema and guarded transactional SQL under
  `reports/canonical_catalog_2026_08_25/`. Raw item/description SHA stayed
  `f87b6fde...51a515` before and after.
- The SQL committed successfully in disposable PostgreSQL 18: 4,029 catalog,
  11,746 lines, 8 aliases. A first test correctly rolled back on a local-only
  missing `service_role`; the grant was made conditional and the full test then
  passed.
- Frontend branch adds original item name and description to catalog history.
  Targeted ESLint passed and `npm run build` completed. Full-repo lint remains
  red on 12 unrelated pre-existing errors; none are in changed files.
- **No production Supabase write and no Git push occurred.** Future matching is
  documented as a backend-ingestion responsibility; this repo has no online
  ingestion writer today.

### 2026-08-19 — client email sent; two uploads; the client's own filing promoted over the model

- **The client email went out** after a full fact-check that caught two errors in
  the draft: 106 of the 107 commission lines are bank commissions and the 107th
  is an auction commission from Tattersall Ganado; and `HORA TECNICA` is followed
  by *initials*, not "two letters" — `CAL` is three, and three lines carry none.
  An assertion pass over all 29 figures caught both.
- **Migration applied and both uploads verified.** Live went 7,143/4,603 →
  7,285/4,461 → **7,335/4,411**. Every check was re-run independently against
  live rather than trusting script 82's own "all match" line. Source movement
  balanced to zero on the first upload (+327 `manual_recategorisation`, +152
  audited, −477 `model`, −2 `business_rule`) — proof nothing was invented or lost.
- **D-040 established and applied: a consistent client folder placement beats the
  model.** `file_audit` measured **98% self-consistent** (363 of 369 item-kinds in
  exactly one category; the 6 exceptions are all meter-dependent electricity).
  `scripts/90` and `scripts/91` promoted 54 rows on that basis — 18 DIFOR
  scheduled services, 19 staff/welfare rows, 4 `Revision Tecnica`, 4 GEA
  pezoneras, 2 SONDAJES pure-service, 3 exact-string matches.
- **`scripts/92` reverted 4 rows the same session (→ D-041).** They had been
  promoted on their descriptions, but they describe buying and improving pumps and
  commissioning a borehole, and the supplier's giro includes `Const. e
  Instalaciones`. Expense-vs-fixed-asset is question 1 of the email just sent.
- **Gotcha — the tag is not the evidence.** `client_evidence_backfill` was
  described to Afaq as "the client labelled this row himself." It is not: **0 of
  its 612 rows** trace to a highest-trust client label — 243 rest on `file_audit`
  and 367 on `silver_audit_v2`, our own keyword matching. He asked for the trace
  rather than accepting the tag, and the tag was wrong. → D-042.
- **Gotcha — 141 review rows worth CLP 106,758,176 were about to be written off
  as unreadable.** The draft email said ~254 lines "name no object at all". Afaq
  pointed out the description carries the product. Measured: of 155 vague-named
  review rows, **155 have a description and 141 are fully identifiable from it**.
  Only **14 rows, CLP 1,450,281** are genuinely blind. A claim that data is
  missing is a claim about *every* field on the record, and must be measured.
- **Gotcha — an assertion firing is information, not an obstacle.** `assert
  len(changed) == 20` fired at 31 in script 91. The 11 extra were DIFOR service
  intervals the client never filed — and inspection showed they were *justified*
  (client 3/3, model 18/18 unanimous). Without the assertion they would have gone
  in silently. A second assertion was added to keep that extension honest.
- **Gotcha — a correlate is not a key.** A proposal to route every contractor
  invoice inside the barn's build window to `AF-2.1` was rejected by Afaq on
  sight. The window contained a house repair at Maitén and a fence at Raíces.
  Replaced with: the money is concentrated, so hand the client the 10 contractors
  holding 73% of it in 93 lines and let his team adjudicate.
- **Gotcha — `bolón` is not `bolo`.** A substring match on the bale product root
  returned 28 rows; reading them showed only 18 were bale-making. The rest were
  wrapping film, netting, transport, a machine repair, and one line of **crushed
  stone** whose name differs by a single letter. Reading the rows also produced
  the finding that mattered — the *supplier* separates silage from hay where
  wording, property and date all fail.
- **The bale question was checked and is valid.** The client's own vocabulary does
  encode the split (`heno`/`pasto seco`/`paja` vs `silo`/`pradera`), but **all 18
  open rows carry none of those words** — they are bare or name only a property.
  He is also not perfectly consistent: `BOLOS SILO CHAPILCAHUIN` is filed as Hay
  while `BOLOS SILO YUTRECO` is Silage.
- **The decision log was then audited end to end, and three entries had drifted.**
  D-037 still stated the model-agreement bar that D-040 had removed the same day —
  applied literally it would have reverted the `Revision Tecnica` rows now live.
  D-016 is true of the runtime (`business_rules.csv` is 28 rules, all `ING-*`)
  but its payload tag drifted to mean "a script applied a deterministic rule":
  only **124 of 928** `business_rule` rows are `ING-*`. Both now carry pointers.
  Two suspected contradictions were checked and cleared: D-024 vs the bidón
  spellings (they live in `app/data/product_lookup.csv`, a data file, which is
  what D-024 asks for) and D-016 vs D-029 (structured DTE field, not supplier
  wording).
- **`DECISIONS.md` is no longer append-only, by Afaq's instruction.** D-009 and
  D-011 were deleted — both fully dead with zero inbound references. D-001 and
  D-034 were kept because `CLAUDE.md`, `CONSTRAINTS.md`, `ARCHITECTURE.md` and
  two scripts cite them. Deleting D-011 left D-015 pointing at a missing entry;
  caught and fixed. **Check inbound references before deleting, and re-grep
  after.**
- **Gotcha — the same failure appeared three times in one day, in three
  different files.** D-037, D-016 and D-027 were each true when written and none
  had been told the ground moved. The cheap fix is a habit, not an audit: when a
  change narrows an earlier entry, edit the earlier entry **in the same commit**.
  D-040 said "narrows D-037" only inside D-040, which is the half nobody reads
  first.
- **Decided:** D-040 (client filing beats the model), D-041 (never pre-answer an
  open client question in the payload), D-042 (`prediction_source` consolidation
  deferred to its own upload), **D-043 (name the decision before acting on it)**,
  and D-027 amended to drop append-only.

### 2026-08-18 (sixth pass) — lookup audit re-run and clean; client brief published

- **The delegated lookup audit was re-run and it came back clean.** The first
  run's temp file was verified empty (0 bytes) before re-running via
  `codex exec "$(cat reports/codex_lookup_audit_2026_08_18/SPEC.txt)"`. Output is
  saved at `reports/codex_lookup_audit_2026_08_18/codex_output.txt` (untracked —
  `git add -f` it if committing).
  **1 finding in 696 entries, not actionable** — line 390 `NEXGARD SPECTRA X 1
  TABLETA` (COLUN) in `EXP-16.2`, proposed `EXP-2.5`. It is a
  `client_product_rule`, 1 payload row, CLP 27,174, and his dog *food* goes to
  `EXP-5.3 Concentrado Otros Animales` by the same pet-follows-the-taxonomy
  logic. Verified independently, **not applied** (D-030). No script 90.
  **This closes the largest unverified risk in the payload**: `product_lookup`
  auto-accepts 2,639 rows and had never been read item by item.
- **D-037 and D-038 amended by Afaq** — amendments are inline in each entry,
  dated. D-037: a client rule is no longer the only route into auto_accept; the
  model plus an independent manual auditor (Claude or Codex) agreeing on what the
  object physically **is** now also qualifies. Where a client rule exists it still
  wins (D-030). D-038: with no rule, apply a finding only when beyond doubt;
  otherwise move it to the best category as a **corrected hint** and leave it in
  review.
- **Client brief published** —
  https://claude.ai/code/artifact/47769557-4221-4b7d-a29c-00ca2d3d88a7
  ("The Review Queue"). Eight **non-overlapping** questions covering 2,110 of the
  4,461 review lines. Also covers the fixed-asset answers, the nails/tools
  diagnosis (-> D-039), and the excluded-category audit.
- **Decided:** no "supporting tools" category — the gap is a default rule
  (-> D-039).
- **The review queue was re-partitioned so no line is counted twice.** The
  previous 13-question list double- and triple-counted: the hardware-store
  question *contained* the fasteners, fittings, welding and half the paint
  questions. Exclusive partition of the 4,461, priority-ordered:

  | group | lines | CLP |
  |---|---:|---:|
  | Hardware & building stores (6 suppliers) | 1,562 | 27,987,733 |
  | Supermarket goods | 284 | 2,040,767 |
  | Filters | 67 | 4,954,009 |
  | Fire extinguishers | 53 | 2,094,737 |
  | Tolls / TAG | 45 | 574,005 |
  | Bank commissions | 44 | 448,086 |
  | Bale making (`bolos`) | 28 | 59,464,922 |
  | GEA `HORA TECNICA` | 27 | 12,817,584 |
  | **Everything else — no shared question** | **2,351** | **852,671,372** |

  **The eight questions cover 47% of the lines but only 12% of the money.** State
  that plainly; the earlier framing implied the questions would empty the queue.
- **Excluded-category list fully checked.** Two claims were already known false
  (`Arriendo Predio Lecheria`, `Arriendo Otros Predios`). A third is false:
  `Impuestos, comisiones, multas` — 107 commission lines, CLP 6,768,282, from
  BICE / Banco de Chile / Santander, 63 already auto-accepted into `ADM-1.7`.
  The remaining three **do hold**: no `Arriendo Casas` invoices exist (Yutreco
  appears only as a place), no wage or payroll invoices exist.
- **Two auto-accepted families rest on `silver_audit_backfill`, which D-037 no
  longer accepts as promotion evidence** — 37 bank-commission rows and all 24
  ryegrass rows. Not disturbed, but they are why those two questions have zero
  rows stuck and are still being asked.
- **Fixable without the client:** `ASESORIA CONTABLE Y TRIBUTARIA`, CLP 505,363,
  suggested as `EXP-15.1 Servicios Agronomicos`; `ADM-1.8 Asesoria Contable`
  exists. Still in review, so no wrong label was ever shown.
- **Gotcha — a supplier-shaped bucket silently swallows product-shaped ones.**
  Counting "hardware store" and "fasteners" as separate questions triple-counted
  hundreds of rows. **When measuring a queue by category, assign each row to
  exactly one bucket in priority order and assert the buckets sum to the total.**
- **Gotcha — a normaliser regex that misses a spacing variant undercounts
  silently.** `SULFATO DE? ?COBRE` matched 3 of the 6 copper-sulphate rows;
  `SULFATO\s+(DE\s+)?COBRE` matches all 6. A count that disagrees with the docs
  is a regex bug until proven otherwise.
- **Doc corrections:** payload is **7,285 auto / 4,461 review** (measured), not
  7,286 / 4,460 — script 89 moved one more row than the previous entry recorded.
  Fixed in `CLAUDE.md` and throughout `STATE.md`.

### 2026-08-18 (fifth pass) — every auto-accept checked against the client's own rules

- **The whole payload was matched against client-decided products** — the 524
  products the client himself ruled on via `client_product_rule`,
  `direct_client_example`, `client_service_rule` or a family resolution, matched
  on product identity with sizes, codes and packaging stripped.
  **Result: 1 contradicting row in 7,286 auto-accepts.**

  | source | auto-accepted | contradicting a client decision |
  |---|---:|---:|
  | product_lookup | 2,639 | 0 |
  | meter_lookup | 1,587 | 0 |
  | model | 983 | 0 |
  | business_rule | 884 | 0 |
  | client_evidence_backfill | 611 | 0 |
  | **silver_audit_backfill** | **365** | **0** |
  | manually_audited_near_identical | 217 | **1** |

- **Afaq's concern about the silver backfill is answered: 0 of its 365
  auto-accepted rows contradict a client ruling.** The four known
  silver-vs-client conflicts are all in gold only and never reached the payload.
- **The one real hit is now an open client question, not a fix.**
  `SULFATO COBRE 25 KG.` sat in `EXP-7.0 AGROQUIMICOS` while the client's own
  rule files `SULFATO DE COBRE X 25 KL.` under `EXP-16.2 Otros Gastos Campo`.
  It was first moved onto the client's code; **Afaq reversed that** — copper
  sulphate is a fungicide and the standard hoof footbath, so the client's rule
  may have been written from the name rather than the use. All 3 non-lookup rows
  are now `review_required` with the agrochemical hint
  (`scripts/89_fix_client_rule_contradiction.py`). The 3 rows sitting directly on
  his `product_lookup` rule are untouched — only he can overturn his own decision
  (D-030). → client question #13.
- **Gotcha — the first run of this check reported 138 contradictions and all
  were my own bug.** Item names too short to identify a product (`93 S/P`,
  `G93`) normalised to an empty key, which collided with every other short
  client entry (`M.C.P.A X 1 LT`, `LI - 700 X 10 LT.`). The silver loop had a
  guard against the empty key; the loop for the other sources did not. **A
  normaliser that can return an empty key must refuse to match on it** — and
  a contradiction report that suddenly finds 138 hits deserves a debug pass
  before it is believed.

### 2026-08-18 (fifth pass) — checkpoint before the delegated lookup audit

**Where this stands right now, mid-task.** Payload is **7,285 auto / 4,461
review** (after script 89), 98 tests pass, invariant clean, **nothing uploaded** — live Supabase is
still 7,143 / 4,603. Scripts 86, 87, 88 are applied locally and tracked in git.

**Done this session, in order:** swept the 147 low-confidence model auto-accepts
(10 real errors, all substring collisions); dispersed misfiled hardware (script
86, 252 rows); promoted 55 rows on client product rules and re-hinted 78 (script
87); audited the silver backfill and the lookup structurally, then promoted 98
more (script 88). Hardware in narrow product accounts went 66 → 0. `EXP-1.1
Otros Gastos RRHH` went 313 → 173 review rows.

**What is queued, in order:**

1. **Codex: item-by-item audit of all 696 lookup entries** — delegated. Report
   is findings only; apply nothing without re-checking against client rules.
2. **Verify Codex's findings independently** before any script 89. Two vendors,
   independent eyes — and Codex will not know D-037 or D-038 unless told.
3. ~~**Silver backfill re-check**~~ — **DONE.** See the session entry below:
   every auto-accepted row in the payload was matched against the products the
   client decided himself. **1 contradiction in 7,286**, now fixed by script 89.
   `silver_audit_backfill` scored **0 of 365**.
4. **Client email** — 12 questions now logged in `CLIENT_CONVENTIONS.md`.
5. **Upload** — needs `002_add_manual_recategorisation_source.sql`, then script
   81 backup, then script 82.

**Standing rule set this session:** D-037 (a row reaches auto_accept only on a
rule the client wrote, with the model independently agreeing) and D-038 (read
the description and the client's rules before calling a row wrong).

**Gold is deliberately not being maintained right now.** Afaq's decision: fix the
payload first, then treat the settled auto-accepts as the new gold. So the four
known gold defects (`CLAVO TERRANO`, `LEVANTADOR DE VACAS`, `MOSKIMIC FORTE`,
`ORBENIN E.D.C`) are recorded, not fixed — see D-038 and the entry below.
