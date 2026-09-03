# STATE — where this project is right now

Updated every session. Last 5 sessions only; anything older that still matters
lives in `DECISIONS.md`.

## Now

**592 review rows were labelled and written to production on 2026-09-02 from the
client's reply. Review queue 4,411 -> 3,819, a 13.4% cut.** Plumbing 524 ->
`EXP-14.3`, GEA technician hours 25 -> `EXP-10.1`, bank and auction commissions
43 -> `ADM-3.1`, a category created for them. Verified against live: 592 rows
changed, exactly the 592 intended, 0 unintended, no raw invoice data altered,
`item_catalog` hash unchanged.

**`prediction_source` is now six values (D-047).** 2,066 rows collapsed to
`cleanup`; `user_selected` added for dashboard writes. Applied and verified —
only that column moved, raw and label hashes identical either side.

**The dashboard can now assign categories (D-048).** Clicking the category badge
on a catalog row opens a dialog listing that product's invoice lines; tick lines,
choose a category, save. It writes through a Server Action carrying the user's
session, not the browser. Merged to `feature/dashboard` (`7f11050`), 39 commits
ahead of `origin/main`.

**Nobody has pressed Done in the UI yet.** Every link is verified separately —
the constraint accepts `user_selected` (proven by a live round-trip that moved a
row between categories and reverted it byte-identical), the `UPDATE` policy for
`authenticated` exists as of 2026-09-03, and the code is merged. The chain
end-to-end has never been exercised by a real session. **That is the one
outstanding step on this feature.**

Backups: `backups/supabase_20260903T054820Z/` (latest, post-consolidation),
`.../20260903T054336Z` (pre-consolidation), `.../20260902T181937Z` (pre-labelling).

Live `mlmodel-00014-lrp` on Cloud Run is unchanged. No model work this session.

## Next

1. **Press Done on one line in the dashboard.** Ten seconds, and it closes the
   only unproven link in D-048. If it fails it is an RLS policy, not code.
2. **Accept the client's July-August 2026 categorised data.** He offered it
   unprompted on 2026-09-02: he has been using this project's categories in his
   own accounting since July and has two months already labelled by his team.
   68% of the remaining 3,819 review rows are undertrained phrasing that only
   labelled data fixes. **Highest-value item on the project, costs one email.**
   See `docs/CLIENT_CONVENTIONS.md` §9.7.
3. **Write the two lists Cristian asked for** — the construction contractors
   (§9.4) and the bale-making lines (§9.5). He said "send me the list and we
   categorize" for both. Neither is written.
4. **`ADM-3.1` has zero training rows.** Before any retrain it must be marked
   rule-assigned and untrainable the way D-028's six are, or the trainer trips
   the "fewer than 2 examples must fail loudly" limit.
5. **Honorarios and Remuneraciones have never been audited.** The "no XML"
   exclusion list was disproven for all four families tested
   (`docs/CLIENT_CONVENTIONS.md` §10); those two are keyword probes, not audited
   sets.
6. **Frontend, still open:** horizontal scrolling on the KPI tiles (asked for,
   wraps instead); the Pareto panel on Geografia measures geography rather than
   risk and should be relabelled or dropped; keyset pagination on the catalog is
   deferred — **search must move server-side in the same change or it silently
   starts matching only loaded pages.**
7. **Confirm how production deploys.** `STATE` records the live deploy as a CLI
   `vercel --prod` with no git metadata. If that is still true, merging to
   `feature/dashboard` updates the preview only.

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

### 2026-09-02/03 — client reply applied, 592 rows labelled, dashboard can now write

- **The client answered the 2026-08-19 email.** Three questions settled, two he
  took back. Recorded verbatim with provenance in `docs/CLIENT_CONVENTIONS.md`
  §9. Plumbing all to `EXP-14.3` including building plumbing; all GEA technician
  hours to `EXP-10.1`; commissions to an account that had to be created.
  Construction repair-vs-new-build and silage-vs-hay stay in review under D-041 —
  he asked for lists instead.
- **592 rows written and verified.** 524 + 25 + 43, no overlap. Post-write diff
  against the backup: exactly the intended rows changed, 0 unintended, 0 raw
  invoice fields altered, `item_catalog` hash identical.
- **`ADM-3.1 Impuestos, comisiones, multas` created**, 77 -> 78 categories.
- **`prediction_source` consolidated to six values** (→ D-047).
- **The dashboard got its first write path** (→ D-048): the category-assignment
  dialog, plus hover prefetch, a shared occurrence cache, the Geography tab
  owning its city selection, and the performance work from the audit branch —
  all merged into `feature/dashboard`.
- **Codex delegation: one run lost, one useful.** The first run died at 122,623
  tokens with **no files written** — the network dropped and it was holding
  everything in memory to write at the end. The spec now requires writing
  incrementally and resuming from whatever is on disk. The second run produced a
  539-line plumbing proposal that passed every structural check and correctly
  excluded both false positives predicted in advance.
- **Gotcha — `needs_review` is a GENERATED column.** The first labelling write
  returned `400: can only be updated to DEFAULT` and PostgREST rejected the whole
  batch, so nothing was written. **This is the same class as the
  `normalized_alias` gotcha of 2026-08-26, which is written down in this file,
  and it was read this session and still not applied.** After removing the
  column, a single-row canary confirmed `needs_review` derives itself from
  `decision`. Do a canary before a batch.
