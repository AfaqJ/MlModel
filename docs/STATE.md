# STATE — where this project is right now

Updated every session. Last 5 sessions only; anything older that still matters
lives in `DECISIONS.md`.

## Now

**The Yunt workstream now has a scope Afaq has sent to the team, and four
decisions behind it (D-051 to D-054).** The document he actually sent is
`docs/Yunt_scope_v1.docx`, nineteen numbered items across four sections.
`docs/YUNT_REQUIREMENTS.md` is the long-form reference behind it and is marked
partly superseded, with its three out-of-date sections named in its own header.
`docs/MILK_YUNT_PLAN.md` was **deleted** on 2026-09-08 with Afaq's approval.

**The recipe now exists:** `docs/YUNT_IMPLEMENTATION_PLAN.md` on branch
`feature/yunt`, eleven phases. Six decisions settled that session, one withdrawn.

**Afaq's correction, and it was right twice.** First, the `D-NNN` log was
treated as binding on a greenfield feature; those decisions came from the
labelling job and do not govern a new agent. Second, ingestion was designed with
the agent inside it for no reason - there is no judgement in the path, so it is
plain code (D-051).

**The Audisoft API was tested and does not authenticate.** Rodrigo wants
ingestion from the API rather than email. Endpoints reach real code but every
credential form returns an identical 401. Blocker message is drafted and Afaq
has sent it. Email ingestion continues as the fallback (D-054).

**MCT-37 itself is unchanged.** No Supabase writes, no backup, no model work, no
deploy. Live `mlmodel-00014-lrp` untouched. Tracked changes this session are
`docs/DECISIONS.md`, `docs/STATE.md` and `CLAUDE.md`; the four Yunt files are
untracked.

## Next

1. **Write the implementation plan for the Yunt scope.** Afaq asked for this
   explicitly in a fresh session: the recipe behind
   `docs/Yunt_scope_v1.docx`, all nineteen items. Read that docx, D-051 to
   D-054, and the API findings below before starting.
2. **Chase Audisoft for a working API call.** Nothing can be built against it
   until they answer. Questions are in the sent message: one complete example
   URL, how the token is transmitted, the date or period parameter, pagination,
   whether the 19 June token is still active and whether access is IP
   restricted. Also whether an HTTPS address or domain name exists, and written
   confirmation that storing extracted lines is within clause 3.4.
3. **The asks removed from the sent doc are recorded nowhere the team sees.**
   Afaq deleted the "What we need from Antillanca" section: allowed sender
   addresses, confirmation of the CLP 500,000 two-quotation rule, and the
   July-August 2026 categorised invoices Antillanca offered and nobody
   collected. That last one is still the highest-value input available.
4. **Say GO on `docs/YUNT_IMPLEMENTATION_PLAN.md`.** Phase 0 is half a day and
   proves the deploy path while it is still empty. Still needed from Afaq:
   Cristian's address, the receiving domain, the Resend and Claude keys.
5. **`src/lib/extractor/xml-parser.ts` in the frontend silently drops repeated
   elements.** `flattenNode` has an empty `if (elements.length > 1) {}` branch,
   so on a DTE file every `<Detalle>` is discarded and only the header and
   totals survive, with no error. It is a manual inspection tool, not the
   ingestion parser, but it is wrong for the files it is pointed at.
6. **Press Done on one line in the dashboard.** Unchanged, still the only
   unproven link in D-048. Ten seconds.
7. **Answer the credit-note question.** 103 invoices of `document_type = '61'`,
   CLP 87,885,532, all stored positive, so totals count a purchase and its
   cancellation as two purchases. The `Referencia` block was never loaded, so
   netting needs a re-read of the raw XML. Options in
   `OPEN_QUESTIONS_2026_09_03.md` section 1.
8. **Ask the client about `document_type = '43'`** - 29 liquidacion facturas,
   CLP 292,085,987, all Feria Ganaderos Osorno. If the underlying sale is
   already present as a type 33, these double-count.
9. **Ask Salman why the Risk tab was disabled.** It arrived commented out in
   `7d9ae21` with no recorded reason. With D-049 applied, Overview says "36
   critical anomalies need attention" with nowhere to click.
10. **Decide the IVA split** (`OPEN_QUESTIONS` section 3). The Tax Breakdown card
    adds IVA credito to IVA debito under one label. Needs the accountant.
11. **`ADM-3.1` has zero training rows.** Before any retrain it must be marked
    rule-assigned and untrainable the way D-028's six are.
12. **Honorarios and Remuneraciones have never been audited** - keyword probes,
    not audited sets (`CLIENT_CONVENTIONS.md` section 10).
13. **Three defects in `milk-company/src/lib/analytics/`**, verified in code:
    - `aggregate.ts:88-90` - `totalRevenue` sums COMPRAS **and** VENTAS;
      `avgInvoiceValue` (`:122`) divides that combined figure.
    - `types.ts:194` requires `final_categories_id && final_code`;
      `item_summary.sql:35-37` checks only the id.
    - `aggregate.ts:104-107` counts `decision='auto_accept'`, which
      `productos/actions.ts:76` sets on a **human** pick, so the auto-accept
      rate and the 67% figure in `CLAUDE.md` are contaminated.
14. **Frontend, still open:** horizontal scrolling on the KPI tiles; the
    Geografia Pareto panel measures geography rather than risk; keyset
    pagination on the catalog is deferred - **search must move server-side in
    the same change or it silently starts matching only loaded pages.**

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
