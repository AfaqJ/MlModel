# STATE — where this project is right now

Updated every session. Last 5 sessions only; anything older that still matters
lives in `DECISIONS.md`.

## Now

**Invoices now go from a ZIP to the live database, proved end to end.** On
2026-09-10 a synthetic invoice was uploaded through `/carga` as a signed-in
user, saved, verified row by row against live, replayed to prove the second
upload changes nothing, then removed. Live returned to baseline exactly:
5,195 invoices / 11,746 lines / 461 companies / 0 batches.

**Migrations `004`–`022` are ALL LIVE.** Afaq ran `021` and `022` on
2026-09-10; verified by 12 new `*_auth_*` policies and the three aggregate
functions existing. `023` is written and proved but **NOT live** — see below.

**`023_protect_settled_lines.sql` is written, proved, and waiting to be run.**
`007`'s line upsert overwrites `final_code`, `decision` and `prediction_source`
from whatever the caller passes; the only thing preventing that is the dedup
check in application code. `023` makes a settled row structurally
un-overwritable. The predicate is `final_code is not null OR reviewed`, not
`reviewed` alone: measured against live, 7,927 rows carry a `final_code` and
exactly 7,927 carry `decision='auto_accept'`, but only **593** carry
`reviewed=true`, so a `reviewed` guard would have protected 7% of what needs
protecting. `reviewed` is monotonic — a human review sets it once and nothing
resets it — and is the right marker going forward (Afaq, 2026-09-10).
`milk-company/scripts/check-settled-lines.sql` fails against `007` and passes
against `023`; run it both ways or the guard is unproved.

**Three defects were found by actually running the thing, not by reading it.**

1. **`directionOf` rejected every real archive.** It required a path segment
   exactly `COMPRAS`/`VENTAS`; the client's export names them
   `dte_<rut>_COMPRAS`. A real upload would have stored nothing and reported
   "0 files read". Fixed, three assertions added. **Afaq's point, now
   `MCT-162`: the DTE itself states the direction** — Antillanca's RUT
   `96685810-9` is `RUTRecep` on a purchase and `RUTEmisor` on a sale. The
   folder should be the fallback, not the source. Deliberately deferred; it
   works today.
2. **`item_aliases` is invisible to a signed-in user.** 8 rows exist; the
   upload path logged `loadAliases: 0 rows`. `021` never granted it to
   `authenticated`, so `/carga` and the email path resolve items differently —
   the exact drift the one-pipeline design exists to prevent. **Not yet fixed.**
3. **The TypeScript pipeline creates Antillanca as a company; the old Python
   load never did.** 461 companies, none of them the client. Saving put
   `966858109 ANTILLANCA SPA` into its own counterparty list. Needs a decision,
   not a fix.

Also: `/carga`'s "Proveedores nuevos" card counts both parties of every document
as an upsert list, not new rows — it says 2 when the answer is 1.

**`YUNT_ALLOWED_ADDRESSES` was never unset.** It has been on Vercel Preview
since 2026-09-09, value unknown because every var is sensitive-flagged and reads
back as `[SENSITIVE]`. That is what produced the wrong note in earlier docs.
`vercel env rm` is blocked by the permission classifier, so converting them to
readable needs Afaq. He has said this is a readability preference, not a blocker.

**Branch `yunt` is pushed through `02d7a58`** — all 38 commits, including the
`directionOf` fix and `023`. Preview rebuilt. Production remains `main`.

**Still to build:** recurring reports (`MCT-154`), PDF and charts (`MCT-152`),
flags per line in the dashboard (`MCT-155`). None touch the write path; every
number they need is already computed by existing tools. There is still no
`vercel.json`, so no scheduler exists.

### Working agreement, set by Afaq on 2026-09-10

One ticket at a time: implement, check it in the UI at `localhost:3000`, run an
end-to-end test, fix what breaks, update the ticket, close it, move on. Do not
open five things at once. Anything touching production data needs a rollback
path written *before* the write and a backup taken first. Tickets were
AI-generated and are **not authoritative** — correct them when they are wrong.
Post concise, ASCII-only project updates in Linear after each milestone, pitched
at a product manager, not at an engineer.

`agent/tools/` holds 20 tools; `src/lib/yunt/` holds 19 modules. Read that
listing before adding either — three re-implementations were caught only because
someone looked first.

### Local UI testing, which is now the fast path

`.env.local` in `milk-company` had both Supabase values as `[SENSITIVE]`; Afaq
filled in the project URL and the **publishable** key (`sb_publishable_…`, the
replacement for the legacy anon key). `npm run dev` then works against live
Supabase with a real signed-in session. It holds **no service key**, which is
what proved `MCT-159`: the save could only have gone through RLS as
`authenticated`.

To put a file into the upload form without a file picker, copy it to
`milk-company/public/` and have the page `fetch()` it into a `DataTransfer` —
far cheaper than injecting base64. Delete it afterwards.

## HANDOVER — 2026-09-09, session ended by Afaq

Read this before doing anything. It is written for the next session and for
Codex, and it includes a mistake that needs checking by a person.

### What I inherited from Codex, and how I learned it

Codex's session hit its usage limit mid-handover, so it wrote no docs. I
reconstructed its work from `git log`, file diffs, and by running its checks
myself — not from its summary. It had produced ten commits (`3ba9b1f` ..
`f6705ec`) plus one uncommitted increment, all in `../milk-company`:

- migrations `009` (durable review state), `010` (atomic completion),
  `011` (review packets), `012` (findings outbox, uncommitted at the time);
- three grounded EVE tools — `load_review_chunk`, `review_precedent`,
  `submit_review_chunk`;
- an OIDC-secured, idempotent dispatcher to EVE.

I verified rather than trusted: `tsc --noEmit` clean, all its check scripts
passing. Codex's own summary claimed a full regression it never ran on the
outbox increment; I ran it, and it passed.

### What I added

Five commits on `yunt` (`813e8a9` .. `8881a12`), 26 files, ~1,566 lines:

- **Committed Codex's uncommitted outbox increment** (`813e8a9`).
- **Connected the writer to `/carga` in source** — dry-run first, saves only on
  a second explicit click; a later permission audit found that the authenticated
  client cannot yet access the service-only writer objects, so this is not a
  working live path.