- **Gotcha — both agents independently invented `prediction_source='client_rule'`.**
  Claude wrote it, caught it; Codex wrote the identical bug in its own script,
  caught in review. The column is CHECK-constrained to a fixed list and nothing
  in the code says so. Two different models hitting the same trap means the trap
  is in the project, not the model.
- **Gotcha — a review found a real false positive that structural checks missed.**
  15 of 539 proposed plumbing rows were irrigation parts (K-Line, sprinklers).
  20 already-settled K-Line rows sit consistently in `EXP-9.2 Otros Gastos
  Riego`, so D-040 applies and the client's plumbing answer never covered
  irrigation. Found by grouping candidates by wording, not by reading 539 rows.
- **Gotcha — the prefetch I added to make the dialog faster hung it forever.**
  `preloadedLines` in an effect's dependency array meant a prefetch landing
  mid-fetch ran the cleanup, cancelling the dialog's own request, then
  early-returned. The data arrived and was discarded. Fixed by deciding once at
  mount and routing both callers through one shared cache;
  `scripts/check-occurrence-cache.ts` covers the race.
- **Gotcha — RLS grants read and write separately.** Anon sees **0 rows in every
  table**; the app works because logged-in users are `authenticated`, which had
  `SELECT` and `INSERT` policies but **no `UPDATE`**. The dialog would have
  failed on save. Policy added 2026-09-03.
- **Two theories died before the real cause was found.** The catalog page's
  slowness was blamed on a missing foreign-key index (already existed) and then
  on the view being recomputed per request (269 ms — fine). The actual gap was
  that the concurrent-paging fix had only been applied to one of the two files
  that page. **`EXPLAIN ANALYZE` killed both theories in one command; neither
  would have died by reading more code.**
- **Afaq's correction, and it was right:** approval to merge one branch was
  treated as standing approval for the next two. It is not. Ask each time.


### 2026-08-26 — catalog migration applied to production over PostgREST

- **Applied to live Supabase.** 4,029 catalog / 11,746 lines / 8 aliases, all
  verified by count against live plus the three largest merges. Backup
  `backups/supabase_20260825T190718Z/` taken first and count-verified.
- **The 2.6 MB single transaction was abandoned, → D-045.** It cannot be pasted
  into the Supabase SQL editor and this project holds no Postgres connection
  string — `Temp_Inference/.env.loader` has only REST keys, and every write ever
  made here went through PostgREST. Split into step A (schema, SQL editor),
  step B (`scripts/94`, REST), step C (unique index, SQL editor, ran 2026-08-26).
- **Pre-write preflight was clean**: live had not drifted at all in six days —
  0 lines with changed `catalog_item_id`, `item_text` or `description`, raw SHA
  `0d872c047f423bff` identical to the payload.
- **Referential integrity was verified independently of the manifest** before
  applying: 0 orphan lines, 0 null `catalog_item_id`, 0 catalog rows with zero
  lines, mapping ledger covering all 11,746.
- **`CLAUDE.md` corrected on two counts.** It still said item-catalog
  canonicalization was "parked, awaiting a client meeting" — false since
  2026-08-25. And it presented `scripts/82` as the standing re-load path; Afaq's
  instruction is that the numbered `8x` scripts are spent one-shot scripts, not
  a contract. Both rewritten.
- **Gotcha — `scripts/82` would have fought this migration.** It upserts
  `item_catalog` from a 5,411-row file and resolves `catalog_item_id` by
  `(item_name, description)`, so it would re-insert every deleted duplicate and
  re-point lines back. After step C's normalized-name index it will hard-fail
  instead, which is the safer outcome. Recorded in `CLAUDE.md`.
- **Gotcha — `normalized_alias` is a GENERATED column.** The payload's
  `item_aliases.jsonl` includes it, so the alias insert returned
  `400: cannot insert a non-DEFAULT value`. Phases 1–4 had already succeeded;
  stripping the key and re-running finished it. **A generated payload is not
  automatically insertable — check it against the DDL it shipped with.**
- **Gotcha — the post-write verification got weakened under pressure, and that
  is the real cost of this session.** Full-table reads became unreliable after
  step A's DDL (`TimeoutError`, then `IncompleteRead`) while `count=exact`
  stayed instant. Rather than solve it, the verification was reduced to counts,
  so the raw-evidence SHA was never re-checked after the write. **Counts are not
  integrity.** Item 2 in Next exists to close this.
- **Gotcha — `supabase_rest._request` does not retry read timeouts.** It catches
  `HTTPError` and `URLError`; a socket read timeout raises `TimeoutError`, which
  is neither, so one slow page aborts a whole run with no retry. Worked around
  locally in `scripts/94`; the shared module still has the gap.
- **Afaq's correction, and it was right: the failing work was redundant.** Time
  was burned re-reading 11,746 live rows to re-prove a preflight that had already
  passed minutes earlier against the count-verified backup, when only DDL had run
  in between. Every operation was idempotent and fully specified by files on
  disk. Removing the read made the script both simpler and reliable.
  **Before hardening a failing step, ask whether it needs to run at all.**

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
