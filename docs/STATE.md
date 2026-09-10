# STATE — where this project is right now

Updated every session. Last 5 sessions only; anything older that still matters
lives in `DECISIONS.md`.

## Now

**The pipeline is proved end to end offline and live-saved once.** On 2026-09-10
a synthetic invoice went through `/carga` as a signed-in user, was verified row
by row against live, replayed to prove the second upload changes nothing, then
removed. Live is back at baseline exactly: 5,195 invoices / 11,746 lines /
461 companies / 0 batches. Backup `supabase_20260910T044749Z`.

**Migrations `004`–`023` and `025` are LIVE; only `024` is pending.** Afaq ran
`021`–`023` and then `025` on 2026-09-10. `025` is independent of `024` — it
touches `invoices.transport_plate` and the precedent function, references
`yunt_flags` nowhere — so applying it first was safe, despite its header saying
"run after 024". `024_yunt_flags_dashboard_read.sql` grants signed-in users
*read* on `yunt_flags`; until it runs the new dashboard flag column shows
nothing.

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

**Git.** `ML-model` on `yunt-backend` at `5ef2fd7`. `milk-company` on `yunt` at
`5a03d23`, three commits past the last push (`02d7a58`): flags column,
invoice-context precedent, PDF/charts. Both working trees clean.

**Still to build in V1:** the approve/undo half of `MCT-155`, and the first half
of `MCT-149`, which needs the Claude API key. **Recurring reports (`MCT-154`) are
parked for V2** (D-069) — a first pass lives on `yunt-recurring-reports-v2` and is
deliberately not on `yunt`, so no V1 deploy registers a cron.

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

`agent/tools/` holds 20 tools; `src/lib/yunt/` holds 19 modules. Read that
listing before adding either — three re-implementations were caught only because
someone looked first.

**Grill him where his input is genuinely needed** — his domain knowledge has now
twice beaten a statistical conclusion (the folder-vs-RUT direction, and the
meter/plate finding above). Ask before concluding something about the client's
data is wrong.

### The order of work, agreed 2026-09-10

**Next, needs nobody:** the approve/undo half of `MCT-155`. `MCT-152` needs only
its acceptance run, not more building.

**Waiting on Afaq:** run `024`; the Claude API key, which unblocks the first
half of `MCT-149` and everything agent-shaped; a real email for `MCT-160`;
a decision on whether TypeScript ingestion should create Antillanca as a company
row when the old Python load never did.

**Last, deliberately:** `MCT-162` direction from the RUTs, and `MCT-163` the
four hardcoded-Spanish pages. Both work as they are; neither affects Antillanca,
who read Spanish and whose archives are named consistently. Do these when the
feature work is done, not before.

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
- **Backlog, deferred on purpose:** `MCT-162` direction from the RUTs,
  `MCT-163` hardcoded Spanish, `MCT-143` client data questions.

Tickets are written at product level on purpose — no file names, no migration
numbers, no function names — so an implementation discovery cannot turn one into
a lie. The *how* lives here and in `DECISIONS.md`.

## What the Yunt promises, and what it does today

The 19 numbered items are the scope sent to the team, in the client's own
words (`docs/Yunt_scope_v1.docx`). Where that document and `DECISIONS.md`
disagree on *how*, the decision log wins (D-059) — but this list is what
Antillanca was told they are getting, so it is the honest measure of progress.

**14 of 19 done in code, 3 partly, 2 not started. Nothing agentic is live yet.**

| # | What Cristian was promised | Today |
|---|---|---|
| 1 | A mailbox that acts only on agreed senders | Done. Never carried a real message |
| 3 | Duplicate detection on RUT + type + folio; sending twice changes nothing | Done |
| 4 | Lines classified and **written to the database** | Done. `021` is live and a signed-in person has saved through `/carga` on live, verified and cleaned back to baseline. Email has still never carried a real message |
| 5 | An acknowledgement in minutes, then a written report | Done in code as a receipt first and a findings email later; never live-proved |
| 6 | Data quality flags, and fixes proposed on approval | Partly. Detection is built, calibrated and persisted to `yunt_flags`; the dashboard column is built but dark until `024` runs. Proposing fixes remains |
| 7 | Category proposals with evidence, grouped | Partly. Built, grounded, and now triggered by every write. Accuracy still unmeasured |
| 8 | Approve a group, get a confirmation, undo it | Done in code. The confirmation is the database's own words, not the model's |
| 9 | Five query tools answering open questions | Done in code. All five built and proved. `022` is not live |
| 10 | Figure in the body, list as spreadsheet, report as PDF, filter printed on top | Done in code. Figure, CSV attachment and a true PDF, with the filter and basis printed on each. No real question has been answered with one yet |
| 11 | Charts from a fixed set, drawn by code | Done in code. Five fixed types drawn as SVG by `src/lib/yunt/report.ts`, no chart library |
| 12 | Says so when a question does not fit, and we learn from the list | Done in code. One immutable backlog entry per stored request; not live until `017` runs |
| 13 | Month-end summary, post-batch digest, weekly review list | **Parked for V2** (D-069). A first pass exists on a side branch; the post-batch half is arguably already the findings email |
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
