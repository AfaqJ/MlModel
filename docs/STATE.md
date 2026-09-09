# STATE — where this project is right now

Updated every session. Last 5 sessions only; anything older that still matters
lives in `DECISIONS.md`.

## Now

**The full write→review chain is connected in local code, not proved live.** A
ZIP sent by email uses the service-role database client, writes deterministic
facts, sends the receipt, then starts the compact Yunt review. A non-ZIP email
is stored and handed to EVE. No real message has traversed either path.

**`/carga` is currently blocked at its first real save.** It correctly uses the
signed-in user's Supabase client, but `yunt_batches` and the writer/review RPCs
grant only `service_role`; no authenticated policy exists. The page can preview,
but calling the live write should fail. Do not hide this by importing the secret
service client into a browser-triggered action. The proposed production fix is
a database-backed Yunt operator allowlist, initially Afaq and later Cristian;
Afaq has not approved that permission design yet.

**The review/apply foundation and three of five business query tools are built locally.**
Review packets, grounded evidence, findings email, retryable inbound requests,
apply/undo, bounded item price history, category precedent, filtered invoice-line
lists, and a durable refusal backlog all have regressions. `014` writes
`prediction_source='yunt_applied'` (D-066).
The aggregate and period-comparison tools, seven
data-quality checks, exports/charts/reports, recurring reports, and Yunt-driven
purchasing are still to build.

**Migrations `005`–`010` are live. `011`–`017` are not.** Afaq confirmed the
live boundary; every pending migration has been loaded twice in disposable
PostgreSQL. Supabase currently reports **EXCEEDING USAGE LIMITS**, so no live
write or migration should be attempted until the project serves requests again.

**Branch `yunt` is pushed only through `4035fef`; twenty-three commits are local**
through `7e14e7f`. Preview only. Production remains `main`; nothing merged.
`yunt-backend` here is also unpushed.

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
- `004` through `010` are applied. `011` through `017` are not.
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

### What to run, and why

**Migrations `011` through `017`, in that order, in one paste.**
A combined file was generated and handed to Afaq. Regenerate it with:

```
cat milk-company/supabase/{011_yunt_review_chunks,012_yunt_review_outbox,013_yunt_inbound_requests,014_yunt_apply_undo,015_yunt_price_history,016_yunt_invoice_line_list,017_yunt_refusals}.sql
```

- `011` — review packets, so a retry cannot double-count findings
- `012` — findings-email outbox; a clean review sends nothing, one sender only
- `013` — inbound requests, stored before the agent sees them, threaded by `In-Reply-To`
- `014` — apply-on-approval and undo; sealed rows, stale proposals refused
- `015` — bounded catalog lookup and item price history; ambiguous names are not guessed
- `016` — bounded invoice-line list with exact review/date/amount filters
- `017` — immutable refusal/backlog entries, one per stored inbound request

Why it is safe: there is no `DELETE`, `TRUNCATE`, `DROP TABLE`, or top-level
data `UPDATE`. `014` deliberately replaces the existing
`invoice_items_prediction_source_allowed` constraint so it can add
`yunt_applied`; it does not rewrite existing rows. `012` drops and immediately
re-creates its own outbox trigger. `015` creates read-only functions. Supabase
may warn because those two expected `DROP` statements are present; read their
exact targets before confirming.

Proof: `milk-company/scripts/prove-011-to-014.sh` loads `008`->`014` in order on
a disposable PostgreSQL, re-runs `011`->`014` for idempotency, and exercises
`013`'s round trip. `scripts/prove-014-apply-undo.sh` proves apply/undo;
`scripts/prove-015-price-history.sh` proves filters, ambiguity and idempotency;
`scripts/prove-016-invoice-line-list.sh` proves bounded row filters;
`scripts/prove-017-yunt-refusals.sh` proves refusal logging and replay safety.
All are committed and re-runnable.

**Take a backup first** (`scripts/81_backup_supabase.py`). The last one is
2026-09-03, and the next thing after these migrations is the first real write.

### Open, needing Afaq

1. **Who may use `/carga`.** Recommendation: a database-backed Yunt operator
   allowlist seeded with Afaq's signed-in email and extended with Cristian later.
2. **Claude model choice.** Claude pinned Opus 5 / medium from a cost estimate;
   Afaq has not explicitly ratified that choice.
3. **Your yes on the 222 harvested aliases** — `006` is live, so this is unblocked.
4. **The Supabase org shows "Grace period is over" and the project is flagged
   EXCEEDING USAGE LIMITS.** That stops the project serving requests. It needs
   handling before any real write.

## What the Yunt promises, and what it does today

