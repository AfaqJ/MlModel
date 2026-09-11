# STATE — where this project is right now

Updated every session. Last 5 sessions only; anything older that still matters
lives in `DECISIONS.md`.

## Now

**Test 1's classification cases are proved end to end on live email, and three
real bugs were found and fixed doing it.** Every case ran through real Outlook
mail, the deployed agent and live Supabase. Deployed frontend is `72562e8`.

| Case | Result |
|---|---|
| Approve a proposal | Applied. `096b6abe`, ADM-1.4 → ADM-1.8, 1 row |
| Reject one | Honoured, nothing touched, proposal left pending |
| Correct with a category never suggested | Staged as EXP-2.6, confirmed, applied (`5b204210`) |
| `Undo that.` | Restored all four recorded before-values exactly |
| Approval phrase not on the first line | Refused; nothing applied |

**Nothing was ever written before a confirmation**, in any run. Applied rows
carry `prediction_source = 'yunt_applied'` (D-066) and complete before-state.

**The proposal lookup had never once worked on live** (D-081). It compared
Resend's API uuid to an RFC Message-ID. The 2026-09-11 "Apply the Leasing
change" success was Codex's manual recovery script, not the agent. Resolution
now comes from the conversation, verified against live data before shipping.

**Two more fixes in the same run.** The client-facing "Por qué" printed the
model's filler — "esta categoría encaja mejor con el concepto" — because the
grounded precedent we had already computed lost to whatever prose survived the
internal-terms filter. It now leads with the precedent, satisfying D-080. And a
category written the way the Yunt itself prints it — `EXP-2.6 Otros Gastos Salud
Animal`, code and name together — was rejected as "no unique category"; the
matcher now accepts code, name, or both.

All three carry regression checks **verified to fail against the pre-fix code**:
`check-thread-batch-resolution.ts`, and two new cases in
`check-yunt-action-confirmation.ts`. `./check.sh` is green.

**Still open, deliberately not spent on:** the stale-proposal refusal is
enforced in SQL by `apply_yunt_proposal` and covered offline by
`check-yunt-apply.ts`; it was not re-proved live. One proposal, G0002, is still
pending on purpose and is the cheapest next live case.

**A rejection is acknowledged but not recorded.** Saying "no, déjalo como está"
leaves the proposal in `proposed`. Nothing is wrong with the data, but there is
no stored trace that the client declined it.

**Live is NOT at baseline — the test batch is still there**, and
`scripts/90_yunt_live_test_undo.py` dry-runs clean against it: 6 invoices, 7
lines, 6 catalog items, 1 batch, 14 inbound requests, 4 proposals, 3
applications, 1 refusal. Both applied category changes sit on those test lines,
so removing the batch removes them; no production row was touched. Backup
`backups/supabase_20260911T093640Z`. Run with `--apply` when the batch is no
longer needed.

**`yunt_refusals` has its first row**, which is what `MCT-153` was waiting for.
It has not been inspected.

## Next

1. Decide whether to clean the test batch now (`--apply`) or keep it for the
   stale-proposal case and any further Test 1 work. G0002 is the live anchor.
2. Close what the evidence supports. `MCT-150`'s approve-and-undo path is now
   proved through real email; check each ticket's own done-when before closing,
   and do not close on code alone.
3. Then the report/refusal thread (MCT-152/153 — a real refusal now exists) and
   purchasing (MCT-156/157).

## Prior checkpoint (superseded by `Now` above)

**Step 0 had been run before the key was added.** `docs/GO_RUNBOOK.md` became the
operative file: the three tests were prepared, the fixtures existed and had
been read through the real ingest, and the undo was written and dry-run.

**Four blockers were found for free before anything was spent; all are now
resolved.** At that checkpoint there was no model credential on Vercel (the agent runs
in the deployment, so `.env.local` is not enough); every deploy since
2026-09-10 fails because the eve service emits an Edge `_middleware`, which is
fixed here with `runtime: "nodejs"` but unverified until a push; Vercel
Deployment Protection answers 401 to every request, Production included, so the
Resend webhook has never been able to reach `/api/yunt/inbound` at all; and 18
commits are unpushed, so the newest working Preview is two days behind. Details
and the fix for each are in `GO_RUNBOOK.md`.

