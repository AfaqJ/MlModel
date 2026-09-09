# STATE — where this project is right now

Updated every session. Last 5 sessions only; anything older that still matters
lives in `DECISIONS.md`.

## Now

**The Yunt's whole read path is built and ported, and nothing has been written
to the database.** Reading a ZIP of SII invoices, parsing them, deduplicating,
matching lines to the catalog and calling the classifier all work end to end,
in TypeScript, in `../milk-company/src/lib/ingest/`. The purchasing forms are
built. Eight regression checks pass in the dashboard, 146 tests here.

**The Yunt is an eve agent in Next.js on Vercel, not a Python service** (D-055).
GCloud keeps only the classifier. `yunt/` here is the reference implementation
and is deleted once the last piece is ported — Afaq's instruction, since git is
the archive.

**Branches, nothing pushed:** `yunt-backend` here, `yunt` in `../milk-company`.

**Every number in the port was verified by equality, not inspection.** The same
4,451 files give 4,451 documents, 10,620 lines, 158 rescaled, 50 non-reconciling
— identical to the Python, asserted as exact equalities.

**Linear:** new project `Antillanca - Yunt and purchasing`, eight issues,
MCT-139 to MCT-146 and MCT-148.

## Next

1. **Run two SQL files in the Supabase editor** — `milk-company/supabase/005_purchase_orders.sql`
   (the purchase-order screens do not work until this runs) and
   `006_alias_provenance.sql` (must precede any bulk alias load, or an alias
   Afaq approved becomes indistinguishable from one the machine proposed). Both
   idempotent.
2. **Build the ZIP upload page** (MCT-145). Approved, unblocked, and it makes
   the whole pipeline usable before the mailbox exists.
3. **Write the ingest → Supabase writer** (MCT-146). First live write in this
   workstream: backup, dry run, and Afaq's yes on the day.
4. **Apply the 222 harvested aliases** after step 1. Backup, dry run, scoped
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
8. **Everything still waiting on Afaq** is in `docs/YUNT_OPEN_DECISIONS.md`:
   Cristian's address, the receiving domain, the Resend and Claude keys.

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