The 19 numbered items are the scope sent to the team, in the client's own
words (`docs/Yunt_scope_v1.docx`). Where that document and `DECISIONS.md`
disagree on *how*, the decision log wins (D-059) — but this list is what
Antillanca was told they are getting, so it is the honest measure of progress.

**9 of 19 done in code, 3 partly, 7 not started. Nothing agentic is live yet.**

| # | What Cristian was promised | Today |
|---|---|---|
| 1 | A mailbox that acts only on agreed senders | Done. Never carried a real message |
| 3 | Duplicate detection on RUT + type + folio; sending twice changes nothing | Done |
| 4 | Lines classified and **written to the database** | Partly. Email is connected in code; `/carga` is blocked by missing authenticated permissions; neither is live-proved |
| 5 | An acknowledgement in minutes, then a written report | Done in code as a receipt first and a findings email later; never live-proved |
| 6 | Data quality flags, and fixes proposed on approval | Not started |
| 7 | Category proposals with evidence, grouped | Partly. Built, grounded, and now triggered by every write. Accuracy still unmeasured |
| 8 | Approve a group, get a confirmation, undo it | Done in code. The confirmation is the database's own words, not the model's |
| 9 | Five query tools answering open questions | Partly. Price history, category precedent and row listing are built; aggregate and period comparison remain |
| 10 | Figure in the body, list as spreadsheet, report as PDF, filter printed on top | Not started. Plain-text replies only |
| 11 | Charts from a fixed set, drawn by code | Not started |
| 12 | Says so when a question does not fit, and we learn from the list | Done in code. One immutable backlog entry per stored request; not live until `017` runs |
| 13 | Month-end summary, post-batch digest, weekly review list | Not started |
| 14 | Form one: what is needed, how much, by when, for which farm | Done. Tables live, not yet used in anger |
| 15 | A request stays open until an order closes it | Done. Enforced in the database |
| 16 | Form two, with the two-quotation rule above CLP 500,000 | Done. Rule proved by regression |
| 17 | A purchase-order PDF Antillanca sends themselves | Partly. A print-styled page; the browser saves the PDF. Cannot be attached to mail |
| 18 | The Yunt fills form one from a plain-language email | Not started |
| 19 | The Yunt drafts the order once a quotation exists | Not started |

**Read the middle column, not the count.** The deterministic base is farthest
along. The EVE review and action tools are now called by the email path in code,
but their migrations, model credentials and real-message proof are still open.

**The next foundation priority is permission, not another feature:** make
`/carga` a real authenticated write without exposing service-role power, clear
the Supabase usage block, run `011`–`017`, then prove one real email and one
upload including replay. In parallel, finish the remaining four read tools.

## V1 checklist

Every box that must be ticked for a working v1. Updated as work lands — if a box
is unticked, there is no code for it. "Built" means proved by a regression;
"live" means the migration has run in Supabase.

### The spine — invoices in, stored, reviewed

- [x] Deploy path, Resend mailbox, ZIP upload page (Phases 0–1)
- [x] Read, deduplicate, resolve to catalog, classify, report (Phases 2–2.5)
- [x] Atomic writer: whole invoice and all its lines in one transaction (D-063)
- [ ] `/carga` live save: source is connected, but authenticated writer/review
      permission is missing
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
- [x] **Temporarily pinned to `anthropic/claude-opus-5`** in `agent/agent.ts`,
      reasoning `medium`; Afaq still needs to ratify the model/cost choice
- [ ] Proof run: 200 known review rows, counting the confidently-wrong (Phase 5)

### Talking to Cristian

- [x] Inbound requests recorded and threaded by `In-Reply-To` (`013`)
- [x] `reply_to_email` — recipient read from the row, one reply per request
- [ ] **Five query tools + the canonical money view** (Phase 7, D-053): item
      3/5 are proved; aggregate and period comparison remain
- [ ] Answer delivery: figure in the body, list as `.xlsx`, report as PDF
- [x] Refusal path and `yunt_refusals`, one immutable backlog row per request
- [ ] Restate-then-confirm before any action the person agreed to in prose

### Acting, with a way back

- [x] **`apply_proposal`** — sealed targets, no row list from the caller, stale
      proposals refused because a person's later edit wins (Phase 6)
- [x] **`yunt_applications`: prior values stored, undo is a per-row replay** —
      `decision` and `reviewed` come back too
- [ ] Data-quality flags, all seven checks; a flagged `auto_accept` is
      downgraded to review and nothing else (Phase 4, D-058, D1)

### Purchasing

- [x] The two forms, real tables (`005` live) — not yet exercised live
- [ ] The Yunt fills them from an email, with precedent prices from the
      price-history tool (Phase 10)
- [ ] The CLP 500,000 two-quotation check called from the same function the
      form uses, never a second copy