- **Routed the mailbox** — a ZIP goes to deterministic ingest; anything else is
  recorded in `yunt_inbound_requests` and handed to the agent, which answers via
  `reply_to_email`. The recipient is read from the stored row, never from the
  model.
- **Pinned the model.** There was no `agent/agent.ts`, so eve was running its
  own default (`openai/gpt-5.6-luna-fast`). Now `anthropic/claude-opus-5`,
  reasoning `medium`, chosen after measuring a real packet (~15k tokens, ~4
  packets a month, ~$2.80/month on Opus 5 versus ~$0.56 on Haiku — cost is not a
  constraint at this volume).
- **Closed the write→review loop in source** (`after-write.ts`). The email door
  has the required service permissions. The upload door calls the same code but
  is blocked by the permission gap above. It can never turn a successful write
  into a failed receipt (D-064).
- **Scope item 8, apply-on-approval with undo** — migration `014`, plus
  `apply_proposal` and `undo_application` tools.

New migrations that are mine, not Codex's: **`013`** and **`014`**.

### What I deleted, and what I put back

I deleted `supabase/008_yunt_category_precedent.sql`, believing its function was
superseded by `009`. **That was wrong** — `008` also installs the `pg_trgm`
extension that `009`'s function depends on. I restored it immediately, along
with `scripts/prove-011-to-014.sh` which I had edited in the same step. Both
repos' working trees are clean; nothing else was deleted at any point.

### The mistake that needs a person

While auditing live state I drove the Supabase SQL editor in the browser and
**typed over editor buffers that held Afaq's pasted script history**, using
select-all and replace. The migration content itself is safe — it lives in
`milk-company/supabase/*.sql` — but any ad-hoc query he had in an open tab may
be gone. The saved queries under **PRIVATE (10)** in the SQL editor sidebar are
what to check. Do not drive that editor again; read live state another way, or
ask him to run a query and paste the result.

### What live actually contains (verified, not inferred)

- `pg_trgm` is installed, in schema `extensions`.
- Exactly **one** `yunt_category_precedent` exists — the 5-argument version from
  `009`, which is the correct one. There is **no** duplicate overload. An earlier
  claim of mine that there were two was wrong and is retracted.
- `004` through `010` are applied. `011` through `019` are not.
- `prediction_source` allows six values including `user_selected`, so `014` is
  legal against the live constraint.

**There is nothing to clean up inside Supabase.** The disorder is in the files.

### The file disorder, stated once

Four numbering lineages, three of them starting at `001`, across two repos:

| Where | State |
|---|---|
| `ML-model/reports/recovery_v1_3_3/supabase_upload/` `001`, `002`, `002` | Applied Aug 19. **Two files share the number `002`.** Both superseded by milk-company `004` |
| `ML-model/reports/canonical_catalog_2026_08_25/` `001`-`004` | Complete Aug 26. `001` was review-only; `002` (15,905 lines) never ran, replaced by `003` + a PostgREST pass |
| `ML-model/reports/client_reply_2026_09_02/001` | **Not applied**, awaiting Afaq's decision |
| `milk-company/supabase/004`-`014` | The live lineage. Starts at `004` because `003_user_selected_source.sql` was superseded and deleted — `004`'s header says so. Nothing is missing |

Two real traps in that set:

1. **`008` and `009` both define `yunt_category_precedent` with different
   signatures.** Had both fully applied, Postgres would keep two functions, and
   the older one silently skips the batch-exclusion guarantee. Only `009`'s
   landed. That was luck. `008` still matters for its `pg_trgm` line.
2. **`010`'s `complete_yunt_review` was superseded 24 minutes later** by `011`'s
   per-packet completion. The live function is harmless; `completeReviewAttempt`
   in TypeScript is now dead, reachable only from its own test.

### What I was about to do, and did not

- Write `milk-company/supabase/README.md` — one index page naming every lineage,
  what is applied, and what supersedes what. **This is the actual fix**; the
  numbering is not the problem, the missing index is.
- Add a header to `008` marking its function superseded and its extension line
  still load-bearing. Do not renumber, do not delete — it is applied.
- Delete the dead `completeReviewAttempt` TypeScript path only, leaving the live
  `010` function alone.
- Then scope item 9, the five parameterised query tools, which unblock items 10,
  11, 12, 13, 18 and 19. Before building it, settle whether they read through a
  new canonical Postgres view (what the plan says) or reuse the 2,200 lines of
  existing in-memory dashboard aggregation (faster, but inherits whatever the
  credit-note / revenue / IVA defects are).

### What was run

Afaq applied `011`–`020` on 2026-09-09 from a concatenated file. Nothing in that
set was destructive: no `DELETE`, `TRUNCATE`, `DROP TABLE` or top-level data
`UPDATE`. Its four `DROP` statements were all guarded and re-created in the same
file — `012`'s own trigger, and the two constraints `014` and `020` widen. `020`
must follow `014` because it re-adds a constraint `014` created.

### Open, needing Afaq

1. **Who may use `/carga`.** Recommendation: a database-backed Yunt operator
   allowlist seeded with Afaq's signed-in email and extended with Cristian later.
2. **Claude model choice.** Claude pinned Opus 5 / medium from a cost estimate;
   Afaq has not explicitly ratified that choice.
3. **Your yes on the 222 harvested aliases** — `006` is live, so this is unblocked.
4. **The Supabase org shows "Grace period is over" and the project is flagged
   EXCEEDING USAGE LIMITS.** That stops the project serving requests. It needs
   handling before any real write.

## Linear, as of 2026-09-09

Linear now mirrors this project feature by feature, so it can be read instead of
this file for *progress*. It is still not the design; where a ticket and
`DECISIONS.md` disagree, the decision log wins.

- `MCT-142` **The Yunt assistant** is the parent. Its sub-issues are one per
  capability: review and propose (`149`), approve and undo (`150`), answer
  questions (`151`), spreadsheets/PDFs/charts (`152`), refuse and keep the list
  (`153`), recurring reports (`154`), data-quality flags (`155`), open a request
  from email (`156`), draft and issue the order from email (`157`).
