# STATE — where this project is right now

Updated every session. Last 5 sessions only; anything older that still matters
lives in `DECISIONS.md`.

## Now

**The pipeline is proved end to end offline and live-saved once.** On 2026-09-10
a synthetic invoice went through `/carga` as a signed-in user, was verified row
by row against live, replayed to prove the second upload changes nothing, then
removed. Live is back at baseline exactly: 5,195 invoices / 11,746 lines /
461 companies / 0 batches. Backup `supabase_20260910T044749Z`.

**Migrations: `026` is CONFIRMED live; `024` is believed pending; `023` and
`025` are believed live but NOT re-verified.** Afaq lost track of what he pasted
(2026-09-10) and asked that this be settled first next session. `026` is proved
by behaviour, not by a doc: a quotation saved with no file at all on 2026-09-10,
which `storage_path NOT NULL` would have refused. **Verify the rest the same
way — by what the database does, not by what this file says.** Every statement
in `023`–`026` is idempotent (`if exists` / `if not exists` / `drop not null`),
so re-pasting any of them is safe and is the cheapest way to be certain. Afaq ran
`021`–`023` and then `025` on 2026-09-10. `025` is independent of `024` — it
touches `invoices.transport_plate` and the precedent function, references
`yunt_flags` nowhere — so applying it first was safe, despite its header saying
"run after 024". `024_yunt_flags_dashboard_read.sql` grants signed-in users
*read* on `yunt_flags`; until it runs the new dashboard flag column shows
nothing. `026_quotation_without_file.sql` (Afaq ran it 2026-09-10) lets a
quotation be a stated price rather than a document.

**`MCT-164` is done and closed.** The apparent label inconsistency was
deterministic all along. `dte.ts` now keeps `<Transporte><Patente>` as
`invoices.transport_plate`, and `025` ranks an exact `meter_code` match above
mere same-wording evidence. Measured on the fixed 400-line held-out run,
confidently-wrong proposals fell **5.75% → 2.76%**, 97.2% of proposals correct.
Reproduce with `.venv-backend/bin/python scripts/87_measure_precedent_quality.py 400`.

**`MCT-152` is implemented but not closed.** `reply_with_report` queries the
aggregate RPC itself and attaches a real PDF or one of five code-drawn SVG
charts (bar, monthly line, stacked bar, pie, table). Filter, accounting basis,
credit-note rule and truncation disclosure are printed on the artefact. Focused
generator check, targeted lint, `tsc --noEmit` and a visual PDF render all
passed. What remains is the acceptance run from one real stored question.

**`MCT-155` is half done.** The dashboard flag column is committed (`0d20315`);
`024` must run before a signed-in user sees anything. The approve/undo half is
not built.

**`YUNT_ALLOWED_ADDRESSES` was never unset.** It has been on Vercel Preview
since 2026-09-09, value unknown because every var is sensitive-flagged and reads
back as `[SENSITIVE]`. That is what produced the wrong note in earlier docs.
`vercel env rm` is blocked by the permission classifier, so converting them to
readable needs Afaq. He has said this is a readability preference, not a blocker.

**Git.** `ML-model` on `yunt-backend` at `1b19a65`; `CLAUDE.md` was already
modified when this session began, and this session changes `STATE.md` and
`DECISIONS.md`. `milk-company` on `yunt` at `205451d`, 12 commits past its
upstream. Three uncommitted performance files remain parked: dashboard and
products cache experiments plus the analytics hint nesting fix. Do not mix them
into feature work without reopening `MCT-166`.
Parked branch `yunt-recurring-reports-v2` holds the V2 recurring-reports work
and its own `026` — renumber that one when it is resumed (D-069).

**Purchasing is proved end to end on live**, by using the screens rather than
reading them: request → quotations → order above CLP 500,000 refused with fewer
than two → allowed with two → request closed → numbered PDF. `MCT-140`,
`MCT-161`, `MCT-168` and `MCT-169` are closed on that evidence. Test rows are
marked `PRUEBA`; delete by `title like 'PRUEBA%'`, orders before requests.