**`YUNT_ALLOWED_ADDRESSES` is one address: `afaq@mctechstudio.com`.** Read from
`.env.local`, which earlier docs assumed was unreadable. Mail from anywhere else
is ignored in silence, so every test email must be sent from there.

### Completed actionable list, answered by Afaq on 2026-09-11

Completed in this order. Kept as history because D-077 through D-079 explain
the resulting architecture.

1. **Afaq adds the Anthropic key to Vercel himself**, so it never passes through
   a transcript. Unflagged, not sensitive, so a later session can confirm it is
   there (D-077):
   `vercel env add ANTHROPIC_API_KEY preview` — paste at the prompt.
2. **Switch the agent to the direct Anthropic path** (D-077): `npm i
   @ai-sdk/anthropic`, `model: anthropic("claude-sonnet-5")` in
   `agent/agent.ts`, and `YUNT_REVIEW_MODEL` in `src/lib/yunt/after-write.ts`
   to `claude-sonnet-5` in the same commit — D-076 says those two move together.
   In the same edit, `defaultTools: false` (D-078).
3. **Push `yunt` and watch the deploy.** 18 commits, and the top one carries the
   `runtime: "nodejs"` middleware fix for
   `Edge Runtime is not supported in services`. Afaq has asked for this to be
   done for him. If the deploy still fails, the next thing to try is Next 16's
   `proxy.ts` (`npx @next/codemod@canary middleware-to-proxy .`); the Edge
   function is what Vercel refuses, not the middleware's logic.
4. **Deployment Protection is still on and nothing bypasses it.** Afaq thought
   he had added a bypass; `vercel env ls` shows no automation-bypass secret on
   the project, and a request carrying a made-up bypass value is redirected to
   the Vercel login exactly like one carrying none. So Resend has never reached
   `/api/yunt/inbound`, and no email test can pass until either protection is
   off for the project or a Protection Bypass for Automation secret exists and
   is appended to the webhook URL in Resend as
   `?x-vercel-protection-bypass=<secret>`. The svix signature covers the body,
   so a query string does not invalidate it. **This is a Vercel dashboard
   setting and it needs Afaq.**
5. **Delete the leftover test row** — one `purchase_requests` row,
   `SOL-2026-0003` "Petroleo Diesel", whose description already says
   `PRUEBA 4 ... Eliminar despues`. Afaq has confirmed it is his test row.
   Back up first, write the delete as a scoped PostgREST call anchored on that
   `request_id`, and re-snapshot the baseline afterwards
   (`scripts/90_yunt_live_test_undo.py --snapshot`), because the purchasing
   baseline moves from 1 to 0.
6. **Delete the Python `yunt/`** (D-079), and in the same commit take
   `CLAUDE.md`'s warning about it, and the `.venv-yunt` test conventions, out
   with it.
7. **Then run the three tests**, in `docs/GO_RUNBOOK.md`'s order. Everything
   they need already exists: the archive, the fixture check, the undo and its
   snapshot.

**The earlier MCT-155 cleanup returned live to baseline exactly** — 5,195 invoices /
11,746 lines / 461 companies / 4,002 catalog items / 78 categories. Backup
`supabase_20260911T074329Z`. The
MCT-155 test batch was written to live, read, judged and removed; the undo script
`scripts/89_cleanup_mct155_test.py` restored the counts exactly and is the pattern
to copy for the next live test (anchored on one fake supplier RUT, dry-run by
default, verifies the baseline itself).

**Migrations: `024`, `026` and `027` are CONFIRMED live; `023` and `025` are
believed live but NOT re-verified.** `024` is proved by the signed-in dashboard
reading `yunt_flags` without error; `026` by a quotation saved with no file at
all; `027` by flags actually landing on a save. Everything in `023`–`027` is
idempotent, so re-pasting is safe and is the cheapest way to settle the last two.