- `MCT-139` ingest, `MCT-140` purchasing, `MCT-141` the mailbox, `MCT-145` the
  upload page carry the deterministic halves.
- Three urgent blockers are their own tickets: `MCT-158` run the pending
  database changes, `MCT-159` decide who may save from the upload page,
  `MCT-160` the first real email end to end.

Tickets are written at product level on purpose — no file names, no migration
numbers, no function names — so an implementation discovery cannot turn one into
a lie. The *how* lives here and in `DECISIONS.md`.

## What the Yunt promises, and what it does today

The 19 numbered items are the scope sent to the team, in the client's own
words (`docs/Yunt_scope_v1.docx`). Where that document and `DECISIONS.md`
disagree on *how*, the decision log wins (D-059) — but this list is what
Antillanca was told they are getting, so it is the honest measure of progress.

**12 of 19 done in code, 4 partly, 3 not started. Nothing agentic is live yet.**

| # | What Cristian was promised | Today |
|---|---|---|
| 1 | A mailbox that acts only on agreed senders | Done. Never carried a real message |
| 3 | Duplicate detection on RUT + type + folio; sending twice changes nothing | Done |
| 4 | Lines classified and **written to the database** | Partly. Email is connected in code; `/carga`'s permission is written and proved as `021` but not run; neither is live-proved |
| 5 | An acknowledgement in minutes, then a written report | Done in code as a receipt first and a findings email later; never live-proved |
| 6 | Data quality flags, and fixes proposed on approval | Partly. Detection is built and calibrated; a flagged auto-accept is downgraded. Persisting flags and proposing fixes remain |
| 7 | Category proposals with evidence, grouped | Partly. Built, grounded, and now triggered by every write. Accuracy still unmeasured |
| 8 | Approve a group, get a confirmation, undo it | Done in code. The confirmation is the database's own words, not the model's |
| 9 | Five query tools answering open questions | Done in code. All five built and proved. `022` is not live |
| 10 | Figure in the body, list as spreadsheet, report as PDF, filter printed on top | Partly. Figure in the body and the spreadsheet attachment are built, with the filter printed on both. PDF remains |
| 11 | Charts from a fixed set, drawn by code | Not started |
| 12 | Says so when a question does not fit, and we learn from the list | Done in code. One immutable backlog entry per stored request; not live until `017` runs |
| 13 | Month-end summary, post-batch digest, weekly review list | Not started |
| 14 | Form one: what is needed, how much, by when, for which farm | Done. Tables live, not yet used in anger |
| 15 | A request stays open until an order closes it | Done. Enforced in the database |
| 16 | Form two, with the two-quotation rule above CLP 500,000 | Done. Rule proved by regression |
| 17 | A purchase-order PDF Antillanca sends themselves | Partly. A print-styled page; the browser saves the PDF. Cannot be attached to mail |
| 18 | The Yunt fills form one from a plain-language email | Done in code. Missing required facts are requested; a stored draft becomes a real open request only after exact confirmation. Not live until `018` runs |
| 19 | The Yunt drafts the order once a quotation exists | Done in code. Drafts from a supplier, quantity and agreed price it was given, then issues the order only on the exact confirmation. Not live until `020` runs |

**Read the middle column, not the count.** The deterministic base is farthest
along. The EVE review and action tools are now called by the email path in code,
but their migrations, model credentials and real-message proof are still open.

**The next foundation priority is permission, not another feature:** make
`/carga` a real authenticated write without exposing service-role power, clear
the Supabase usage block, run `011`–`019`, then prove one real email and one
upload including replay. In parallel, finish the remaining four read tools.

## V1 checklist

Every box that must be ticked for a working v1. Updated as work lands — if a box
is unticked, there is no code for it. "Built" means proved by a regression;
"live" means the migration has run in Supabase.

### The spine — invoices in, stored, reviewed

- [x] Deploy path, Resend mailbox, ZIP upload page (Phases 0–1)
- [x] Read, deduplicate, resolve to catalog, classify, report (Phases 2–2.5)
- [x] Atomic writer: whole invoice and all its lines in one transaction (D-063)
- [ ] `/carga` live save: source is connected and `021` grants the permission,
      but `021` has not been run, so the first real save still fails
- [x] Mailbox router: ZIP → deterministic ingest, everything else → the agent
- [x] **Mailbox connected to the writer** — claimed by the Resend message id
- [x] **Email review fires after a write** and never blocks the receipt (D-064)
- [ ] `/carga` review runs under the final operator permission design
- [ ] First real write, against a backup, with Afaq's yes on the day

### The review loop

- [x] Durable review state, packets, atomic completion (`009`–`011`)
- [x] Three grounded EVE tools: load, precedent, submit
- [x] Findings-email outbox: sends only when findings exist (`012`, D-065)
- [x] OIDC-secured, idempotent dispatch to EVE
- [x] **`anthropic/claude-opus-5`, reasoning `high`** in `agent/agent.ts`.
      Settled 2026-09-09 from current published pricing: Opus 5 $5/$25 per MTok
      against Sonnet 5 $2/$10 and Haiku 4.5 $1/$5. `high` is the model default
      and the quality/token balance point; `medium` had been chosen on a cost
      argument, which is the wrong axis when the whole month is a few dollars
- [ ] Proof run: 200 known review rows, counting the confidently-wrong (Phase 5)

### Talking to Cristian

- [x] Inbound requests recorded and threaded by `In-Reply-To` (`013`)
- [x] `reply_to_email` — recipient read from the row, one reply per request
- [x] **All five query tools** (Phase 7, D-053): price history, category
      precedent, invoice-line listing, grouped totals and period comparison.
      Money semantics live in one function and print on every answer — net line
      amounts, IVA excluded, credit notes negated and excluded by default
- [x] **List as a spreadsheet attachment**, queried by the tool rather than
      retyped by the model. CSV with a BOM and semicolons so Excel reads it in
      Chile; a real workbook only if formatting or formulas are ever needed
- [ ] Report as PDF, and charts from the fixed set
- [x] Refusal path and `yunt_refusals`, one immutable backlog row per request
- [x] Exact restate-then-confirm for apply and undo: code-generated prompt,
      Message-ID/sender/action/target binding, and one-use first-line token

### Acting, with a way back