**The original V1 scope has no missing implementation code.** It contains 19
promises; recurring reports (#13 / `MCT-154`) are parked for V2 (D-069), leaving
18 active. All 18 have code, 8 are fully accepted end to end, and 10 still need
live integration or acceptance (see the table below). Outside that original
scope, `MCT-165` — judging whether a quotation is genuine before it counts
toward the CLP 500,000 rule — is still unbuilt and needs the Claude API key.
`MCT-155` only needs `024` plus a person reading real flags; D-070 deliberately
forbids the Yunt from proposing edits to values copied from a DTE.

**Do not drive the Supabase SQL editor.** A previous session typed over editor
buffers holding Afaq's own saved queries. Read live state through
`scripts/supabase_rest.py` or ask him to run a query and paste the result.

### Working agreement, set by Afaq on 2026-09-10

One ticket at a time: implement, check it in the UI at `localhost:3000`, run an
end-to-end test, fix what breaks, update the ticket, close it, move on. Do not
open five things at once. Anything touching production data needs a rollback
path written *before* the write and a backup taken first. Tickets were
AI-generated and are **not authoritative** — correct them when they are wrong.
Post concise, ASCII-only project updates in Linear after each milestone, pitched
at a product manager, not at an engineer.

`agent/tools/` holds 22 tools; `src/lib/yunt/` holds 22 modules. Read that
listing before adding either — three re-implementations were caught only because
someone looked first.

**Grill him where his input is genuinely needed** — his domain knowledge has now
twice beaten a statistical conclusion (the folder-vs-RUT direction, and the
meter/plate finding above). Ask before concluding something about the client's
data is wrong.

### The order of work, agreed 2026-09-10

**First, cheap and blocking nothing else:** confirm which migrations are
actually applied (see Now). Re-pasting an idempotent migration settles it.

**Completed this session:** `MCT-163` localises the upload and purchasing UI in
both languages while leaving Antillanca's stored and client-facing content in
Spanish (D-071). `MCT-167` adds the missing order-centric list. Both passed
targeted lint, TypeScript, translation-key parity and browser checks. They are
committed together as `205451d`; their Linear status still needs updating.

**Next, needs nobody:** there is no more missing original-scope feature code
that can be completed without credentials or live input. `MCT-152` needs only
its acceptance run from a real stored question; none currently exists.

**Waiting on Afaq:** run `024`; the Claude API key, which unblocks the first
half of `MCT-149`, `MCT-165` and everything agent-shaped; a real email for
`MCT-160`;
a decision on whether TypeScript ingestion should create Antillanca as a company
row when the old Python load never did.

**Deferred deliberately:** `MCT-162`, direction from the DTE RUTs instead of
the ZIP folders, is not required by the signed V1 scope. Performance work in
`MCT-166` is parked while functionality is finished. Recurring reports remain
parked for V2.

**Ticket coverage is not proven.** The tickets were AI-generated and may not
span the whole scope. Closing them all is not the same as building everything.
Reconcile `docs/Yunt_scope_v1.docx` and `DECISIONS.md` against the closed
tickets at the end — the decision log wins where they disagree (D-059).

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

## Linear, as of 2026-09-10

Linear mirrors this project feature by feature, so it can be read instead of this
file for *progress*. It is not the design; where a ticket and `DECISIONS.md`
disagree, the decision log wins.

- **Done:** `MCT-139` ingest, `MCT-145` upload page, `MCT-146` save to database,
  `MCT-147` auto-accept rate, `MCT-148` purchasing tables, `MCT-151` answer
  questions, `MCT-158` run pending migrations, `MCT-159` signed-in save,
  `MCT-164` the field that decides the answer.
- **In progress:** `MCT-142` the parent, `MCT-149` review and propose (blocked on
  the API key), `MCT-150` approve and undo, `MCT-152` PDF/charts (built, needs
  acceptance), `MCT-153` refusals (cannot close without a live refusal),
  `MCT-155` flags (needs `024`), `MCT-156`/`157` purchasing from email,
  `MCT-161` the order document, `MCT-140`/`141`/`144`.
- **Todo:** `MCT-160` the first real email.
- **Backlog, parked for V2:** `MCT-154` recurring reports (D-069).
- **Built and awaiting ticket update:** `MCT-163` hardcoded Spanish and
  `MCT-167` the order-centric list (`205451d`).
- **Backlog, deferred on purpose:** `MCT-162` direction from the RUTs and
  `MCT-143` client data questions.

Tickets are written at product level on purpose — no file names, no migration
numbers, no function names — so an implementation discovery cannot turn one into
a lie. The *how* lives here and in `DECISIONS.md`.

## What the Yunt promises, and what it does today

The 19 numbered items are the scope sent to the team, in the client's own
words (`docs/Yunt_scope_v1.docx`). Where that document and `DECISIONS.md`
disagree on *how*, the decision log wins (D-059) — but this list is what
Antillanca was told they are getting, so it is the honest measure of progress.

**Implementation: 18 of 18 active V1 promises have code; #13 is parked for
V2. Acceptance: 8 of those 18 are proved end to end, and 10 still need a live
email, model run, migration or real request. Nothing agentic is live-proved
yet.**

| # | What Cristian was promised | Today |
|---|---|---|
| 1 | A mailbox that acts only on agreed senders | Built. Never carried a real message |
| 2 | A ZIP containing SII XML under `COMPRAS` and `VENTAS` | Proved through `/carga`; the real mailbox path is still unproved |
| 3 | Duplicate detection on RUT + type + folio; sending twice changes nothing | Done |
| 4 | Lines classified and **written to the database** | Built and proved through `/carga` on live; the email route remains unproved |
| 5 | An acknowledgement in minutes, then a written report | Built as a receipt first and a findings email later; never live-proved |
| 6 | Data quality flags, and fixes proposed on approval | Flags are built, calibrated and persisted; the dashboard stays dark until `024`. D-070 corrects the scope: DTE values are reported, never changed; only category changes can be proposed |
| 7 | Category proposals with evidence, grouped | Built and grounded; deterministic precedent quality measured at 97.2% of proposals correct. The real Claude review still needs its key and acceptance run |
| 8 | Approve a group, get confirmation, undo it | Built with database-enforced confirmation and undo; no live agent run yet |
| 9 | Five query tools answering open questions | Done. All five built and their figures independently proved; `022` is live |
| 10 | Figure in the body, list as spreadsheet, report as PDF, filter printed on top | Built and visually checked. No real stored question has received one yet |
| 11 | Charts from a fixed set, drawn by code | Done. Five fixed SVG types are code-drawn and checked |
| 12 | Says so when a question does not fit, and we learn from the list | Built and migration `017` is live; no real refusal exists yet |
| 13 | Month-end summary, post-batch digest, weekly review list | **Parked for V2** (D-069). A first pass exists on a side branch; the post-batch half is arguably already the findings email |
| 14 | Form one: what is needed, how much, by when, for which farm | Done and exercised on live |
| 15 | A request stays open until an order closes it | Done, database-enforced and exercised on live |
| 16 | Form two, with the two-quotation rule above CLP 500,000 | Done; refusal with fewer than two and success with two were both proved on live |
| 17 | A purchase-order PDF Antillanca sends themselves | Done. The print page and true PDF use one loader and were exercised on live |
| 18 | The Yunt fills form one from a plain-language email | Built; exact confirmation turns a stored draft into a request. Migration `018` is live, but no real email/model run exists |
| 19 | The Yunt drafts the order once a quotation exists | Built; exact confirmation issues the order and migration `020` is live. No real email/model run exists |

**Read the middle column, not only the count.** The deterministic base is
proved. The EVE review and action tools are called by the email path in code,
but model credentials and real-message proof are still open. The repository has
22 agent tools; all tools promised by the original scope exist. `MCT-165` is an
important discovered safety gap outside that scope, not evidence that the scope
toolset is missing.

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
- [x] `/carga` live save: `021` is live and one real signed-in save has been
      proved on live, then cleaned back to baseline exactly
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
- [x] **Report as PDF, and charts from the fixed set** — one tool, five chart
      types drawn as SVG by code, PDF written without a browser. Acceptance from
      a real stored question is still outstanding
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
- [ ] Flags shown per line in the dashboard — built (`0d20315`), dark until `024` runs

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
- [ ] **Run `024`** in the Supabase SQL editor. Proved by
      `scripts/prove-024-yunt-flags-read.sh`; it grants read only and changes no
      row. `021`-`023` and `025` are already applied
- [x] `021` written and proved (`scripts/prove-021-carga-writes.sh`)
- [x] `/carga` permission design decided: any signed-in user, no roles in v1
- [ ] **Your yes on the 222 harvested aliases** (`006` is live, so unblocked)
- [ ] Send the first real email to `antillanca.yunt@mountaincreative.cl`
- [ ] Fix the `Confeccion de Bolos` duplicate — three catalog rows, one thing

### Deliberately not in v1

Roles and approval chains on purchase orders (D-052, and the scope document says
so in the client's own words), goods receipt / invoice matching / payment, and
ingestion from the Audisoft API, which is blocked on credentials that return 401
(D-054), and — since 2026-09-10 — **recurring reports**, scope item 13, which
were in v1 until the product questions behind them turned out to be unanswered
(D-069).
## Recent sessions

### 2026-09-10 (e) — localisation finished and scope counted from the contract

- **`MCT-163` built and accepted in the browser.** `/carga`, `/solicitudes`,
  request detail/order forms, `/ordenes` and `/levantamiento` now use the shared
  Spanish/English catalog. English changes only interface chrome; Antillanca's
  stored values, generated reports and purchase-order documents remain Spanish
  (D-071).
- **`MCT-167` built.** `/ordenes` is now an order-first list with order number,
  supplier, amount and date, linked from requests. Live currently has zero
  orders, so the browser acceptance proved the real empty-data state; it did not
  invent a production order to exercise a row.
- **Proof:** targeted ESLint, `npx tsc --noEmit --incremental false`, catalog
  parity (42 upload keys and 115 purchasing keys), `git diff --check`, and all
  five affected routes in the signed-in browser in both locales. Commit
  `205451d`.
- **Reconciled the 19-item scope from `Yunt_scope_v1.docx`, not ticket status.**
  Item 13 is parked; every active item has code. Eight are fully accepted and
  ten need live integration/acceptance. All original-scope tools exist; there
  are 22 agent tools and 22 Yunt library modules, correcting the stale 20/19
  inventory.
- **Ticket coverage is broad but not proof of completeness.** `MCT-165` is a
  discovered safety gap outside the original promise, and several tickets call
  code-built work done without the live email/model evidence their own done-when
  requires.
- **Performance stayed parked.** Three uncommitted cache/hydration files remain
  outside the feature commit. Do not let them obscure the remaining functional
  acceptance work.

### 2026-09-10 (d) — purchasing proved by using it, and four defects it hid

- **Checkpoint repair.** Codex replaced this file with 41 lines before dying;
  the 900-line version was still uncommitted at `HEAD`, so nothing was lost.
  Restored, trimmed to five sessions, and the dead 2026-09-09 HANDOVER section
  deleted. `CLAUDE.md` and `supabase/README.md` had gone false about migrations.
- **`MCT-154` parked for V2** (D-069) after building a first pass and realising
  every product question behind it had been guessed. Code lives on
  `yunt-recurring-reports-v2`, off the release branch so no cron is registered.
- **`MCT-155` scope settled** (D-070): the Yunt may change a category and never
  a value off the document. Already enforced — `apply_yunt_proposal` refuses
  `data_fix` and `review-persistence.ts` hardcodes `category_change`. That
  refusal is the decision, not unfinished work. The model is now told so.
- **`MCT-161` closed.** One loader feeds the print page and a new PDF route, so
  the printed and emailed order cannot drift. The PDF writer was emitting ASCII,
  printing "Comercial Peña y Muñoz" as "Pena y Munoz" on a document that
  supplier reads; the font already declared WinAnsi, so it just had to be
  written as Latin-1. `MCT-152`'s reports inherit the fix.
- **`MCT-140` closed**, exercised on live: the CLP 500,000 rule refused an order
  with no quotations and allowed one with two. The rule is `count(*)` in the
  database, never a model — `MCT-165` raised because counting cannot tell a real
  quotation from a blank file.
- **`MCT-168` closed.** A quotation may now be a stated price; a constraint
  keeps it honest — document or source, never neither, because either way it
  counts toward a rule that gates money.
- **`MCT-169` closed.** The request page could always show what an item last
  cost; nobody had ever seen it, because nothing linked a request to a
  catalogued item. Verified live: Petroleo Diesel shows FEROSOR AGRICOLA at
  753/709/864/747. Everything stays free text — the list is a shortcut.
- **Gotcha — every internal link dropped the locale and 404'd.** Eleven files
  imported plain `next/link`/`useRouter` when `createNavigation` versions exist.
  Creating a request landed on a 404 *after saving it*, so it read as failure.
  All 18 routes now return 200 in both locales.
- **Gotcha — the home screen's CLP 500,000 notice never rendered.** `<strong>`
  in a message is a next-intl rich-text tag, not HTML, so `t()` threw and the
  card came up empty. `t.rich` fixes it and removes two `dangerouslySetInnerHTML`
  sinks fed by translator-controlled strings.
- **Gotcha — a one-click price chip read $753 and filled 752.99.** CLP has no
  cents; the stored figure is a division artefact. Found by clicking it.
- **All four defects above passed types, lint and `check.sh`.** `CLAUDE.md` now
  says a feature is not finished until it has been used in the browser.
- **`MCT-144` closed by re-measuring, not building:** 81.3% of 11,746 lines
  match with nobody involved and every automatic match lands where it sits
  today. The only 7 disagreements are the known `Confeccion de bolos` triple.
- **`MCT-166` closed, and it was two pages.** The dashboard cached ~3.7 MB of
  invoices and `/productos` ~3.25 MB of summaries through `unstable_cache`,
  which refuses anything over 2 MB — so neither ever cached anything and both
  threw on every render before querying anyway. Removing the wrapper changes
  nothing at runtime. The second page was found by reading the server log while
  fixing the first, which is the argument for reading logs rather than trusting
  a green suite.

### 2026-09-10 (c) — the deciding field, and reports that carry a file

Run by Codex; it hit its usage limit mid-checkpoint, having replaced this file
with a 41-line summary. The 900-line version was still uncommitted at `HEAD`, so
nothing was lost; the work below was reconstructed from `git`, Linear and the
migration ledger, not from its summary.

- **`MCT-164` closed.** `dte.ts` keeps `<Transporte><Patente>`; `025` stores it
  as `invoices.transport_plate` and ranks an exact `meter_code` match above
  same-wording evidence in `yunt_category_precedent`. Afaq applied `025`.
- **Measured, not asserted:** the fixed 400-line held-out run moved
  confidently-wrong proposals from **5.75% to 2.76%**, 97.2% of proposals
  correct. `scripts/87_measure_precedent_quality.py 400`.
- **`MCT-152` built** (`5a03d23`): `reply_with_report` runs the aggregate query
  itself and attaches a true PDF or one of five code-drawn charts, with the
  filter, basis, credit-note rule and any truncation printed on the artefact.
  Checked by `npx tsx scripts/check-yunt-report.ts`, targeted ESLint,
  `npx tsc --noEmit`, and a Poppler render of the produced PDF. Not closed —
  the acceptance run from a real stored question has not happened.
- **`MCT-155` half built** (`0d20315`): the flag column exists in the explorer
  tab and `024` is written and proved, but not run, so it displays nothing yet.
- **Decided:** an exact meter match outranks wording similarity (→ D-068).
- **Gotcha — Linear accepts a status change but rejects a detailed metrics
  comment.** Its outbound-data policy blocks the numbers, not the transition.
  Keep ticket comments short and product-level; put the measurements here.
- **Gotcha — `025`'s own header says "run after `024`" and that is advice, not a
  dependency.** It references `yunt_flags` nowhere. Read the migration before
  believing its header.

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
  `scripts/87_measure_precedent_quality.py`.
- **That conclusion was WRONG, and Afaq caught it within the hour.** He said to
  check the description and the client convention before blaming the labels.
  Both paid out. **There is no inconsistency at all.** All 29 wordings are
  decided by a field the precedent search never looks at:
  **23 wordings / 882 lines are determined by `meter_code` with zero
  exceptions** — different electricity meters are different cost centres, so
  `Servicio publico` correctly lands in three categories (3021→EXP-11.2 15/15,
  124581→EXP-11.1 15/15, 28201→EXP-9.1 6/6). The remaining
  **6 wordings / 625 lines are all petrol**, decided by the DTE's
  `<Transporte><Patente>` — plate means `ADM-1.4`, jerrycan means `EXP-11.4`,
  a rule already written in `docs/CLIENT_CONVENTIONS.md:55-61`. The raw XML
  carries it (78 of 600 sampled COMPRAS invoices) and **`dte.ts` discards it** —
  no reference to `Patente` or `Transporte` anywhere — so it never reaches the
  database and the rule cannot be applied. Raised as **`MCT-164`** (High). The
  `MCT-143` comment was **withdrawn**; nothing goes to the client.
- **The lesson, worth more than the ticket:** apparent label noise was
  100% deterministic once the right column was used. Before concluding the data
  is inconsistent, check what else the row carries and read
  `CLIENT_CONVENTIONS.md`. Statistics over `item_text` alone will manufacture
  ambiguity that is not there.
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
