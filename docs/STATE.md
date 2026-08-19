# STATE — where this project is right now

Updated every session. Last 5 sessions only; anything older that still matters
lives in `DECISIONS.md`.

## Now

**Live Supabase and the staged payload are IDENTICAL — nothing is pending.**
Both hold **11,746 lines: 7,335 auto-accepted and 4,411 in review**, 77
categories, with zero rows showing a label while awaiting review. Two uploads
went out on 2026-08-19 via `scripts/82_apply_label_corrections.py`, each backed
up first and verified afterwards by an independent query, not by trusting the
script's own summary. Latest backup: `backups/supabase_20260819T064303Z/`.

**The `manual_recategorisation` migration is APPLIED to production.**
`002_add_manual_recategorisation_source.sql` was run in the Supabase SQL editor
by Afaq and confirmed by a probe that set and restored one row. Live now carries
all 8 `prediction_source` values. That file is the record of a schema change that
has actually shipped — do not lose it.

**The client email was sent 2026-08-19**, five questions covering construction
contractors (240 lines, CLP 137,094,957), hardware stores (1,534 / CLP
27,895,730), bank commissions (107), bale making (18 / CLP 56,581,822) and GEA
technician hours (27). Four rows are deliberately held in review because they
would pre-answer question 1 (→ D-041).

**The decision log was audited and pruned this session.** 41 entries. Three were
asserting things that had stopped being true — D-037 read as forbidding
promotions that are live in Supabase, D-016 implied the `business_rule` payload
tag still means the 28 sales rules (only 124 of 928 rows are `ING-*`), and D-042
gained that third drifted tag. `DECISIONS.md` is **no longer append-only**: a
dead entry is deleted once nothing cites it, and D-009 and D-011 were removed on
that test. **D-043 is new and changes how sessions run — name the decision you
are relying on, in plain language, before acting on it, not only when it
conflicts with what Afaq asked.**

v1.3.3 remains live on Cloud Run (`mlmodel-00014-lrp`). No model change. Branch
`codex/transaction-aware-retrain-v2`, **clean — everything is committed.**
Tests: **98 passing**. Five commits: `6b5bd41`, `8d67693`, `e749139`, `4754b2e`,
`41348bd`.

## Next

1. **The `prediction_source` consolidation (→ D-042).** Merge the two `manual*`
   tags, rename or retire `client_evidence_backfill`, and delete the dead
   `COLLAPSE_TO_SCHEMA` block in `scripts/78_prepare_supabase_upload.py`. Needs
   its own migration and its own dry run — deliberately not bundled with a label
   upload.
2. **Work the remaining 4,411 review rows.** The D-040 sweep is only partly
   done: a general pass over *all* consistent client folder conventions was
   measured (51 candidates) but only the judged ones were applied. Re-run it with
   the D-040 limits and read each family before promoting.
3. **The 141 vague-named rows the description rescues, CLP 106,758,176.** Review
   rows whose `item_text` is `Item`/`SERVICIOS`/`ANTICIPO` but whose
   `description` names the job outright — `FLETE MAICILLO`, `CONFECCION CAMINO
   YUTRECO`, `RETIRO DE PURINES`, `MANTENCION GRUPO ELECTROGENO`. Only **14
   rows, CLP 1,450,281** are genuinely blind. This is the largest readable block
   left and it was nearly written off as unreadable.
4. **Frontend fix — still untouched.** The UI renders `predicted_code` on rows
   awaiting review. Same error class as the original incident.
5. **Gold defect before any retrain.** `FUNDO CHAPICAHUIN` and `FUNDO RAICES` are
   farm names sitting in gold as `EXP-6.3` (Cal); the model memorised them. Also
   the four client-vs-silver contradictions recorded 2026-08-18.
6. **Run the `giro` variant — scaffolded but never trained.** Baseline to beat:
   base = 0.7441 accuracy / 0.6768 macro-F1 / 0.8765 top-3 on 340 val rows.
7. **On next retrain, handle the six added categories.** `EXP-15.6` still has
   **0 rows** and would trip the "fewer than 2 examples must fail loudly" limit.
   Also re-measure INT8 flip count — it worsened from 12/308 to 15/312.
8. **Item catalog — still parked** pending the client meeting (D-036). Live
   `item_catalog` holds 5,411 entries for 11,746 lines.
9. **Quantity parsing** — `GASOLINA 93` shows 62,648,532 litres; Chilean decimal
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