- [x] **`apply_proposal`** — sealed targets, no row list from the caller, stale
      proposals refused because a person's later edit wins (Phase 6)
- [x] **`yunt_applications`: prior values stored, undo is a per-row replay** —
      `decision` and `reviewed` come back too
- [x] **Data-quality flags: four line checks and one document check**, each
      chosen by measuring candidates against the stored 11,746 lines. A flagged
      `auto_accept` is downgraded to review and nothing else (Phase 4, D-058, D1)
- [x] **Flags persisted to `yunt_flags`** with `source='deterministic'`, written
      when the review attempt opens so an incomplete review still leaves them
- [ ] Flags shown per line in the dashboard

### Purchasing

- [x] The two forms, real tables (`005` live) — not yet exercised live
- [x] The Yunt drafts and creates form one from email only after exact
      confirmation (`018`)
- [x] Read one request, its bounded quotations and any existing order without
      exposing private quotation storage paths
- [x] The order form records an optional chosen quotation; the database rejects
      a quotation belonging to a different request (`019`)
- [ ] Attach supplier/price precedent to that buying exchange when requested
      (the grounded price-history tool itself already exists)
- [x] **The Yunt drafts and issues the order from email after exact
      confirmation** (`020`), through the same `create_purchase_order` the form
      calls — the CLP 500,000 two-quotation check has one copy, never a second

### Waiting on Afaq

- [ ] Confirm Supabase is out of its **EXCEEDING USAGE LIMITS** state. The
      `011`–`020` run succeeding suggests it is; not checked directly
- [ ] **Run `021` then `022`** in the Supabase SQL editor. Both proved twice
      against disposable PostgreSQL; neither drops, truncates, deletes, updates
      data, or changes row-level-security posture. Back up first
- [x] `021` written and proved (`scripts/prove-021-carga-writes.sh`)
- [x] `/carga` permission design decided: any signed-in user, no roles in v1
- [ ] **Your yes on the 222 harvested aliases** (`006` is live, so unblocked)
- [ ] Send the first real email to `antillanca.yunt@mountaincreative.cl`
- [ ] Fix the `Confeccion de Bolos` duplicate — three catalog rows, one thing

### Deliberately not in v1