**The classifier was redeployed on 2026-09-10 and ingest works again.** Revision
`mlmodel-00015-mjr`, image tag `v1.3.3-plate`, 100% of traffic. The model is
untouched — `artifacts/v1.3.3-int8/` has no commits since the previous deploy and
`/artifact-check` reports the same 278,181,947 bytes — so this shipped code, not
weights: `5ef2fd7` had added `transport_plate` to `app/api/schemas.py` that
morning while Cloud Run still ran the container built before it, and Pydantic
answers `422 extra_forbidden` to an unknown key. Every ingest failed at the
classify step for a few hours, found by driving `/carga` rather than by a test.

`docs/TEST_CHECKLIST.md`'s "Before deploying" list is now
`scripts/88_prove_deploy.sh`; all seven checks pass against the live revision,
including the incident path and its direction guard. The income slice does **not**
gate this kind of release — it gates accepting a *retrain*, read off
`model_card.json`, and there is no new model card. Rollback stays a traffic shift
to `mlmodel-00014-lrp`, no rebuild.

**The review now runs on Sonnet 5 at `high` reasoning (D-076).** Two files must
agree: `agent/agent.ts` picks the model, `YUNT_REVIEW_MODEL` in
`src/lib/yunt/after-write.ts` stamps it on each attempt as provenance. What would
reverse it is review *quality*, not cost — see D-076 for what to watch for.

**`reviewAfterWrite` now takes an optional dispatcher** (`2e496a6`), so the whole
review chain — packets, chunking, the submit guard, proposals, approval, apply,
undo — can be driven by a stub with no API call. That is step 0 of the test plan
and it should happen before the key is wired.

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

**`MCT-155` is done and closed.** Flags are written, shown per line in both
languages, and have been read on live data and judged useful. There is no
approve/undo half: a flag reports a problem in the supplier's document and never
changes a value (D-070), so there is nothing to approve. Category proposals keep
their own approve-and-undo path, which is `MCT-150`.

**`YUNT_ALLOWED_ADDRESSES` was never unset.** It has been on Vercel Preview
since 2026-09-09, value unknown because every var is sensitive-flagged and reads
back as `[SENSITIVE]`. That is what produced the wrong note in earlier docs.
`vercel env rm` is blocked by the permission classifier, so converting them to
readable needs Afaq. He has said this is a readability preference, not a blocker.

**Git.** `ML-model` is on `yunt-backend`; this checkpoint and its test fixtures
follow `f3dff7b`. `milk-company` is on `yunt` at `7d8b632`, pushed and deployed.
Three uncommitted performance files remain parked: dashboard and
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
`MCT-155` is closed; D-070 deliberately forbids the Yunt from proposing edits to
values copied from a DTE.

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

### The order of work, as of 2026-09-11

**Nothing is left that does not need the key.** Every open ticket is blocked on a
live run. The plan for those runs is `docs/YUNT_TEST_PLAN.md`, and its step 0 —
driving the whole review chain from a stub, free — should happen **before** the
key is wired, because that is where the non-model bugs are.

**Waiting on Afaq:** the Claude API key (see the test plan for exactly which
variable, which depends on whether it is a gateway key or an Anthropic one), and
a real invoice email for `MCT-160`.

**Still unverified, cheap:** `023` and `025` are believed live but were never
re-checked. Both are idempotent; re-pasting settles it.

**`MCT-162` is done (D-072).** Direction is read from the RUTs in each document
— Antillanca as `RUTEmisor` is a sale, as `RUTRecep` a purchase — and the
`COMPRAS`/`VENTAS` folder is only a fallback for a document naming neither. That
case does not exist: across all 5,584 raw DTEs, Antillanca is on exactly one side
of every one, never neither and never both, and the RUT rule reproduces the
folder on all 5,195 ingested documents with **zero disagreements**. So nothing
already stored is relabelled; what changed is that a flat or differently-named
archive is now accepted instead of rejected file by file. Proved on `/carga`:
six documents in one flat `todo/` folder, four purchases and two sales, read and
split correctly with nothing written. The `no_direction_folder` rejection reason
is gone.

**Deferred deliberately:** `MCT-143` client data questions stay logged, not
raised: Afaq's call on 2026-09-10 was that they do not appear to affect
processing logic. Performance work in `MCT-166` is parked while functionality is
finished. Recurring reports remain parked for V2.

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

