# STATE — where this project is right now

Updated every session. Last 5 sessions only; anything older that still matters
lives in `DECISIONS.md`.

## Now

**The chain is half connected.** `/carga` now reads a ZIP, shows exactly what
would be stored, and stores it only when the person clicks a second time; the
batch is claimed by a hash of the archive, so the same ZIP twice is a no-op. The
mailbox splits structurally — a ZIP goes to deterministic ingest, and any other
message is recorded as an inbound request and handed to the agent, which answers
through `reply_to_email` with the recipient read from the stored row.

**What is still disconnected:** the mailbox does not call the writer, and
nothing calls `stageReviewAttempt`, so no write yet triggers a review. The
review layer, its three EVE tools, the dispatcher and the findings outbox are
all built and proved, and all still unreached in production.

**Migrations `005` through `010` are live.** Afaq ran them on 2026-09-09.
`011`, `012` and `013` are written, proved against a disposable PostgreSQL, and
**have not run**.

**Branch `yunt` is pushed only through `4035fef`; fourteen commits are local.**
Preview only. Production is still `main`; nothing merged. `yunt-backend` here is
unpushed.

## Doing now

**The spine is connected.** An invoice can now travel the whole way in code:
arrive by email or upload, be stored atomically, and start a grounded review
that mails its findings back. Nothing has run against live data yet.

Next: **item 8, apply-on-approval with undo.** Every path now ends in a proposal
and there is no way to accept one, which makes items 6 and 7 read-only advice.

## What the Yunt promises, and what it does today

The 19 numbered items are the scope sent to the team, in the client's own
words (`docs/Yunt_scope_v1.docx`). Where that document and `DECISIONS.md`
disagree on *how*, the decision log wins (D-059) — but this list is what
Antillanca was told they are getting, so it is the honest measure of progress.

**9 of 19 done, 3 partly, 7 not started.**

| # | What Cristian was promised | Today |
|---|---|---|
| 1 | A mailbox that acts only on agreed senders | Done. Never carried a real message |
| 2 | A ZIP of SII XML, COMPRAS and VENTAS inside | Done |
| 3 | Duplicate detection on RUT + type + folio; sending twice changes nothing | Done |
| 4 | Lines classified and **written to the database** | Done in code, both doors. Never yet run against live data |
| 5 | An acknowledgement in minutes, then a written report | Partly. One email carries both; the fast acknowledgement is not separate |
| 6 | Data quality flags, and fixes proposed on approval | Not started |
| 7 | Category proposals with evidence, grouped | Partly. Built, grounded, and now triggered by every write. Accuracy still unmeasured |
| 8 | Approve a group, get a confirmation, undo it | Not started. **This is the gap that makes 6 and 7 unusable** |
| 9 | Five query tools answering open questions | Not started |
| 10 | Figure in the body, list as spreadsheet, report as PDF, filter printed on top | Not started. Plain-text replies only |
| 11 | Charts from a fixed set, drawn by code | Not started |
| 12 | Says so when a question does not fit, and we learn from the list | Partly. The agent is told to refuse; no `yunt_refusals` log |
| 13 | Month-end summary, post-batch digest, weekly review list | Not started |
| 14 | Form one: what is needed, how much, by when, for which farm | Done. Tables live, not yet used in anger |
| 15 | A request stays open until an order closes it | Done. Enforced in the database |
| 16 | Form two, with the two-quotation rule above CLP 500,000 | Done. Rule proved by regression |
| 17 | A purchase-order PDF Antillanca sends themselves | Partly. A print-styled page; the browser saves the PDF. Cannot be attached to mail |
| 18 | The Yunt fills form one from a plain-language email | Not started |
| 19 | The Yunt drafts the order once a quotation exists | Not started |

**Read the middle column, not the count.** Items 1-5 and 14-17 are the parts
that work without a language model, and they are the ones that are done. Every
item where the Yunt is supposed to *think* — 6 to 13, 18, 19 — is either
unstarted or built-but-unreachable. The product today is a good deterministic
pipeline with an agent bolted on that nothing calls.

**The single most valuable next thing is item 8.** Items 6 and 7 both end in a
proposal, and there is no way to accept one. Until apply-with-undo exists, every
finding the Yunt produces is a message Cristian can read and not act on.

## V1 checklist

Every box that must be ticked for a working v1. Updated as work lands — if a box
is unticked, there is no code for it. "Built" means proved by a regression;
"live" means the migration has run in Supabase.

### The spine — invoices in, stored, reviewed

- [x] Deploy path, Resend mailbox, ZIP upload page (Phases 0–1)
- [x] Read, deduplicate, resolve to catalog, classify, report (Phases 2–2.5)
- [x] Atomic writer: whole invoice and all its lines in one transaction (D-063)
- [x] Writer connected to `/carga`, dry run first, save on a second click
- [x] Mailbox router: ZIP → deterministic ingest, everything else → the agent
- [x] **Mailbox connected to the writer** — claimed by the Resend message id
- [x] **Review fires after a write**, from both doors, and never blocks the
      reception email (D-064)
- [ ] First real write, against a backup, with Afaq's yes on the day

### The review loop

- [x] Durable review state, packets, atomic completion (`009`–`011`)
- [x] Three grounded EVE tools: load, precedent, submit
- [x] Findings-email outbox: sends only when findings exist (`012`, D-065)
- [x] OIDC-secured, idempotent dispatch to EVE
- [x] **Pinned to `anthropic/claude-opus-5`** in `agent/agent.ts`, reasoning
      `medium`. Without that file eve ran its own GPT default