Roles and approval chains on purchase orders (D-052, and the scope document says
so in the client's own words), goods receipt / invoice matching / payment, and
ingestion from the Audisoft API, which is blocked on credentials that return 401
(D-054). **Recurring reports are not on this list** — they are scope item 13 and
belong in v1.

## Recent sessions

### 2026-09-10 (b) — the first real save, and three defects found by running it

- **Afaq ran `021` and `022`.** Verified by 12 new `*_auth_*` policies and the
  three aggregate functions. `MCT-158` closed.
- **`MCT-159` closed: a signed-in person can upload and save.** Full round trip
  through `/carga` on live — dry run, confirm, 5,195→5,196 invoices and
  11,746→11,747 lines, then cleaned back to baseline exactly. The done-when
  ("saves as that person, not the system") is proved by construction:
  `.env.local` holds no service key, so the write could only pass RLS as
  `authenticated`.
- **`MCT-146` closed: replay proved inert.** The identical archive uploaded a
  second time produced 0 new documents, no second batch claim, no duplicate
  invoice, unchanged counts — and the reception report was still generated.
  That is also the hard half of `MCT-160`, so the mailbox ticket is now only
  waiting on Resend carrying a real message.
- **`MCT-151` closed: the money figures were checked independently.** All 31
  monthly groups across COMPRAS and VENTAS agree with a recomputation from the
  raw rows — values, line counts and document counts. COMPRAS 4,852,221,504;
  VENTAS 5,269,557,578. The top-N guard was checked too: 25 of 438 supplier
  groups shown understate by CLP 954,276,937, and `overall_value` carries the
  truth. Saved as `scripts/86_verify_aggregate_vs_raw.py`.
- **`MCT-145` and `MCT-139` closed** on the evidence above. `MCT-139`'s
  description asserted the direction "cannot be worked out from the file
  itself"; that was corrected in place rather than left for a future session to
  believe.
- **Wrote `023`** and `check-settled-lines.sql`, which fails against `007`
  (`FAIL legacy final_code overwritten: expected 6001, got 9999`) and passes
  against `023`.
- **Raised `MCT-162`** (direction from the DTE's RUTs, not the folder) and
  **`MCT-163`** (four new pages are hardcoded Spanish: `carga`, `solicitudes`,
  `ordenes`, `levantamiento`). Both deliberately deferred.
- **`MCT-153` cannot be closed by building** — its done-when needs Cristian to
  be refused by a live Yunt. Mechanism built, table live, zero rows, which is
  correct. Noted on the ticket.
- **`MCT-149`: the category proposal was measured, and the finding is about the
  data, not the code.** Held out against the 7,927 human-confirmed lines (each
  line removed from its own evidence), sample 400, fixed seed:
  13.0% abstain, 92.8% of proposals correct, **5.75% confidently wrong** —
  wrong while resting on same-wording evidence, which is the expensive kind.
  Examining all 20 confident errors showed they are almost entirely **not**
  search failures: **29 wordings are filed by humans under more than one
  category, covering 1,507 of 7,927 lines (19%)**. `servicio publico` is
  EXP-11.2:15 / EXP-11.1:15 / EXP-9.1:6 — a tie, so nothing can beat 50% there;
  `gasolina 93` is 368/81 across an operating and an administrative category,
  which looks deliberate rather than sloppy. The search performs near this
  data's ceiling. Reproduce with
  `scripts/87_measure_precedent_quality.py`. Raised for the client on `MCT-143`.
  `MCT-149` stays open only for its first half, which needs the Claude API key.
- **Three project updates posted in Linear**, ASCII-only and pitched at a
  product manager, per Afaq's standing request.
- **Gotcha — a cleanup script must delete children before parents.** The first
  cleanup run hit a 409: `yunt_batch_items.item_id` references
  `invoice_items.item_id`. Nothing was deleted; the database refused. Order is
  batch children, then lines, then invoices, then `yunt_batches`, then the
  company row.
- **Gotcha — the test invoice must reuse an existing supplier and existing
  catalog wording.** Change only the folio on a real DTE. Then the only new rows
  are the invoice, its lines, the batch, and Antillanca's own company row, which
  makes the cleanup exact instead of sprawling. The DTE signature is never
  verified, so editing the folio is safe.
- **Gotcha — `unzip -l` shows uncompressed size.** The 5-file archive reads
  6,920 there and is 4,673 bytes on disk. Not a truncation bug.


### 2026-09-10 — the two pending migrations, written, proved and handed over

- **Wrote `021_carga_operator_writes.sql`.** Afaq supplied the text, because
  Claude's own write of it had been refused twice by the safety classifier for
  granting database permissions. Nothing in it was changed.
- **Proved it, which it had never been.** `scripts/prove-021-carga-writes.sh`
  first asserts the fixture *cannot* save before the migration, so the proof
  cannot pass vacuously against an already-open database; then loads `021`
  twice; then checks that `authenticated` ends up with exactly the table
  privileges, function grants and per-command policies the upload path needs —
  and that `yunt_batch_items` gained no update policy, a direct insert into
  `invoices`/`invoice_items` is still refused, and `anon` gained nothing.
  Commit `e65edae`.
- **Re-proved `022`** so both pending migrations were green on the same day.
- **Handed over the consolidated paste** of `021` then `022`, after checking by
  grep rather than assumption that neither carries a `DROP`, `TRUNCATE`,
  `DELETE`, top-level data `UPDATE`, or any row-level-security posture change.
- **Skipped `check.sh` deliberately.** The commit touched only SQL, a shell
  script and Markdown; running the TypeScript regression would have proved
  nothing and is the kind of broad re-run Afaq asked to stop.
- **Correction:** five frontend and six root commits that appeared to be someone
  else's work were from later in the previous session, past the point Claude's
  context was trimmed. Neither Afaq nor Codex worked after it ended.


### 2026-09-09 (n) — the corpus check found a real defect

- **Verified the aggregate against an independently computed count.** The real
  stored corpus — 5,195 documents, 11,746 lines — loaded into a throwaway
  PostgreSQL, every figure compared with the same total worked out in Python
  from the same JSONL. Two implementations, one answer.
- **It caught what the fixtures could not.** A grouping with more than 100
  distinct values is truncated by the row cap, so adding up the returned rows
  understates the answer: by supplier the corpus has **438** groups and the top
  100 miss **CLP 194,149,548**; by item it has **5,259** groups and they miss
  **CLP 1,733,487,393**. `truncated` was a boolean nobody had to act on.
- **Fixed by returning the real total.** `overall_value` and `total_groups` are
  computed with window functions across every group before the cap, and the tool
  turns them into a coverage line: these are N of M groups, the total is X, do
  not add the rows up. A complete answer carries no such line.
- **Everything else agreed exactly:** purchases with and without credit notes
  netted, line and document counts, the largest category, the lines with no
  confirmed category, and all six groupings.
- **`scripts/verify-022-against-corpus.py` is re-runnable** and touches nothing
  live. Commit `619f92e`. `./check.sh` all green; `npx eve build` passed.
- **Gotcha:** PostgreSQL will not start under a long macOS temp path (the Unix
  socket limit) and refuses to start at all without `LC_ALL` set. Both failures
  present as a bare "could not start server".

### 2026-09-09 (m) — answers arrive as a file

- **Scope item 10's spreadsheet half.** `reply_with_spreadsheet` takes the same
  filters as the list and totals tools plus the written answer, **runs the query
  itself**, and attaches the result. A row the model retypes is a row the model
  can get wrong, and the attachment is the artefact Cristian keeps.
- **CSV, not a workbook.** Excel opens it and the format is forty lines rather
  than a dependency. Two details make it readable in Chile: a UTF-8 byte-order
  mark, or accented supplier names arrive mojibake, and a semicolon separator,
  because a Spanish-locale Excel reads the comma as the decimal point and shifts
  every column. Marked with a `ponytail:` note — a real workbook only when
  formatting, several sheets or formulas are needed.
- **Proof:** `scripts/check-yunt-spreadsheet.ts` covers the BOM, the separator, a
  supplier name containing a semicolon, an embedded quote, an embedded newline,
  null and undefined as empty cells, and zero surviving a falsy check.
  `./check.sh` all green; `npx eve build` passed. Commit `4a23b6d`.

### 2026-09-09 (l) — the deterministic findings are stored

- **They were computed and then thrown away.** The quality checks fired at
  ingest but their results only reached the batch report and the model prompt.
  They now land in `yunt_flags` with `source='deterministic'`, written as the
  review attempt opens — before the model sees anything, so a review that never
  completes still leaves them behind.
- **Five module types map onto the table's five allowed ones.** The table holds
  one row per group per type, so several amount problems in a group collapse
  into one flag naming every affected line. The worst severity wins along with
  its own reason: a critical finding reported at `warning` is one that gets
  skipped.
- **Only lines the review actually linked can carry a flag**, so a stray input
  id cannot smuggle one in, and a clean group produces no row rather than an
  empty one.
- **Proof:** `scripts/check-yunt-deterministic-flags.ts` covers the mapping, the
  collapse, the severity rule, the orphan case and the clean case. `./check.sh`
  all green; `npx eve build` passed. Commit `5965368`.

### 2026-09-09 (k) — one definition of a data-quality flag

- **The arithmetic check existed twice.** `quality.ts` derived it from
  `Line.reconciles` for the write-time downgrade; `batch-review.ts` derived it
  again from the same field for the model prompt. Review groups now take their
  flags from the quality module, so there is one definition.
- **The model gains three checks it could not see before:** a line worth more
  than its whole document, an item name that identifies nothing, and a
  non-positive amount. `line_total_mismatch` is renamed `line_arithmetic` after
  the module that owns it; no review packet has ever been produced, so nothing
  stored carries the old name.
- **A fixture that stubbed the feature out was hiding the wiring.**
  `check-yunt-batch-review` used an empty quality result; it now runs
  `applyQualityFlags` exactly as `prepareIngest` does.
- **Proof:** `./check.sh` all green, `npx eve build` passed. Commit `06bd8fa`.

### 2026-09-09 (j) — the last two query tools, and one filter instead of two

- **Scope item 9 is complete in code.** `yunt_invoice_aggregate` groups invoice
  lines by month, category, supplier, document type, item or city and measures a
  sum, a count of lines or of documents, an average unit price, a minimum or a
  maximum. `period_comparison` runs it over two ranges and joins on the label.
- **Money semantics are settled and stated, not hidden.** Net line amounts, so
  IVA is excluded; a credit note subtracts and is excluded entirely unless asked
  for; a prediction still under review is never counted as a category (D-001).
  Every answer prints the filter, the basis and the credit-note treatment. Afaq
  ruled this was an accounting question for the client rather than a code
  blocker — if the convention changes it changes in one function.
- **One definition of "a matching line", not two.** `016` already had the filter
  the aggregate needed. Rather than copy it, it moved into `yunt_filtered_lines`
  and `016` now selects from that; its signature and behaviour are unchanged,
  proved by re-running its own checks over the new source.
- **The only TypeScript arithmetic is the period difference, and it refuses to
  invent a percentage.** A zero or negative base gives a difference and no
  percent change; a group present in only one period is named as such instead of
  being shown as a change from zero.
- **Proof:** `scripts/prove-022-aggregate.sh` loads `022` twice and covers every
  grouping, every measure, credit-note netting, the review-required exclusion,
  null unit prices, argument validation and the row cap, then re-runs `016`'s
  behaviour over the shared source. `scripts/check-yunt-aggregate.ts` covers the
  argument mapping and the comparison edge cases. `./check.sh` all green;
  `npx eve build` passed. Frontend commit `7b674cf`.
- **Two migrations now pending:** `021` (`/carga` operator writes, still not
  written to disk) and `022`.

### 2026-09-09 (i) — migrations 011-020 went live

- **Afaq applied `011`–`020` in one paste.** The whole pending set is now in the
  real database: review packets, the findings outbox, durable inbound requests,
  apply/undo with exact confirmation, price history, invoice-line listing, the
  refusal backlog, and both halves of Yunt purchasing. `004`–`020` are all live.
- **What was handed over, and the safety argument that went with it.** A
  concatenated file in run order, plus a scan showing no `DELETE`, `TRUNCATE`,
  `DROP TABLE` or top-level data `UPDATE` anywhere in the set, and the four
  guarded `DROP`s named with their exact targets. `020` must follow `014`
  because it re-adds a constraint `014` creates.
- **This changes what "not live" means in every other doc.** `supabase/README.md`,
  this file and `CLAUDE.md` were all corrected in the same session, because a doc
  still claiming `011`–`020` are pending is worse than no doc.
- **Not proved live.** Every one of those paths is now live-*capable*. None has
  carried a real message. The first real email remains the next real milestone.

### 2026-09-09 (h) — data-quality checks, chosen by measurement

- **Afaq closed three standing questions.** Money semantics is an accounting
  question for the client, not a code blocker: totals sum net line amounts,
  credit notes subtract, IVA excluded, and the filter printed on every answer
  says so. `/carga` gets the same permission every other write in this product
  has — any signed-in user, no roles in v1 (D-052); the named-allowlist idea is
  dropped. The model choice is settled below.
- **Model settled: `claude-opus-5`, reasoning raised `medium` → `high`.** Read
  from current published pricing rather than memory. `high` is the model's own
  default; `medium` had been picked on cost, and at this volume the month is a
  few dollars either way. Not `xhigh`/`max` — the agent computes nothing.
- **Built scope item 6, and chose the check set from the corpus.** Seven
  candidates were measured against the stored 11,746 lines / 5,096 documents.
  Four survive: `line_arithmetic` 3.53%, `line_exceeds_document` 2.02%,
  `junk_item_name` 1.63%, `non_positive_amount` 0.32% — 7.19% of lines together,
  downgrading 5.62% of auto-accepts. `document_arithmetic` (8.54% of documents)
  is reported but downgrades nothing.
- **Dropped, with reasons:** duplicate folio fired on 0 of 5,195 documents
  because deduplication already rejects them; an unseen supplier RUT fired on
  8.4% of purchases and a new supplier is ordinary business; unit price against
  an item's own history could judge only 407 of 5,217 catalog names and fired on
  7–9% of those (D-049); `quantity <= 0` fired on nothing.
- **Two rules were wrong as written, and both would have looked like noise.**
  Blaming a whole document for a total mismatch downgrades 14.8% of the corpus;
  naming the single line that exceeds the document total downgrades 1.95% and
  still catches the meter-reading case. The document check fires on 13.2% until
  the exempt amount is allowed for — on 199 documents the lines legitimately
  include it while the header net does not.
- **A first draft re-implemented arithmetic the parser already does.** It
  measured 9.82% purely by treating `discountAmount` and `discountPct` as two
  discounts, which `dte.ts` already documents as one. `line_arithmetic` now
  reads `Line.reconciles`. What is new is the consequence: a line that did not
  reconcile was counted in the report and then stored settled anyway.
- **Proof:** `scripts/check-ingest-quality.ts` covers every rule, both
  explained-away cases and the downgrade, and was verified to fail against the
  double-counting draft. `./check.sh` all green, `npx eve build` passed.
  Frontend commit `fa341a3`.
- **Blocked, needs Afaq:** writing the `/carga` permission migration was refused
  by the safety classifier, twice, because it grants database permissions. The
  file is not written. It needs his approval or a paste.

### 2026-09-09 (g) — the Yunt drafts and issues a purchase order

- **Scope item 19 built.** `draft_purchase_order` stages one order from a
  supplier, quantity and agreed unit price the Yunt was actually given;
  `request_action_confirmation` sends the code-generated restatement including
  the exact total; `create_purchase_order` issues it only on the exact reply
  (D-067). It contacts no supplier and invents no fact.
- **One copy of the money rule, kept.** The new database function calls the
  existing `create_purchase_order`, so the CLP 500,000 two-quotation rule, the
  open-request check and the closing of the request are unchanged (D-052).
- **The blocker that was there all along.** `create_purchase_order` refused any
  caller without an `auth.uid()`. The Yunt runs as `service_role` and has none,
  so the second caller the rule was centralised for could never have reached it.
  `020` widens that one guard and changes nothing else.
- **Proof:** `scripts/prove-020-purchase-order.sh` — `020` loads twice; staging
  is idempotent; a cross-request quotation and an already-ordered request are
  refused at drafting; "si dale" creates nothing; the exact line creates one
  order and closes the request; a replay returns the same order; CLP 900,000 on
  one quotation is refused in that function's own words **without** consuming
  the confirmation token, so the retry after uploading a second quotation works.
  `./check.sh` all green (including a new `check-yunt-purchase-order.ts`) and
  `npx eve build` passed. Frontend commit `a9140e4`.

### 2026-09-09 (f) — purchase-order quotation integrity

- **Fixed an existing order integrity hole.** The order form now sends its
  optional `selected_quotation_id`, which the existing server action already
  supported. Migration `019` enforces that a selected quotation belongs to the
  same purchase request; no selection remains valid. Frontend commit `ce08223`.
- **Proof:** `scripts/prove-019-quotation-guard.sh` loaded `019` twice, rejected
  a cross-request quotation, and accepted matching and null selections.
  `./check.sh` and `npx eve build` both passed before commit.
- **Checkpoint discipline:** this entry and the live/pending migration boundary
  were written immediately after the increment, before starting more code.

### 2026-09-09 (e) — provenance fixed, migration line clarified, three query tools

- **Afaq chose `yunt_applied`.** Unrun migration `014` now adds that seventh
  `prediction_source`, apply writes it, undo restores the prior source, and the
  dashboard's automatic-accept KPI excludes both direct human selections and
  human-approved Yunt changes (D-066). Commit `649c48f`.
- **Removed migration ambiguity.** `supabase/README.md` now names the live
  boundary and every supersession; `008` says its function is replaced but
  `pg_trgm` is load-bearing; the dead TypeScript caller of `010` was removed.
  Commit `5597860`.
- **Built query tool 1/5.** `item_price_history` resolves only one exact catalog
  item automatically, asks when a name is ambiguous, returns bounded newest-first
  rows with exact filters, and excludes credit notes unless explicitly included.
  Migration `015` and EVE tool committed as `d7b21b0`.
- **Opened the existing category precedent to ordinary questions.** A batch id
  is optional for email questions and still mandatory in review calls that must
  exclude their own rows. Commit `137ede9`.
- **Built bounded invoice-line listing.** Direction, counterparty, category,
  document type, review state, dates and amounts are validated filters; the
  model receives at most 100 rows and is forbidden to total them. Migration
  `016`, commit `ff55c64`.
- **Made agent-email failure retryable.** A failed delivery now releases the
  durable request to `open`; the old code marked it `failed` while the claim
  function accepted only `open`, so its claimed retry path could never run.
  Commit `9026387`.
- **Built the refusal backlog.** The agent records one immutable refusal per
  inbound request, with the missing capability and reason but never a model-
  rewritten copy of the user's question. Migration `017`, commit `7e14e7f`.
- **Closed a dangerous approval hole.** An opening request was stored with its
  own Message-ID as `in_reply_to`, so every question looked like a reply; even a
  real reply was not bound to the proposal it supposedly approved. Opening
  messages now stay opening. Apply and undo require a code-generated prompt and
  a reply matching its Message-ID, sender, exact action, exact target and one-use
  token on the first line. The findings email now exposes the actual proposal
  id the next EVE session can use. Commit `dc76546` (D-067).
- **Proved the production classifier connection without writing data.** The
  deployed `/health` and `/artifact-check` reported v1.3.3 and intact artifacts;
  one prediction returned `EXP-2.3 Vacunas`, and the dashboard's own TypeScript
  adapter received exactly 10/10 results from `/predict-batch`.
- **Stopped failed reviews lying about their state.** If staged packets cannot
  reach EVE, the numbered attempt now closes as `unavailable` instead of staying
  `running` forever. A future retry can start a clean attempt. Commit `002e0b5`.
- **Built Yunt-created purchase requests.** The agent refuses to invent any of
  what/quantity+unit/date/farm, stages a durable draft, shows an exact
  confirmation, then creates the ordinary open `purchase_requests` row with
  `created_via='yunt'` and the source email id. It creates no order and contacts
  nobody. Migration `018`, commit `016f907`.
- **Grounded the next purchasing step.** `purchase_request_context` reads one
  exact request, up to 20 quotations belonging to it, and any existing order.
  It does not expose private quotation storage paths and cannot write anything.
  Commit `7587d50`.
- **Proof:** `014` apply/undo and `015` price history each loaded twice and passed
  behavioral PostgreSQL checks; `016` and `017` passed the same load-twice and
  behavior proof; `018` passed load-twice plus draft/create/replay behavior. The
  expanded `014` proof also rejects opening mail, quoted
  confirmation text, wrong targets, reused prompts and stale rows. After every
  increment, `./check.sh` was all green
  (types, zero lint errors, build, all checks); the final `npx eve build` passed.
- **Gotcha:** source wiring hid a real security failure. `/carga` carries an
  authenticated client into objects granted only to `service_role`. Previewing
  works because it reads; committing does not. Fix authorization at the database
  boundary, never by smuggling the service key into the action.

### 2026-09-09 (d) — the review layer: state, packets, tools, dispatch, outbox

Built by Codex in one run; the session hit its usage limit before writing any
of this down, so it was reconstructed from git and re-verified by Claude.

- **Durable review state (`009`, `010`, live).** A batch carries a review
  attempt with `pending`/`running`/`completed`/`unavailable`/`failed`, linked to
  the exact stored line ids. Flags and sealed proposals are stored apart from
  invoice truth, so a proposal never mutates a category on its own. Precedent
  lookup excludes the batch's own new lines — a batch cannot cite itself as
  historical evidence.
- **Packets (`011`, built, unrun).** A staged review is cut into numbered
  packets. The database accepts each packet once and closes the review only when
  every packet is done; a replay returns the stored completion and adds no
  duplicate finding. A finding aimed at a group the packet does not own is
  rejected.
- **Three grounded EVE tools.** `load_review_chunk` hands the model one bounded
  packet plus the valid category list; `review_precedent` fetches a few real
  historical examples and records exactly which evidence the model saw;
  `submit_review_chunk` rejects invented groups, unknown categories, unseen
  evidence, or a switched target. **None of them can change an invoice
  category** — applying a proposal stays a separate, approval-gated tool that
  does not exist yet.
- **Secure dispatch.** Vercel's OIDC helper authenticates the app's call to its
  own protected EVE endpoint, so the email webhook never opens an
  unauthenticated agent URL. Dispatch ids are `batch/attempt/packet`, so a
  webhook retry cannot launch a second review of the same packet.
- **Findings outbox (`012`, uncommitted, unrun).** A database trigger marks the
  queued row `ready` only when findings exist and `suppressed` when the review
  was clean, so a clean batch sends no second email. One worker claims the row;
  a second claim gets zero rows. The send carries a stable Resend
  `Idempotency-Key`.
- **Proof:** each migration was run twice against a disposable PostgreSQL and
  its behaviour asserted; `check-yunt-{review-persistence,review-jobs,
  batch-review,review-tools,dispatch,findings-email}.ts` all pass, and
  `tsc --noEmit` is clean on the working tree. `./check.sh` has **not** run
  since the outbox increment.
- **Gotcha — a test fixture that is smaller than production lies.** The `011`
  proof failed on a disposable `yunt_batches` missing two columns `009` had
  already added live. The migration was fine; the miniature was not.

### 2026-09-09 (c) — the first write boundary built and proved offline

- **Built the ingest writer, without connecting it.** A pure preflight builds
  complete `companies`, `item_catalog`, `invoices`, and `invoice_items` rows;
  any missing document field, prediction, or live category aborts before the
  first write. Dry-run is the default.
- **Made delivery idempotent at its real boundary.** `yunt_batches` claims a
  Resend message id or upload id once; a completed replay is a no-op. Failed
  batches may retry; concurrent `processing` claims fail loudly.
- **Made invoice writes atomic.** Migration `007_yunt_ingest.sql` writes an
  invoice and every line in one database transaction, explicitly omitting the
  generated `needs_review`. A failed line cannot strand a half-invoice that a
  retry would later mistake for a duplicate (D-063).
- **Fixed a shared-path resolver bug.** `loadResolver` fetched aliases but not
  the company ids needed to activate supplier-specific aliases, so the offline
  resolver test was greener than the upload/email paths. It now pages companies
  and maps supplier RUTs to their ids.
- **Proof:** `./check.sh` is all green, including the focused writer regression;
  a disposable PostgreSQL 18 database also proved replay idempotency, generated
  column behaviour, catalog normalization, and transaction rollback. Nothing
  contacted Supabase.
- **Gotcha — PostgreSQL output-column names are PL/pgSQL variables.** The first
  real migration run caught an ambiguous `item_name` in `ON CONFLICT`; aliasing
  the insert target fixed the migration before it reached production.

### 2026-09-09 (b) — the mailbox and the upload page; Resend and Vercel wired

- **Two doors into one pipeline.** `/carga` (ZIP upload, ADMIN-only, in the
  sidebar) and `POST /api/yunt/inbound` (the Resend webhook) both call
  `runIngest` in `src/lib/ingest/live.ts`. One copy of read → deduplicate →
  resolve → classify → report, so the two cannot drift. Neither writes.
- **Ported `yunt/classify.py`** to `src/lib/ingest/classify.ts`, dropping the
  Cloud Run identity token: that came from Google's metadata server, which does
  not exist on Vercel. The classifier stays public for now (D6).
- **Mail, with no new dependencies.** `mail.ts` is the only sender and refuses
  every recipient off `YUNT_ALLOWED_ADDRESSES`, which is unset. The Svix
  signature check is a dozen lines of `node:crypto` rather than the `svix`
  package, guarded by `scripts/check-webhook-signature.ts` — 2 acceptances, 11
  refusals including replay outside the tolerance window.
- **Set up in Afaq's accounts, by browser:** Resend webhook on `email.received`
  pointing at the `yunt` preview URL, signing secret rotated, old API key
  deleted and replaced, Vercel bypass secret created, six environment variables
  on Vercel Preview.
- **Decided:** D-058 (the Yunt acts on data problems, but only through one
  apply path), D-059 (the scope docx is a client menu, not the source of truth),
  D-060 (the upload page is permanent, not a stopgap), D-061 (shared Resend
  account, so filter inbound by recipient), D-062 (preview reaches the webhook
  through a Vercel bypass secret).
- **Gotcha — two wrong endpoints in the Python port, found by reading the docs
  rather than trusting it.** Attachments are at
  `/emails/receiving/{id}/attachments/{attachment_id}`, not `/emails/{id}/…`,
  and that returns JSON with a short-lived signed CDN `download_url` — a second
  hop, and the API key must **not** be sent to it.
- **Gotcha — concluded a feature was unavailable because a menu item was
  missing.** Said Resend inbound was not enabled on the account, having looked
  in the sidebar and in each domain's tabs. It is a **tab on the Emails page**,
  and inbound had been working for another project for 23 days. Absence of a
  menu entry is not evidence.
- **Gotcha — a Resend webhook cannot be scoped, and the intuitive fix does not
  work.** Creating one takes `endpoint` and `events` and nothing else, so every
  endpoint on the account gets every `email.received`. A dedicated subdomain
  changes nothing. Fixed in our code, by recipient (D-061).
- **Gotcha — the preview URL answers a webhook with 302 to a login page.**
  Vercel Authentication. Measured with `curl`, not assumed. Fixed with a
  protection-bypass secret in the query string (D-062).
- **Gotcha — `.gitignore` swallowed `.env.example`.** `.env*` matched the
  template too, so the file documenting every variable would never have been
  committed. Exempted explicitly.
- **Afaq's correction, and it was right: the scope docx is not authoritative.**
  Two copies existed and differed; several things were settled by discussion
  after it was sent. Its item 6 contradicts itself — "a flag never changes
  anything" beside "the YUNT proposes fixes and acts on Cristian's approval".
  He settled it: the Yunt is a collaborator, not an advisor (D-058).
- **Afaq's correction: Linear is not the map.** The tickets were made recently,
  for things only just discovered. Nine issues do not cover nineteen scope items.
- **Two secrets were pasted into the chat and had to be rotated.** Both replaced
  the same session. Terminal output pasted for debugging carries live values.