To put a file into the upload form without a file picker, build the bytes in the
page and assign them through a `DataTransfer`, then `form.requestSubmit()`.

**Do not stage the file in `milk-company/public/`.** It reads as cheaper than
inlining base64 and it is not: the dev server watches that directory, so writing
there triggers Fast Refresh, the page reloads, and the file input is cleared
before the submit lands. The symptom is a submit that silently does nothing,
twice, with no console error. Inline the base64 — a one-document ZIP is about
1.3 KB of it. Also wait for hydration before assigning: on a freshly navigated
page the first `requestSubmit()` can be swallowed, and clicking the real button
by `ref` after setting the file is the reliable form.

## Linear, as of 2026-09-11

Linear mirrors this project feature by feature, so it can be read instead of this
file for *progress*. It is not the design; where a ticket and `DECISIONS.md`
disagree, the decision log wins.

- **Done:** `MCT-139` ingest, `MCT-145` upload page, `MCT-146` save to database,
  `MCT-147` auto-accept rate, `MCT-148` purchasing tables, `MCT-151` answer
  questions, `MCT-158` run pending migrations, `MCT-159` signed-in save,
  `MCT-164` the field that decides the answer.
- **In progress — every one blocked on a live run, none on missing code:**
  `MCT-142` the parent, `MCT-149` review and propose, `MCT-150` approve and undo,
  `MCT-152` PDF/charts (needs one real stored question), `MCT-153` refusals
  (needs one real refusal), `MCT-156`/`157` purchasing from email, `MCT-141`
  receive by email.
- **Todo:** `MCT-160` the first real email.
- **Backlog, parked for V2:** `MCT-154` recurring reports (D-069).
- **Backlog, parked performance:** `MCT-166`; removing the broken cache stopped
  its error loop but did not satisfy its no-second-query done-when.
- **Done:** `MCT-163` hardcoded Spanish and `MCT-167` the order-centric list
  (`205451d`); `MCT-162` direction from the RUTs (D-072) and `MCT-155` quality
  flags, both closed 2026-09-11 with proof comments.
- **Backlog, deferred on purpose:** `MCT-143` client data questions.

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
| 6 | Data quality flags, and fixes proposed on approval | **Done.** Built, calibrated, persisted, shown per line in both languages, and accepted on live data. D-070 corrects the scope: DTE values are reported, never changed; only category changes can be proposed |
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
- [x] Flags shown per line in the dashboard, in both languages, proved on live
      data and judged useful (`MCT-155` closed 2026-09-11)

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
- [x] **`024` is run and confirmed live** (2026-09-10). Proved offline by
      `scripts/prove-024-yunt-flags-read.sh` and on live by the signed-in
      dashboard reading `yunt_flags` without error
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

### 2026-09-11 (c) — Test 1's classification cases, and the lookup that had never worked

- **Five cases proved on live email**: approve, reject, correct with a category
  the Yunt never suggested, undo, and an approval phrase not on the first line.
  Nothing was written before a confirmation in any of them.
- **The proposal lookup had never once succeeded on live** (→ D-081). It matched
  Resend's API uuid against the RFC Message-ID a reply quotes. The earlier
  "Apply the Leasing change" success was a manual recovery script.
- **The client-facing reason printed the model's filler**, because the grounded
  precedent lost to whatever prose survived the internal-terms filter. It now
  leads with the precedent, which is what D-080 already required.
- **A category written as the Yunt prints it was rejected** — `EXP-2.6 Otros
  Gastos Salud Animal` matched neither code nor name alone.
- **Each fix carries a regression check verified to fail without it.** Two were
  proved by stashing the fix and re-running.
- **Gotcha — clicking Outlook's Send by coordinate silently saves a draft.**
  Cost four minutes polling for an email that never left. Click it by element
  ref; confirm it left by reading Sent Items, not by the compose window closing.
- **Gotcha — a wide `git add` swept the parked MCT-166 files into a feature
  commit.** Reverted in a follow-up and restored as uncommitted. Name the paths.