- [ ] Proof run: 200 known review rows, counting the confidently-wrong (Phase 5)

### Talking to Cristian

- [x] Inbound requests recorded and threaded by `In-Reply-To` (`013`)
- [x] `reply_to_email` — recipient read from the row, one reply per request
- [ ] **Five query tools + the canonical money view** (Phase 7, D-053)
- [ ] Answer delivery: figure in the body, list as `.xlsx`, report as PDF
- [ ] Refusal path and `yunt_refusals`, which is the backlog for what to add
- [ ] Restate-then-confirm before any action the person agreed to in prose

### Acting, with a way back

- [ ] **`apply_proposal(proposal_id, nonce)`** — sealed targets, no row list
      from the caller (Phase 6)
- [ ] **`yunt_applications`: prior values stored, undo is a per-row replay**
- [ ] Data-quality flags, all seven checks; a flagged `auto_accept` is
      downgraded to review and nothing else (Phase 4, D-058, D1)

### Purchasing

- [x] The two forms, real tables (`005` live) — not yet exercised live
- [ ] The Yunt fills them from an email, with precedent prices from the
      price-history tool (Phase 10)
- [ ] The CLP 500,000 two-quotation check called from the same function the
      form uses, never a second copy

### Waiting on Afaq

- [ ] **Run `011`, `012`, `013`** in the Supabase editor — all idempotent
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

### 2026-09-08 - Yunt scope agreed and sent; Audisoft API tested and blocked

- **Wrote the scope Afaq sent to the team**, `docs/Yunt_scope_v1.docx`, nineteen
  numbered items in four sections. Also `docs/YUNT_REQUIREMENTS.md` (long-form
  reference) and `docs/Yunt_scope_v1.pdf` (earlier prose version).
- **Decided:** D-051 ingestion is deterministic code, the agent only where
  judgement is; D-052 purchase orders v1 is two forms with no roles and no
  approval; D-053 open questions are answered by about five parameterised query
  tools with every number computed by code; D-054 the Audisoft API is the
  intended source with email as fallback.
- **Established what a purchase order is and how it fits.** Afaq did not know
  the domain and asked directly. The dashboard already contains the whole
  seven-phase procurement flow as non-functional demo screens with a
  `DemoBanner`, so this is completing a storyboard rather than designing one.
  The OC carries the accounting category *before* the money is spent, which is
  why it belongs in this product rather than a separate one.
- **Tested the Audisoft API without documentation.** ~13 calls. The URLs in
  Lautaro's email are truncated with dots. Findings: no path segments returns
  **500** with `Connection: close`; any path segments return **401** with
  `keep-alive`, byte-identical across RUT alone, RUT+token, token+RUT, with and
  without the verifier digit, with a period added, and with the token as an
  `Authorization` or bare `token` header. Query strings never worked. No
  `WWW-Authenticate` header, so the server never says what it wants. Stopped
  rather than keep guessing, since clause 6.2 permits revocation without notice.
- **Afaq's correction, and it was right: the decision log was applied where it
  does not belong.** D-048, D-041 and D-001 were surfaced as binding constraints
  on a greenfield agent feature. They were made during the labelling job and
  govern that pipeline, not a new product. He said the project is "polluted by
  so many side notes" and asked to look only at what is implemented, the
  dashboard and the ML model, plus what needs building.
- **Afaq's correction, and it was right: the agent was in the ingestion path for
  no reason.** His words: why do we need a unit to take an email and hit an
  endpoint when deterministic code can do it? Nothing in that path is a
  judgement call. Became D-051, and it makes ingestion shippable standalone.
- **Gotcha - the DTE XML is ISO-8859-1 with no XML declaration.** Verified:
  `file -I` reports `iso-8859-1`, and `ORDENA` stores the enye as the single
  byte `0xD1`, which is Latin-1, not the `C3 91` UTF-8 would use. **No file in
  the dataset carries an `encoding=` declaration**, and the XML spec says a
  parser must then assume UTF-8. So a standards-compliant parser reads these
  files wrong on every accented character. `scripts/10_extract_line_items.py`
  already handles it at lines 85-87, try UTF-8 then fall back to latin-1. Any
  new reader for the API pull needs the same.
- **Gotcha - the frontend's XML extractor silently drops every line item.**
  `src/lib/extractor/xml-parser.ts` is a generic XML-to-table explorer that
  knows nothing about DTE. On a DTE file `findRepeatingElements` finds no
  repeats under `<DTE>` (one `<Documento>`), falls to `flattenNode`, which has
  an **empty** `if (elements.length > 1) {}` branch - so both `<Detalle>` blocks
  are discarded and only the header and totals come back, with no error. Same
  class as the pagination trap: valid response, quietly incomplete.
- **Gotcha - overstated a technical claim and had to walk it back.** Said the
  extractor "can't be used server-side" because of `DOMParser`, `atob`, `File`
  and `webkitRelativePath`. `atob` exists in Node 16+ and `File` in Node 20+;
  only `DOMParser` genuinely does not exist in Node or the Edge runtime. The
  runtime was never the real objection anyway - the parser is simply wrong for
  DTE. **Leading with the weaker argument invited a correct challenge.**
- **Afaq's feedback, saved to memory as `menu-not-recipe`:** anything shown
  upward is a menu of deliverables, never a numbered recipe of build steps.
  Consolidating means fewer lines than the draft, not a re-grouping of the same
  ones.