### 2026-08-18 (fourth pass) — audited the lookup and the silver backfill

- **Afaq's challenge held: three of the four silver-audit rows flagged as errors
  were not errors at all.** Each was already settled by a rule the client wrote,
  and "fixing" them would have overwritten his own convention:
  - `SMART BLUE ... FERTILIZANTES(B)-UREA`, CLP 67.3M — `SMARTBLUE FUNDO` is a
    `client_product_rule` → `EXP-6.2 Nitrogeno`, and the name ends in UREA.
  - `BIDON 20 LTS DIESEL` → `EXP-16.2` — `BIDON CERT. AMARILLO DIESEL 20 L` is a
    `client_product_rule` → `EXP-16.2`. It is a jerrycan, not fuel.
  - `VENTA MATERIAL`, CLP 13.03M — called meaningless from `item_text` alone.
    Its **description** is `MAICILLO`, road surfacing gravel, from an excavation
    contractor. `EXP-14.1 Mantencion Caminos` is right.
  **Method: read the description and search the client's rules before calling an
  auto-accept wrong.** Two of the three were caught only because the lookup was
  read afterwards.
- **One real finding, left for the client:** `SEMILLA BALLICA TAMA` sits in
  `EXP-8.1 Pradera Perenne` (CLP 5.28M) but TAMA is a short-rotation ryegrass and
  `EXP-8.2` exists. No client rule distinguishes varieties → question #12.
- **Four gold defects found where a silver audit contradicts a client label**
  on the same product: `CLAVO TERRANO` (client Cercos / silver Otros Gastos
  Lecheria), `LEVANTADOR DE VACAS` (client Salud Animal / silver Instalaciones),
  `MOSKIMIC FORTE` (client Otros Medicamentos / silver Agroquimicos), `ORBENIN
  E.D.C` (client Terapias Secado / silver Otros Medicamentos). **All four are
  gold-only — the payload follows the client code in every case.** They will
  poison the next retrain and must be fixed before it.
- **Lookup structure checked:** 13 entries have a blank provider and so match any
  supplier — all are specific brand names or exact service phrases, safe. 9
  entries have generic or very short names (`DIESEL`, `FLETE`, `Flete`); all are
  provider-scoped, and `Flete` → `EXP-4.2` is correct for the bale contractor.
- **The fuel/plate rule was then audited end to end and is 100% consistent.**
  All 756 gasoline lines, classified by what `<Patente>` actually contains:
  bidón in any spelling (109) → `EXP-11.4 Bencina`, no exceptions; a real plate
  (216) → `ADM-1.4 Movilizacion`; an unreadable plate (24) → review,
  deliberately; no tag at all (77) → review, which is the client's own answer
  *"Our team to place"*; no tag but covered by client evidence (327) → Bencina.
  **Zero misfiled fuel rows.** The bidón spellings in the wild are `BIDON`,
  `BIDO93`, `BIDO45`, `BIDO91`, `BIDO65`, `BIDO01`, and the transpositions
  `IBDO96`, `VIDO93`, `BIDI25`, `BIOD45`, `BID000`. **The production rule
  handles all of them; two separate ad-hoc audit regexes written this session
  did not.** Do not re-derive this rule in a throwaway script — read it.
- **The plate-vs-bidón scare, resolved.** 56 fuel rows from Estaciones de
  Servicio Paola looked like plated vehicle fuel auto-accepted as farm petrol,
  contradicting five `direct_client_example` rows putting that supplier in
  `ADM-1.4`. The `<Patente>` values are `BIDO93`, `BIDO45`, `BIDO91`, `IBDO96`,
  `VIDO93` — "bidón" plus the fuel grade, typos included. Bidón means farm fuel,
  so `EXP-11.4 Bencina` is correct and the production rule already handled the
  typos. **The audit script was wrong, not the data** (→ D-038).
- **`scripts/88_apply_lookup_audit_findings.py`: 98 rows promoted**, each backed
  by a client-written lookup rule *and* the model independently agreeing: 87 HDPE
  compression fittings → `EXP-14.3` (the client filed HDPE pipe there), 10 SMART
  BLUE → `EXP-6.2`, 1 MOSKIMIC → `EXP-2.5`. **The 15 HDPE rows where the model
  says Milking Parlour instead were left in review** — once the evidence stops
  being unanimous, it is not a promotion.