- **Gotcha — poll for a NEW row, not for the newest row to settle.** Three
  watchers exited immediately or timed out because the reply had already been
  answered before the watcher sampled its baseline.


### 2026-09-11 (c) — first live email chain, apply, and safe undo confirmation

- The Anthropic key and Vercel automation bypass are active; the current `yunt`
  branch deploys successfully and Resend reaches `/api/yunt/inbound`.
- The seven-line invoice archive was backed up, ingested and reviewed. It made
  four category proposals and two source-document flags.
- A natural `Apply the Leasing change.` produced a confirmation. `SÍ, ADELANTE`
  applied exactly one proposal and stored the complete before-state.
- The first approval exposed a lost-email-context defect. The Yunt now resolves
  the sealed action and target from its prior email before interpreting the reply.
- Afaq's `Undo that.` correctly selected the one application and produced a
  precise before/after confirmation; it is waiting for `SÍ, ADELANTE`.
- Client mail was shortened and grounded in prior accounting evidence. Internal
  confidence, model, UUID and database language is hidden (D-080).
- Resend sometimes returns HTTP 200 before it supplies an RFC Message-ID. The
  sender now retries that incomplete response; focused regression, the full
  frontend check and the free review chain pass. Frontend commit `7d8b632` is
  pushed, deployed Ready and the protected handler probe returns 405.
- Backup: `backups/supabase_20260911T093640Z`. Baseline: 5,195 invoices, 11,746
  lines, 461 companies, 4,002 catalog items, 78 categories, 0 purchase requests.
- Gotcha: HTTP 200 from Resend's detail endpoint does not mean its threading
  metadata is ready. A successful-looking response without `message_id` must be
  retried, never treated as final and never repaired by resending.

### 2026-09-11 (b) — step 0, and the four blockers it found before anything was spent

- **The whole review chain now runs free.** `scripts/check-yunt-review-chain.ts`
  takes six real DTEs through the real ingest and the real classifier, then
  staging, chunking, the submit guard, proposals, the findings email, the
  confirmation prompt and the apply/undo payloads, with a stub dispatcher and no
  API call. Eight deliberately bad answers go in and every one is refused.
  `DUMP_PACKET=1` writes the exact packet to `/tmp` to be read before sending.
- **It found a real bug.** The live classifier answered `429 Rate exceeded.` to
  a warm follow-up batch. `classify()` threw with no retry, the writer refuses
  to store lines with no category, and on the email path that is a reception
  report saying the attachment could not be read — nothing stored and no webhook
  redelivery coming. Now retried three times on 429 and 5xx, never on a 4xx,
  with `scripts/check-classifier-retry.ts` behind it.
- **Four deployment blockers, none of them visible from the code.** No model
  credential on Vercel; every deploy since 2026-09-10 rejected with
  `Edge Runtime is not supported in services`; Deployment Protection 401ing
  every request including Production, which is why the mailbox has never carried
  a message; and 18 unpushed commits. The middleware one is fixed here
  (`runtime: "nodejs"`), verified as far as local goes — the Edge function is
  gone from the build and a signed-out request still redirects to `/es/login`.
- **eve was giving the agent eleven tools nobody wrote**, including `bash`,
  `web_fetch` and `ask_question`. Turned off by decision (D-078).
- **Test 1 is prepared and verified without spending anything.**
  `scripts/91_make_yunt_test_zip.py` builds six COMPRAS documents, seven lines,
  fake RUT `77123456-7`, folios 999101-999106, ~928 tokens of packet. Three
  lines are ones where the client's own filing disagrees with the classifier
  (EXP-15.8, ADM-1.8, EXP-7.0), one carries a deliberate arithmetic error, one a
  junk name, one is a clean auto-accept control. `check-yunt-test-fixture.ts`
  reads it through the real pipeline against a read-only snapshot of live and
  asserts every one of those.
- **The undo was written before the write**, covers all three tests, and
  dry-runs clean against a baseline it snapshots itself
  (`scripts/90_yunt_live_test_undo.py`). Its purchasing anchor is
  `created_via = 'yunt'`, **not** `title like 'PRUEBA%'` — the Yunt drafts the
  title from the sender's own words, which is exactly how the 2026-09-10
  leftover survived the documented filter.
