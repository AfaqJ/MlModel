# STATE — where this project is right now

Updated every session. Last 5 sessions only; anything older that still matters
lives in `DECISIONS.md`.

## Now

**The Yunt has two working ways in and still writes nothing.** A person can
upload a ZIP at `/carga` in the dashboard, or Cristian can email
`antillanca.yunt@mountaincreative.cl`; both run the same `runIngest` — read,
deduplicate against live, resolve to the catalog, classify — and both print the
same reception report. Neither stores anything.

**The mailbox is wired end to end but has never carried a message.** Resend
webhook created and enabled on the `yunt` preview URL, signing secret rotated,
Vercel bypass secret in the URL, and all six environment variables on Vercel
Preview: `RESEND_API_KEY`, `RESEND_WEBHOOK_SECRET`, `SUPABASE_SECRET_KEY`,
`CLASSIFIER_URL`, `YUNT_INBOUND_ADDRESS`, `YUNT_MAIL_FROM`.
**`YUNT_ALLOWED_ADDRESSES` is deliberately unset, so the Yunt can mail nobody.**
No deployment has been made since the variables landed, so nothing has run with
them yet.

**Branch `yunt` is pushed** (`4035fef`), preview only. Production is still
`main`; nothing has been merged. `yunt-backend` here is unpushed.

**Nothing has been written to the database, and the two SQL files are still
unrun.**

## Next

1. **Send the first real email** to `antillanca.yunt@mountaincreative.cl` with a
   ZIP attached, after a redeploy (environment variables are baked in at build
   time, so the preview must be rebuilt since they landed). Success looks like
   `[yunt] processed an inbound message; reply mail_not_configured` in the
   Vercel logs — the reply is refused because the allowlist is empty, which is
   correct.
2. **Run two SQL files in the Supabase editor** — `milk-company/supabase/005_purchase_orders.sql`
   (the purchase-order screens do not work until this runs) and
   `006_alias_provenance.sql` (must precede any bulk alias load, or an alias
   Afaq approved becomes indistinguishable from one the machine proposed). Both
   idempotent.
3. **Write the ingest → Supabase writer** (MCT-146). First live write in this
   workstream: backup, dry run, and Afaq's yes on the day. Everything upstream
   of it is built and measured.
4. **Apply the 222 harvested aliases** after step 2. Backup, dry run, scoped
   PostgREST write. The apply script is deliberately unwritten until it is run
   (D-046's lesson).
5. **Fix the `Confeccion de Bolos` duplicate** — three catalog rows for one
   service, 14 lines. Afaq approved the fix *and* folding accents in the
   normaliser so the pair cannot recur. Needs a backup and a dry run.
6. **Scaffold eve** (`npx eve@latest init`) in `../milk-company`, then the
   category-proposal tool. Unknown: whether eve's `needsApproval` pause can be
   driven by an email reply, or whether that approval is wired by hand.
7. **387 documents whose lines disagree with their own header**, CLP 21,189,814
   overstated — see `docs/CLIENT_DATA_ISSUES.md` §1. Needs a decision on the
   stored rows and a question to the client.
8. **Remove the bypass secret from the webhook URL when this merges to
   production** (D-062). Production is not behind the auth wall, so the query
   string becomes a credential sitting in Resend's config for no reason.
9. **Everything still waiting on Afaq** is in `docs/YUNT_OPEN_DECISIONS.md`:
   Cristian's address for the allowlist, and whether `mountaincreative.cl` is
   verified for *sending* as well as receiving.

The older frontend and labelling items below are unchanged and still open.

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

### 2026-09-06 — Milk Yunt designed from scratch; nothing decided

- Afaq rejected the previous session's design wholesale, including its "settled,
  do not reopen" list — a list of closed questions written by the session whose
  judgement was in question. Reframed the Yunt as a **digital collaborator**
  (he talks to it as he talks to Claude Code), not a query box bounded by email.
- Wrote `docs/MILK_YUNT_PLAN.md`. Deleted `MILK_YUNT_DESIGN.md`,
  `MILK_YUNT_IMPLEMENTATION_PLAN.md` and `MILK_YUNT_HANDOVER.md` after folding
  forward the six failure modes and Afaq's stated requirements. None were
  tracked in git, so a session-local copy was kept in the scratchpad only.
- **Two adversarial Codex rounds** (read-only, `--sandbox read-only`). It
  conceded all three pushbacks: float64 is exact for CLP (max line
  CLP 642,482,021, total CLP 12,062,944,437, far under 2^53); multi-tenant
  machinery is over-engineering for one client and one approver; the
  "no E2E without inbound email" objection was a strawman.
- **Gotcha — the write path was genuinely wrong.** The first design had the
  agent pass `expected_row_versions[]` into the apply call. That is not
  authorization: after approval the agent could fetch fresh versions and pass
  those, and a drifted write would succeed. Fix: the proposal is **sealed**,
  carries the target rows and their expected revisions inside itself, and the
  RPC accepts only `(proposal_id, nonce)`. Nothing version-shaped comes from
  the caller.
- **Gotcha — figure placeholders are not enough.** Given a value and a
  `{{fig:3}}` slot, a model writes "`{{fig:3}}`, casi el doble": correct number,
  invented comparison. In rendered output the model gets figure IDs and never
  values; in conversation it sees values but every numeric claim is checked
  against the receipts before send.
- **Process gotcha, cost real time:** Codex said "fix the money semantics
  before extracting anything" and this session turned a *data* dependency into
  a *build* blocker. Afaq called it out. The data defects change whether an
  **answer** is right, not whether the **design** is right. Resolution: every
  figure is read through one canonical Postgres view, so the fixes land on
  Afaq's timeline without touching the agent.
- Restructured the plan into **vertical phases** at Afaq's request — each phase
  ends with something that runs, rather than seven days of layers where nothing
  works until the end. Phase 1 is two tools and a receipt.
- **Decided:** nothing. Every item is a proposal awaiting his approval.

### 2026-09-04 — client reply and exact bale categorisation list prepared

- Distinguished Cristian's answers from the quoted outgoing email. His "If I
  had the list" sentence refers specifically to the 18 ambiguous bale-making
  invoice lines; it does not ask for a contractor list.
- Built and visually checked the client workbook with exactly 18 rows and CLP
  56,581,822. The editable yellow column offers Bolos Silo, Bolos Heno, or Other,
  and every row retains its invoice identifiers for a safe return import.
- Confirmed the earlier client answers were already applied: 524 plumbing, 25
  GEA technician-hour and 43 commission rows, 592 total, with `ADM-3.1` created.
- Confirmed the category-assignment code is in the branch used by the live
  production deployment. Browser verification reached the production login;
  an authenticated press of Done remains untested.
- **Gotcha — there are two different offers to categorise in the reply.** The
  construction section says to send doubts, while the quoted "If I had the
  list" appears in the bale section. Treating both as one contractor-list
  request would send the wrong evidence.