### Waiting on Afaq

- [ ] Clear Supabase's **EXCEEDING USAGE LIMITS** state
- [ ] Approve the `/carga` operator permission design
- [ ] Confirm or change the temporary Opus 5 / medium choice
- [ ] **Run `011`–`017`** in the Supabase editor — all idempotent, each proved
      twice against a disposable PostgreSQL
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
- **Proof:** `014` apply/undo and `015` price history each loaded twice and passed
  behavioral PostgreSQL checks; `016` and `017` passed the same load-twice and
  behavior proof. After every increment, `./check.sh` was all green
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

### 2026-09-09 — the read path built, then ported to TypeScript; eve decided

- **Built the whole ingestion read path in Python, then ported it** to
  `../milk-company/src/lib/ingest/` once Afaq settled that the Yunt is an eve
  agent in Next.js (D-055). Parser, archive reader, catalog resolver, classifier
  call. **Verified by equality:** same 4,451 files, same 4,451 documents, 10,620
  lines, 158 rescaled, 50 non-reconciling, same type breakdown.
- **Four measured rules for reading a DTE (D-056)**, none from the SII spec.
  Non-reconciling lines went from 10.9% to **0.47%**. This corrects
  `AUTOMATION_PLAN` A-3: the `GASOLINA 93` bug was never the decimal separator,
  it is one supplier scaling quantity and price by 10^4 on some lines.
- **Catalog resolver, six tiers.** 81.3% of all 11,746 lines resolve with no
  person, and the only disagreements are one product that exists three times.
- **222 aliases harvested** from assignments the migration already made (D-057).
  78.8% → 86.2%, zero new disagreements. Nothing written.
- **Purchase orders made real** — three tables, two forms, a numbered PDF. The
  CLP 500,000 rule lives in a database function with no insert policy on
  `purchase_orders`, so it cannot be sidestepped and the Yunt reuses the same
  check rather than a second copy in another language.
- **`check.sh` in both repos**, run at every checkpoint at Afaq's instruction.
  Lint is a ratchet against the pre-existing 12 errors, not a gate that would
  fail forever.
- **Decided:** D-055 (eve in Next.js), D-056 (the four DTE rules), D-057 (alias
  is an observation, pattern is a rule).
- **Gotcha — scaling per supplier broke 2,196 lines that were already correct.**
  The same supplier writes scaled and plain values on the same invoice. The fix
  is per-line: arithmetic decides *whether* to rescale, the table only supplies
  the split. A wrong table entry can no longer corrupt a correct line.
- **Gotcha — fuzzy matching proposed confidently wrong merges.** `UNION HDPE 50
  X 1,1/2HE` onto `…1,1/2HI`, `VIAJE 32 VACAS` onto `Viaje De 38 Vacas`.
  Different fittings, a different lorryload of cows, each plausible enough to be
  ticked through. Requiring every digit-carrying token to match exactly took
  fuzzy from 805 matches to 15.
- **Gotcha — a comment that contradicted its own code.** The purchase-order SQL
  claimed orders could only be created through the function while also granting
  an insert policy that made it false. Same class as `EVIDENCE_RULES` §11. Fixed
  by making the code true, which meant `security definer` with a pinned
  `search_path`.
- **Gotcha — a test that passed for the wrong reason.** The path-traversal check
  passed because JSZip normalises `..` away when it *writes* an archive, so that
  case cannot be built with it at all. Now tested on the predicate directly.
- **Gotcha — `check.sh` used a hand-written ignore list and it had already
  rotted.** Two new test files were being collected by the wrong venv, so the
  classifier step reported 116 tests. It is a glob now.
- **Afaq's correction, and it was right: C-8 was cited where it does not apply.**
  It governs *category* rules, which are claims about Antillanca's business
  practice. A catalog pattern is a claim about whether two strings name the same
  product, which the data settles. No client confirmation needed.
- **Afaq's correction, and it was right: the reconciliation rule is inferred.**
  Asked whether it was code or data, and whether the rule was sound or made
  normal data look wrong. It is inferred — measured, never read from the spec.
  That produced `docs/CLIENT_DATA_ISSUES.md` and a constraint that a check may
  only ever flag, never change a value or block an ingest, and that a missing
  field is normal rather than an error.
- **Found while answering that: 387 documents whose lines overstate their own
  header by CLP 21,189,814.** One electricity invoice worth CLP 1,261 carries a
  line claiming CLP 1,011,311 — a meter reading in the amount column. Per-category
  spend on the dashboard is inflated by that today.
- **Afaq's correction on Linear: tickets were being made for side tasks.** A
  database migration and a one-line count fix are how work gets done, not work
  anyone needs on a board.