- **The precedent baseline reproduces exactly**, free and read-only: 97.2% of
  proposals correct, 2.76% confidently wrong, 400 held-out human-confirmed lines.
- **Decided:** direct Anthropic key rather than the gateway (→ D-077), eve's
  default tools off (→ D-078), the Python `yunt/` deleted (→ D-079).
- **Gotcha — a preview URL answering 401 is not a broken route.** Every
  deployment in this project sits behind Vercel SSO, so the webhook never
  arrived and nothing in the app ever ran. Probe the deployed URL before
  debugging the handler.
- **Gotcha — `scripts/` and `backups/` are gitignored in this repo.** The new
  undo script, the fixture generator and the baseline snapshot live on disk
  only, like `89_cleanup_mct155_test.py` before them.


### 2026-09-11 — everything that did not need the key, finished

- **Finished what the previous session was interrupted mid-air doing.** Codex had
  stopped while proving the authenticated `yunt_flags` read on localhost and its
  final checkpoint never landed, so `STATE.md` still claimed `024` was pending and
  `MCT-162` was deferred — both already false. Proved `024` live by behaviour and
  corrected the file.
- **`MCT-162` done and closed (D-072).** Direction now comes from the RUTs in the
  document; the folder is only a fallback. Measured first: across 5,584 raw DTEs
  Antillanca is on exactly one side of every one, and the RUT rule reproduces the
  folder on all 5,195 ingested documents with zero disagreements. D-010 was
  narrowed in the same commit rather than left standing.
- **Redeployed the classifier.** Revision `mlmodel-00015-mjr`. Same model bytes;
  what shipped was the code that already accepted `transport_plate`.
- **`MCT-155` done and closed.** A synthetic invoice with five deliberate problems
  and one clean control was written to live, its flags read and judged useful, and
  the batch removed with the counts verified back to baseline.
- **Switched the review to Sonnet 5 at `high` (D-076)**, and made the review chain
  drivable by a stub so the first run of it costs nothing.
- **Decided:** direction from the RUTs (→ D-072), `companies` holds counterparties
  only (→ D-073), "proveedores nuevos" counts what is new (→ D-074), a flag's
  sentence is interface not stored content (→ D-075), Sonnet 5 for review
  (→ D-076).
- **Gotcha — four failures today were invisible to every automated check**, and
  all four were found by driving a real screen. The classifier 422, the
  `yunt_flags` RLS refusal that silently skipped the *entire* post-write review,
  the doubled supplier count, and the untranslated flag text. `tsc`, lint and the
  check scripts passed throughout. Treat a green suite as evidence about the code
  and nothing else.
- **Gotcha — a swallowed error is invisible twice.** `reviewAfterWrite` never
  throws, by design (D-064), so the RLS refusal surfaced only in
  `.next/dev/logs/next-development.log`. When something that should have written
  rows wrote none and the screen looks happy, read that file before theorising.
- **Gotcha — do not stage upload fixtures in `public/`.** The dev server watches
  it, Fast Refresh reloads the page, and the file input is cleared before submit.
  Cost two silent no-op submits. Inline the base64 instead.

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
- **Linear corrected through its connector.** `MCT-163` and `MCT-167` are Done
  with proof comments. `MCT-166` was reopened to Backlog because its committed
  change did not meet its done-when. `MCT-155` now says flags report source-data
  problems and never rewrite DTE values (D-070), and `MCT-141` no longer claims
  the already-configured Resend mailbox/domain are blockers. `MCT-154` is
  Backlog, matching its parked-for-V2 title.
- **No other ticket can honestly close without the Claude key or user input.**
  `MCT-150` explicitly requires the real email approval and undo path;
  `MCT-152` needs a real stored question; `MCT-153` a real refusal; `MCT-155`
  migration `024` plus human judgement; and `MCT-141`/`160` a real message whose
  review/findings step uses Claude. A fresh five-table logical backup was taken
  at `backups/supabase_20260910T130219Z`, but no live write followed it.

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
