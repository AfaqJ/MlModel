# STATE — where this project is right now

Updated every session. Last 5 sessions only; anything older that still matters
lives in `DECISIONS.md`.

## Now

**The Analítica dashboard was audited figure by figure and three defects were
fixed and merged.** `feature/dashboard` is now `2b6c45d`, pushed. Branch
`fix/audit-2026-09-03` holds the three commits.

Every displayed number was recomputed from `backups/supabase_20260903T054820Z`
and matched against a screenshot of the live app **before** any finding was
written — record counts, both fiscal components with percentages, the net
position, the anomaly count and the concentration triple all reproduced exactly
(→ `EVIDENCE_RULES.md` §12). What that established:

- **The purchases-vs-sales chart was stacked**, so the upper band plotted
  ventas + compras under the Purchases label. October 2025 drew 1,194,984,855
  where purchases were 578,067,481 — **overstated 2.07x**. Fixed (`fee5aec`).
  The doc comment above it claimed the chart was honest; that is now
  `EVIDENCE_RULES.md` §11.
- **Anomaly detection pooled COMPRAS and VENTAS into one z-score** (→ D-049).
  On the default window the flags move from 5 purchases and 9 sales to **24 and
  1**. Fixed (`59c4cb1`), covered by `scripts/check-anomaly-direction.ts` in the
  frontend, which was **run against the pre-fix code and confirmed to fail**.
- **The Ítems tab showed a model suggestion on settled rows** (→ D-050): 1,574
  of 4,002 products had no pending line and still carried a guess, 148 of them
  contradicting the confirmed category. Column removed at Afaq's instruction,
  reversing ledger decision B2, which is marked superseded in the same change
  (`1dad390`).

`tsc` clean, lint clean apart from one pre-existing warning.

**Nothing was verified on screen.** `.env.local` still holds 11-character
redacted placeholders for the Supabase URL and anon key, and `/dashboard`
redirects without a session, so no authenticated page can be reached locally.
The chart fix is proven arithmetically only.

**Ten findings were left as decisions rather than fixes**, written in plain
language for Afaq and his colleague at
`../milk-company/docs/OPEN_QUESTIONS_2026_09_03.md`, with the measurements in
`AUDIT_2026_09_03.md` beside it. Note `docs/` is gitignored in that repo by
Afaq's deliberate 2026-08-27 decision — those are working notes, on disk only.

Live `mlmodel-00014-lrp` on Cloud Run is unchanged. Supabase untouched this
session — no writes, no backup taken, no model work.

## Next

1. **Answer the credit-note question.** 103 invoices of `document_type = '61'`,
   CLP 87,885,532, all stored **positive**, so every dashboard total counts a
   purchase and its cancellation as two purchases. The `Referencia` block that
   says which invoice a credit note cancels **was never loaded into the
   database**, so netting them correctly needs a re-read of the raw XML.
   Options are written up in `OPEN_QUESTIONS_2026_09_03.md` §1.
2. **Ask the client about `document_type = '43'`** — 29 liquidación facturas,
   CLP 292,085,987, all Feria Ganaderos Osorno. If the underlying sale is
   already present as a type 33, these double-count. No code can settle it.
3. **Ask Salman why the Risk tab was disabled.** It arrived already commented
   out in `7d9ae21` (2026-08-07) with no recorded reason and has never been
   live. Now that D-049 is applied, Overview says "36 critical anomalies need
   attention" with nowhere to click.
4. **Decide the IVA split** (`OPEN_QUESTIONS` §3). The Tax Breakdown card adds
   IVA crédito (CLP 909,459,709) to IVA débito (CLP 1,002,431,942) under one
   label. Needs the accountant colleague, not a code change.
5. **Press Done on one line in the dashboard.** Unchanged from last session and
   still the only unproven link in D-048. Ten seconds.
6. **Accept the client's July–August 2026 categorised data.** Still the
   highest-value item on the project and still costs one email. See
   `docs/CLIENT_CONVENTIONS.md` §9.7.
7. **Write the two lists Cristian asked for** — construction contractors (§9.4)
   and bale-making lines (§9.5). Neither is written.
8. **`ADM-3.1` has zero training rows.** Before any retrain it must be marked
   rule-assigned and untrainable the way D-028's six are, or the trainer trips
   the "fewer than 2 examples must fail loudly" limit.
9. **Honorarios and Remuneraciones have never been audited** — keyword probes,
   not audited sets (`CLIENT_CONVENTIONS.md` §10).
10. **Frontend, still open:** horizontal scrolling on the KPI tiles (asked for,
    wraps instead); the Geografía Pareto panel measures geography rather than
    risk; keyset pagination on the catalog is deferred — **search must move
    server-side in the same change or it silently starts matching only loaded
    pages.**
11. **Confirm how production deploys.** `STATE` records the live deploy as a CLI
    `vercel --prod` with no git metadata. If that is still true, merging to
    `feature/dashboard` updates the preview only — **including the three fixes
    merged this session.**

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

### 2026-09-03 — dashboard figure audit; three defects fixed and merged

- **Every figure on Analítica was recomputed and matched to the live screenshot
  before any finding was reported** (→ `EVIDENCE_RULES.md` §12). It also
  surfaced that the default view **excludes 1,003 of 5,195 invoices** with no
  denominator anywhere on screen — a fact no code read would have produced.
- **Three defects fixed and merged** into `feature/dashboard` (`2b6c45d`): the
  stacked chart, the pooled z-score (→ D-049) and the model suggestion on
  settled rows (→ D-050).
- **Ten further findings were logged as decisions, not fixes**, in plain
  language at `../milk-company/docs/OPEN_QUESTIONS_2026_09_03.md`. The largest
  is credit notes: **CLP 87,885,532 added instead of subtracted**, unfixable
  without re-reading the `Referencia` block from raw XML.
- **Gotcha — a doc comment asserted the opposite of what the code rendered.**
  "never a dual axis, so the visual comparison stays honest" sat directly above
  two areas sharing a `stackId`. True about the axis, silent about the
  stacking, and it is *why* the bug survived three passes — reviewers reached a
  reassuring sentence and stopped. → `EVIDENCE_RULES.md` §11.
- **Gotcha — every static check was green the whole time.** `tsc`, ESLint,
  `npm run build` and translation parity cannot see what a chart draws or
  whether a z-score used the right denominator. Both defects were found by
  recomputing against real data, and neither would ever have been found by
  reading more code.
- **Gotcha — a regression test that has never failed has never been tested.**
  `check-anomaly-direction.ts` was run against the pre-fix file (copy aside,
  `git checkout`, run, restore) and confirmed to fail before being trusted.
  Under a minute, and it converts "passes" into "has teeth".
- **Gotcha — provenance changed the recommendation three times out of three.**
  `git log -S`/`-G` showed the suggestion column was added by Afaq's own
  approved decision B2 days earlier (so removing it is a reversal he had to be
  told about); the Risk tab shipped disabled in its first commit and has never
  been live, reason unrecorded; and the "trend regression" subtitle was never
  accurate, so "we removed it" was the wrong story. **`-S` misses a
  comment-out** — the string count does not change — so `-G` is the one that
  finds disabled code.
- **Afaq's correction, and it was right:** `docs/` being gitignored in the
  frontend was raised as a risk. It is deliberate — those are his working
  notes, not something to ship. Do not re-litigate a decision that is already
  recorded in a commit message (`765e355`).
- **Decided:** D-049 (score against the population the value came from), D-050
  (a settled line never shows the model's suggestion; reverses frontend B2).


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
