# YUNT — implementation plan

The recipe. Built horizontally: **every phase ends with something that runs end
to end**, so a defect is found the day it is introduced, not on the last day.

`docs/Yunt_scope_v1.docx` is the client-facing menu of 19 items and **is not
authoritative** — it was sent on 2026-09-07 and several things were settled by
discussion afterwards. Where the two disagree, `DECISIONS.md` wins and this
plan follows it. The scope document is what Antillanca agreed to receive, not
the record of how it is built.

**Branch:** `yunt-backend` here, `yunt` off `feature/dashboard` in
`../milk-company`. Frontend work is pushed through `4035fef`; twenty-six later
commits are local and unpushed through `016f907`.

**Status: building, in `../milk-company`.** Phases 1–2.5 are done. Phase 3's
writer is connected to both doors in source; the email path is unproved live and
the upload path lacks authenticated database permission. The review/apply loop
and three of five query tools, the refusal backlog and Yunt-created purchase
requests are built, but migrations `011`–`018` are not live. Every phase below carries
its own state. The seven GO decisions D1, D2, D3, D5, D6 and D7 are settled
(Afaq, 2026-09-08); D4 was withdrawn.

The production classifier connection itself is proved: on 2026-09-09 the
dashboard's TypeScript adapter received 10/10 results from the deployed v1.3.3
`/predict-batch`. That does not substitute for the first real mailbox run.

---

## 1. What we are building on — the facts, with numbers

Measured from `reports/recovery_v1_3_3/supabase_upload/` (the 11,746-row
snapshot) and live. These numbers are the reason the design looks the way it does.

### What kind of invoices arrive

| | |
|---|---|
| Documents | 5,195, dated 2024-12-31 → 2026-04-02 |
| Direction | 5,107 COMPRAS, 88 VENTAS — this is a **purchasing** dataset |
| Document types | `33` factura electrónica 4,960 · `61` nota de crédito 103 · `34` exenta 100 · `43` liquidación factura 29 · `56` nota de débito 3 |
| Suppliers | 431 distinct seller RUTs |
| Volume | ~300–460 XML per month, 2.5–4.0 MB per month uncompressed |
| Lines | 12,103 raw → 11,746 stored (**357 unexplained**, `AUTOMATION_PLAN` A-1) |

**Sizing consequence:** one month zipped is well under 1 MB. Resend's 40 MB
message cap is not a constraint at this volume. A full-year backfill would be —
that path is a direct upload, not email.

### What settled the 11,746 lines

| Path | Rows | Share | Decision |
|---|---|---|---|
| `product_lookup` — client's own row-level labels | 2,639 | 22% | all auto-accept |
| `meter_lookup` — electricity meter → fixed category | 1,587 | 14% | all auto-accept |
| `business_rule` — 28 exact VENTAS phrases | 928 | 8% | 884 auto, 44 review |
| **Deterministic subtotal** | **5,154** | **44%** | |
| `model` | 5,018 | 43% | **983 auto, 4,035 review** |
| Human backfill passes (now tagged `cleanup`) | 1,574 | 13% | |

**Read that model row again.** The classifier auto-accepts **8% of the corpus**
and sends 34% to review. The deterministic cascade does the work; the model is
mostly a triage device that says "I don't know" honestly.

And of the review rows, `AUTOMATION_PLAN` C-5 measured that **68% (3,529) are
undertrained wordings, not genuinely ambiguous items** — `"Traslado de terneras"`
scored Freight at 0.40 because nothing like it was in training.

**This single fact determines the Yunt's design.** For a wording the model has
never seen but a human has already settled once, the right answer is not a
better model and not a cleverer prompt — it is a **lookup against the 7,900+
already-confirmed lines.** So:

> The Yunt's category proposal is a **precedent search**, computed in SQL. The
> language model's job is to read the question, pick the evidence that applies,
> group the lines and write the sentence. It never invents the category and
> never computes a number.

That is the same rule D-053 already fixed for reports, applied to proposals.

### The classification cascade as it stands (`app/inference/predictor.py`)

```
1. meter lookup        COMPRAS + known CdgIntRecep    → deterministic, score 1.0
2. business rules      exact VENTAS phrase (28)       → deterministic, score 1.0
3. product lookup      COMPRAS, 696 client labels     → deterministic, score 1.0
4. model               ONNX + LR head + direction mask
5. confidence gate     top1 ≥ 0.75 and margin ≥ 0.50
6. ambiguity guard     structural rules               → review
7. familiarity gate    kNN k=10, agreement 0.4        → review
8. unknown-sales rule  unmatched VENTAS               → review
```

Steps 5–8 can only ever **downgrade** to review. None of them can promote.
The Yunt slots in as **step 9, under the same rule** (see decision D1).

---

## 2. Where the Yunt lives

**Inside the existing `milk-company` Next.js app on Vercel, as an
[eve](https://vercel.com/eve) agent (D-055).** Same repo, same deploy, same
database. Google Cloud hosts the classifier endpoint and nothing else.

```
Cristian ──email──► Resend inbound ──webhook──► /api/yunt/inbound   (Vercel)
                                                    │
   Cristian ──browser──► /carga (ZIP upload) ───────┤ same pipeline
                                                    │
        ┌───────────────────────────────────────────┼──────────────────────┐
        │                                           │                      │
   Cloud Run `mlmodel`                          Supabase                Claude API
   /predict-batch (existing, untouched)      (shared state)          (judgement only)
```

**Why not a separate Python service, which is what this plan said until
2026-09-09:** the argument then was that the DTE parser was too hard-won to
rewrite in TypeScript. That argument has been settled by doing it — the parser,
the archive reader, the catalog resolver and the classifier client are all
ported, and each was verified by replaying the same 4,451-file corpus and
asserting the numbers as **equalities**, not by inspection. The knowledge was
not re-earned; it was moved, with a test that proves it arrived intact.

What that buys: one deploy instead of two, one language for the agent's tools
(eve's tools are TypeScript files in `agent/tools/`, and `approval` is a
built-in field rather than machinery we write), and no second service sharing a
failure mode with the client's live classifier.

**Two doors into the same pipeline, deliberately.** Email is the agreed channel
(scope items 1–5). The `/carga` upload page is the standing fallback for when
Cristian would rather not use email, or when the mail path is down — and it is
also the only sane route for a full-year backfill, which was never going to
arrive as an attachment. Both call `runIngest`; there is one copy of the logic,
so the two cannot drift.

**The seam with the classifier is HTTP, not an import.** That is what keeps
torch, onnxruntime and a 278 MB model out of this app, and lets the two deploy
independently.

## 3. Decisions needed before GO

**D1. Does the Yunt gate the write, or annotate after it? — DECIDED: annotate after.**
You said "go over it once before sending the confirmed rows to database". The
sent scope says the opposite order (item 4 writes, section 2 flags).
**Recommendation: write first, then the Yunt pass, and the pass may only
downgrade** — exactly like cascade steps 5–8. Gating means holding a batch in
limbo somewhere that is not the database, which is a second source of truth, and
this project's history is a list of what happens to those. Practically the
outcome is identical: nothing reaches Cristian's report until the Yunt has run,
and a row the Yunt distrusts is in review before he ever sees it.
**Settled 2026-09-08 (Afaq).** The Yunt runs immediately after the write and may
only downgrade an `auto_accept` row to review. No staging store. This differs
from the order described in the sent scope, but the behaviour Cristian observes
is identical — nothing reaches his report before the pass has run — so it needs
no re-send.

**Confirmed and refined 2026-09-09 (Afaq, D-064).** Storage never waits for
Claude: the deterministic reception report is the first email, even when the
agent is unavailable. The Yunt then reviews every line through a compact map of
normalised groups, so repeated wording is sent once rather than once per invoice
line. A second, conversational email is sent only when the Yunt has a finding or
proposal. If the Yunt is unavailable, that second email is absent and the saved
batch remains eligible for a later pass.

**D2. Catalog resolver scope for v1. — DECIDED: build the full resolver first.**

**Settled 2026-09-08 (Afaq),** against the recommendation to ship exact-match
only. `AUTOMATION_PLAN` §D is honoured rather than overridden: an incoming line
must resolve to the *correct* catalog row before it is written, not to a new row
by default. The resolver becomes one callable component with its own phase (2.5)
and adds roughly five days.

**What "full" can and cannot mean, stated plainly.** Four of the six tiers are
buildable now. Two are not, and no amount of scheduling changes that:

- **B-1, B-2 — already solved.** Normalised exact match, enforced live by
  `item_catalog_normalized_name_uidx`. Wiring, not design.
- **B-3 aliases — buildable, needs your approval on content.** `item_aliases`
  already exists with `catalog_item_id` as a foreign key to the canonical row,
  which is the mapping you described; it holds 8 rows, all fuel. 131 measured
  candidates collapse to ~68 shapes. A `source` / `confirmed_by` column must be
  added **before** the first bulk insert, or an alias you approved becomes
  indistinguishable from one the machine proposed.
- **B-4 patterns (same item, different spec) — only partly buildable.** P-01
  (livestock lots) is applied. P-02 (instalments) needs one fix: drop `abono`
  from its strip list, because in `Traslado De Abono` it means fertilizer, not a
  payment. **The other ~1,389 mechanical wordings — kWh readings, `mes de
  MM/YYYY`, `segun ot N`, pack sizes, dimensions — need about six more patterns
  that are marked GUESS and are not written.** C-8 is explicit that a rule
  inferred from within-data correlation must be confirmed by the client before
  it is applied: the contractor→silage hypothesis was 18-of-19 and still wrong.
  Those six are blocked on Antillanca, not on us. **v1 ships P-01 and P-02; the
  rest are proposed to the client, not applied.** The governing rule stays:
  never strip all numbers — `93`, `95`, `97`, plates, contract IDs, models and
  grades *are* identity.
- **B-5 ambiguous parent — has no matching rule and does not need one.** Six
  wordings point at more than one canonical item, and an alias cannot express
  that (one parent, and the unique index rejects it).
  `CATALOG_MATCHING_PROPOSAL`'s own result shape already answers it:
  `match_type: "none"`, `requires_review: true`. Falling through is correct
  behaviour, not a gap.
- **B-6 generic placeholders — same.** `item`, `detalle`, `mano de obra` name no
  product; barred from the alias table, fall through to review with the
  description attached.

So the deliverable is the **five-tier resolver of
`docs/CATALOG_MATCHING_PROPOSAL.md`, complete, with tiers 4 and 5 returning
suggestions rather than automatic matches** — which is what that document
specifies anyway. It satisfies §D. It does not, and cannot, close B-4 in general.

**D3. Fix quantity parsing at ingestion. — DECIDED: fix it.**
`AUTOMATION_PLAN` A-3: Chilean decimals (`1.006,50`) are parsed with `.` as a
thousands separator, so `GASOLINA 93` reports 62,648,532 litres. Amounts are
correct; quantities are not. Scope item 6 wants a "line total ≠ quantity × unit
price" flag — **which would fire on nearly every line until this is fixed.**
Since we are writing a new parser anyway, this is a few lines.
**Settled 2026-09-08 (Afaq).** `yunt/dte.py` parses Chilean decimals correctly
from the first line it reads. The 11,746 historical rows stay wrong until a
separate backfill, which is its own approval.

**D4. — WITHDRAWN.** Was: capture the `Referencia` block for credit-note netting.
Afaq's objection, 2026-09-08, and it was right: nothing in the Yunt needs it.
The quality flags do not (a credit note's own totals are internally consistent)
and report totals are already wrong for historical rows, which is a data-side
item independent of this workstream. Replaced by an implementation note, not a
decision: **the Yunt retains the received XML**, which Phase 2's per-invoice
reconciliation wants anyway, so any field the parser did not capture is
recoverable by re-parsing rather than by a schema commitment made in advance.

**D5. Sender and recipient allowlist. — SETTLED: config, not a decision.**

Antillanca never told us which addresses are allowed; that ask was cut from the
sent doc. For v1: Cristian's address and Afaq's, held in **one env var on the
`yunt` service**, `YUNT_ALLOWED_ADDRESSES` (comma-separated). No address in git.
Afaq's is **Afaq@mctechstudio.com** (given 2026-09-08); Cristian's still needed.

One list serves both directions — a sender not on it is logged and gets no
reply; a recipient not on it cannot be addressed, because `yunt/mail.py` is the
only code that can call Resend's send API and the check lives inside it. **It
fails closed:** unset or empty means the Yunt sends nothing at all, so the
service is safe before Afaq has filled it in. Changing the list is a config
update, not a redeploy.

The Yunt cannot contact a supplier because no code path can construct an address
that is not on this list.

**D6. `/predict-batch` is publicly invokable. — SETTLED: lock it in Phase 3.**

`gcloud run services get-iam-policy mlmodel` shows `allUsers` on
`roles/run.invoker`. No data is exposed (the service is stateless and holds no
records), but anyone who finds the URL spends the client's Cloud Run budget.

**Two callers, so two mechanisms — this is the part that is easy to get wrong:**

- **`yunt` stays publicly invokable.** Resend's webhook arrives from the
  internet with no Google identity, so IAM cannot gate it. Its gate is the Svix
  signature over the raw body, plus `YUNT_ALLOWED_ADDRESSES`. Public means
  reachable, not unprotected.
- **`mlmodel` becomes private.** `yunt` runs as a dedicated service account,
  fetches an OIDC token from the metadata server with `mlmodel`'s URL as
  audience, and sends it as a bearer token. No key, no rotation, nothing in git.

```bash
gcloud iam service-accounts create yunt-sa --display-name="Yunt ingestion service"
gcloud run services update yunt --region europe-west1 \
  --service-account=yunt-sa@testproject-501519.iam.gserviceaccount.com
gcloud run services remove-iam-policy-binding mlmodel --region europe-west1 \
  --member=allUsers --role=roles/run.invoker
gcloud run services add-iam-policy-binding mlmodel --region europe-west1 \
  --member=serviceAccount:yunt-sa@testproject-501519.iam.gserviceaccount.com \
  --role=roles/run.invoker
```

**Why a dedicated account.** `mlmodel` currently runs as
`988859051589-compute@…`, the project's *default* compute account — the identity
every unconfigured service inherits. Granting that `run.invoker` would hand
classifier access to anything else that ever runs in the project. A named
account makes the grant mean what it says, and it is also what reads the Resend,
Claude and Supabase keys out of Secret Manager
(`roles/secretmanager.secretAccessor` on those three secrets) instead of
carrying them as plaintext env vars.

**Risk, stated plainly:** if anything outside this project calls that URL
unauthenticated today, removing `allUsers` breaks it. Nothing known does — the
dashboard reads Supabase, not the classifier — but it is worth one look before
the command runs.

**D7. `docs/MILK_YUNT_PLAN.md` — DONE: deleted 2026-09-08 (Afaq).** It contradicted
D-051 and D-052 and this plan replaces it. Untracked, so it is gone permanently.
Inbound references in `CLAUDE.md` and `docs/DECISIONS.md` were rewritten in the
same pass; the two that remain in `docs/STATE.md` are session history recording
that it existed, which is correct.

---

## 4. The phases

Each phase is one working day or less, ends with something you can run, and
leaves the previous phase still working. "Proof" is the command or action that
shows it, not a summary.

### Phase 0 — the deploy path · DONE, and it cost nothing

Superseded by D-055. The Yunt ships inside an app that is already deployed, so
there is no new container, no `Dockerfile.yunt`, and no `.gcloudignore` trap to
walk into. This phase existed to de-risk a deploy path that no longer exists.

### Phase 1 — email in, email out · BUILT, not switched on

Cristian emails the Yunt, the Yunt replies. Nothing is parsed, nothing is stored.

- `POST /api/yunt/inbound` — **Svix signature verification on the raw body**
  (`svix-id`, `svix-timestamp`, `svix-signature`; verifying against re-serialised
  JSON silently fails). Hand-rolled over `node:crypto` rather than adding the
  `svix` package, and guarded by `scripts/check-webhook-signature.ts`, which
  asserts two acceptances and eleven refusals including replay.
- Sender allowlist. A rejected sender is logged and gets **silence, never a
  bounce** — a bounce tells a stranger the address is live.
- `src/lib/ingest/mail.ts` — the **only** place that can call Resend's send API,
  with the `YUNT_ALLOWED_ADDRESSES` check inside it, failing closed when unset
  (D5). Unset today, so the code physically cannot mail anyone. Setting the
  variable is what turns mail on; there is no commented-out line to remember.
- Attachments come from Resend's receiving API in two hops — `GET
  /emails/receiving/{id}/attachments/{attachment_id}` returns a short-lived
  signed CDN `download_url`, and the API key must **not** be sent to that URL.

**Still needed to switch it on:** a receiving address (the free `.resend.app`
one needs no DNS; a custom domain needs an MX record on a **subdomain**, never
the root, or all mail for that domain goes to Resend), the Resend API key, the
webhook signing secret, and the allowlist. All four are Afaq's to supply.

**Not built:** the `yunt_emails` table recording every message in and out. It is
a write, so it belongs with Phase 3.

**Proof, once the four values exist:** send from Cristian's address and get a
report; send from a third address and get silence.

### Phase 2 — parse, deduplicate, report · DONE. **Still no writes.**

- Fetch attachments via Resend's Attachments API (`download_url`, they are not
  in the webhook body), unzip, walk `COMPRAS/` and `VENTAS/`
- `yunt/dte.py` — port the proven parser from `scripts/10_extract_line_items.py`,
  extended: full `Encabezado` (both parties, totals, IVA, exento, payment form),
  every `Detalle` (including discounts, recargos, `CdgItem`, `UnmdItem`),
  and `Referencia` while we are in the file anyway. Chilean decimals fixed (D3).
- Encoding: try UTF-8, fall back to latin-1. Non-negotiable.
- **The received XML is retained**, so any field the parser did not capture, or
  captured wrongly, is recoverable by re-parsing rather than by re-collecting
  from the client.
- Duplicate detection: `seller_rut + document_type + folio` against live
- **Per-invoice reconciliation** — raw `<Detalle>` count in, logical lines out,
  and a typed reason for every difference (`AUTOMATION_PLAN` A-1's requirement,
  designed in from the start rather than retrofitted)
- Reception report emailed: documents read, lines extracted, duplicates skipped,
  rejections with reasons. **Sent even when everything failed.**

**Proof:** email last month's real ZIP; the report's document and line counts
match `find … -name '*.xml' | wc -l` and the parser's own count; re-send the same
email and the report says 100% duplicate.

### Phase 2.5 — the catalog resolver · DONE, aliases awaiting a write (D2)

The one phase that needs no email, no Cloud Run and no writes: it is built and
measured **entirely offline against the 11,746 rows already in Supabase**, where
the right answer is already known. That is what stops it being five dark days —
there is a number on the board every day.

- **Audit the 4,002 live catalog rows first.** Which are genuine products, which
  are duplicates the normalisation missed, which are placeholders, which are one
  product wearing six specs. The resolver is only as good as what it resolves
  *to*, and no one has looked at the catalog as a whole since the migration.
- `yunt/catalog.py` — one function, the result shape from
  `CATALOG_MATCHING_PROPOSAL`: `{suggested_catalog_item_id, match_type, reason,
  requires_review}`. It never rewrites `item_name` or the line description.
- Tier 1 canonical exact · tier 2 supplier-scoped alias · tier 3 global alias ·
  tier 4 approved pattern (P-01, P-02) · tier 5 fuzzy, **retrieval only**.
- `item_aliases` gains `source` / `confirmed_by` **before** any bulk insert.
- The ~68 alias shapes go to you as a review list, not straight into the table.
- The remaining ~six spec patterns are written up as a proposal for Antillanca
  and are **not applied** (C-8).

**Measured 2026-09-08, before any code — three results that change this phase:**

1. **Accent-stripping buys almost nothing.** Exactly **one** catalog pair merges
   under it (`Confección de bolos` / `Confeccion de Bolos`). The live
   normalisation is already doing its job.
2. **41 catalog rows in 20 groups differ only by word order, filler words or
   accents** — `Arriendo de Televía` / `Arriendo Televía`, `Filtro Aceite Motor`
   / `Filtro Aceite De Motor`, `Purines Maiten` / `Maiten Purines`. These need
   **no alias rows at all**: sorting the tokens and dropping filler words in the
   normaliser merges them for free, and there is nothing to maintain afterwards.
   An alias row is for when the *words* differ, not their order.
3. **The obvious data-driven alias hunt fails, and fails loudly.** Same supplier
   + same unit price + same unit + no shared word produced **867 pairs**, and the
   strongest were `Clavos` ↔ `Tornillos`, `Vaca Gorda` ↔ `Vaquilla Engorda`,
   `Gasolina 93` ↔ `Petroleo Diesel Ultra`. All false. Unit price is not evidence
   of identity — cheap hardware clusters at the same price points. **Do not
   revive this heuristic.**

**And the pattern tier is more dangerous than it looked.** 91 catalog families
have four or more rows sharing their first two words, and most must *not* merge:
`Renta de arrendamiento · Contrato 22338-1` (16 rows, the contract is the
identity), `Mantenimiento preventivo · Equipo 1P05090EAJ0042577` (9 rows,
equipment serial), `Semen Bovino Leche Convencional CENTURION / COMMANDO / MEKE`
(different bulls), `Galleta Costa Limon / Tuareg Coco / Donuts Leche` (different
biscuits). Every pattern stays scoped to a supplier or product family, and each
one ships with the count of rows it would merge and a read of every one.

**So the honest shape of this phase:** the normaliser improvement is the cheap
win, the alias table stays small and human-read, and the pattern tier is a
careful, narrow, evidence-first exercise rather than six rules written at once.

**Daily proof, the same command each day:** replay the resolver over all 11,746
historical lines and print match rate by tier, plus — the number that actually
matters — **how many lines it maps to a catalog row different from the one they
sit on today.** Day one that number is 0 by construction (tier 1 only); every
tier added after must justify each disagreement it introduces.

### Phase 3 — write to Supabase · CONNECTED IN SOURCE; LIVE PROOF/PERMISSION PENDING.

The writer, its batch ledger, and the atomic invoice RPC are implemented on the
local `yunt` branch and dry-run by default. Migration `007_yunt_ingest.sql` is
**live** as of 2026-09-09. Both `/carga` and the mail route now import it. The
mail route uses the service client and still needs a real-message proof. The
upload route uses the signed-in client, but its required tables and RPCs grant
only `service_role`; a real save is blocked until an explicit operator policy is
added. Do not replace that policy with a service-key bypass.

- Classify in batches of 500 against `mlmodel`'s `/predict-batch`
- Lock `mlmodel` to a service account, give `yunt` that identity (D6)
- Write `companies`, `item_catalog` (through the Phase 2.5 resolver), `invoices`,
  `invoice_items` — whole rows, never partial. Each invoice plus all its lines
  goes through one transaction RPC, so one bad line rolls the document back;
  **never write `needs_review`**, it is GENERATED and returns 400
- Idempotent at batch level: the whole ingest keys on the email's message id, so
  a re-delivered webhook changes nothing
- `yunt_batches` table: one row per ingest, with counts and the reconciliation

**Offline proof complete:** focused planning/dry-run/replay tests plus a real
disposable PostgreSQL run. **Live proof still required:** ingest one month; row
counts before/after differ by exactly the report's numbers; the dashboard's
catalog and Analítica show the new period; re-run and nothing changes. Back up
first (`scripts/81_backup_supabase.py`).

**This is the first phase that touches live data.** It gets its own approval
from you on the day, against a dry run.

### Phase 4 — data quality flags · day 9 (scope item 6)

**Detection is deterministic and read-only. Fixing is a proposal, and the
proposal goes through Phase 6's approve/apply/undo path** — not a second one
(D-058). Afaq, 2026-09-09: the Yunt is a collaborator, not an advisor, so it
does act on data problems — but only after Cristian approves, and through the
one apply mechanism that already has an undo.

- line total ≠ quantity × unit price (viable only because of D3)
- document total ≠ sum of its lines
- duplicate folio within the batch
- unit price outside the historical range for that catalog item (scored against
  **that item's own history**, per D-049 — never a pooled distribution)
- supplier RUT never seen before
- junk item names — placeholders (`Item`, `Detalle`), empty names, a name that
  is only a number. 177 such lines exist in the historical corpus.

Flags land in `yunt_flags` and appear in the batch report. A flagged
`auto_accept` row is **downgraded to review** (D1) — the only thing detection
changes by itself. Anything beyond that is a proposal Cristian approves.

**A live example of why this phase is not theoretical:** 387 stored documents
carry lines that overstate their own header by CLP 21,189,814 in total — one
electricity invoice worth CLP 1,261 has a line claiming CLP 1,011,311, which is
a meter reading sitting in the amount column. Per-category spend on the
dashboard is inflated by that today. See `docs/CLIENT_DATA_ISSUES.md` §1. The
constraint there holds: a check may **flag**, never silently change a value and
never block an ingest, and a missing field is normal rather than an error.

**Every threshold is calibrated against the existing 11,746 rows before it
ships, and the hit rate is reported.** Afaq's requirement, and it is the right
one: a flag that fires on a third of the batch is noise Cristian learns to
ignore, and a flag that never fires is a line of dead code claiming to protect
something. Each flag's replay over history is part of the phase's proof, not an
afterthought — and the quantity × price check cannot ship at all until the
decimal fix from Phase 2 is in, or it fires on nearly every line.

**Proof:** a hand-made ZIP with one broken total and one unknown supplier
produces exactly two flags and no others.

### Phase 5 — category proposals with evidence · day 10 (scope item 7)

The first phase with a language model in it.

1. **Code** groups every batch line by normalised wording. Each compact group
   carries counts, classification variants, confidence ranges, counterparties,
   amounts and deterministic flags; exact member ids stay server-side.
2. **Code** fetches precedent for each group: confirmed lines with the same
   normalised wording, the same catalog item, or the same supplier + similar
   wording, with their categories and counts.
3. **Claude** receives the group, its precedent rows, and the relevant
   `CLIENT_CONVENTIONS` extract. It must return a category **from the enumerated
   live list**, a one-sentence reason, and the evidence rows it relied on — or
   `insufficient_evidence`, which is a valid and expected answer.
4. **Code** rejects any response naming a category outside the list, or citing
   evidence that was not supplied.
5. Proposals are written to `yunt_proposals`. **Nothing is applied.**

**That includes every auto-accepted line** (Afaq, reconfirmed 2026-09-09). The
arithmetic flags in Phase 4 cannot see a category that is simply wrong — a line
settled by a stale product-lookup entry is arithmetically perfect. Reading is
where a language model genuinely beats the pipeline, and 44% of every batch is
settled by fixed lookups that no other check ever questions. A wrong-looking
auto-accept becomes a proposal like any other; consistent with D1, the Yunt can
only move it *into* review, never quietly re-file it.

The prompt carries no free-text numbers back into the email: counts and amounts
in the message are rendered by code from the query result.

**Proof:** run it against 200 known review rows whose correct category we already
know from the client's own answers (`reports/client_reply_2026_09_02/`) and
measure how many it gets right, how many it refuses, and — the number that
matters — **how many it gets confidently wrong.**

### Phase 6 — apply on approval, with undo · day 11 (scope item 8)

- A proposal group is **sealed**: it stores the target `item_id`s and the value
  each row held when the proposal was made. Approval calls
  `apply_proposal(proposal_id, nonce)` and nothing else. **No version, id or row
  list comes from the caller** — otherwise a stale approval could be re-armed
  against rows that changed after it was written.
- Rows that drifted since the proposal are skipped and reported, not overwritten.
- Applied rows are written exactly as the dashboard writes them
  (`prediction_source = 'user_selected'`, `decision`, `final_categories_id`,
  `final_code`, `reviewed`), because a category Cristian approved is a category
  Cristian chose.
- `yunt_applications` stores the prior values, so undo is a replay.
- **Cristian can disagree with part of a group** (Afaq, 2026-09-08). He replies
  "todo menos las dos de fletes". The Yunt does not re-issue a new proposal from
  scratch and it does not name rows: **it can only subtract from the sealed
  set.** Code resolves his words to specific rows *within* the group, re-sends
  the trimmed group for a final yes, and only then applies. Removing is safe by
  construction; adding a row is not expressible.

**Afaq's question — does the Yunt pass row names to a tool, or write code?**
Neither. **It never addresses rows at apply time at all.** The proposal already
contains the exact `item_id`s, sealed when it was written. The Yunt's only
outputs in this path are *which proposal* and *which members to drop*, and both
are validated against the seal before anything runs. So a hallucinated row id
cannot widen the change — the worst a wrong answer does is drop a line that
should have stayed, which is visible in the confirmation and undoable.
Code generation is never in this path.

- **A group may move rows either way** — an auto-accepted line that was wrong,
  or a review line being settled. Same mechanism: each row carries its own prior
  value in the seal, so the write is per-row and the undo is per-row.
- Two ways to approve: replying to the email, and a button in the dashboard.
  Same RPC, same seal.

**Proof:** approve a group of 20 by email, verify exactly 20 rows changed and
their prior values are recorded; undo; verify all 20 are back.

### Phase 7 — questions and reports · days 12–13 (scope items 9–12, D-053)

- One **canonical Postgres view** every figure is read through, so the money
  fixes (credit notes, the COMPRAS+VENTAS revenue defect, the IVA split) land in
  one place and every answer inherits them.
- Five tools: the general aggregate (filters × grouping × measure × sort × limit),
  period comparison, single-item price history, row-level listing, precedent
  lookup. Each is a typed function with validated parameters. **No SQL is
  generated by the model.**
- Delivery: a single figure in the body, a list as `.xlsx`, a detailed report as
  PDF. **Every answer prints the exact filter it used at the top**, so a
  misread question is visible rather than silent.
- Charts: bar, line, stacked bar, pie, table. Model picks, code draws.
- Refusal path, and a `yunt_refusals` table — that log is the backlog for what
  to add next, from real questions.

**Proof:** ten real questions in Spanish; every number cross-checked against a
hand-written query; at least one deliberately out-of-scope question refused
rather than guessed.

### Phase 8 — recurring reports · half day (scope item 13)

Cloud Scheduler → three jobs: month-end summary, post-batch digest, weekly
review list. Same tools, same rendering, nothing new except the trigger.

### Phase 9 — purchase orders, the forms · BUILT; `005_purchase_orders.sql` is live (D-052)

Frontend work in `milk-company`. The screens existed as mock-ups with a
`DemoBanner`; migration `005` ran on 2026-09-09, so they are backed by real
tables. Not exercised against live data yet.

- Tables: `purchase_requests`, `purchase_orders`, `quotations` (+ Supabase
  Storage bucket for the quotation files)
- `levantamiento` → form one, writes a real request
- Request list: open until an order is generated against it
- `orden-compra` → form two; **above CLP 500,000 the form will not submit
  without two quotation files**, below it a free-text price is enough
- Numbered PDF, generated server-side, downloaded by the buyer. **No supplier
  contact exists anywhere in the codebase.**
- `aprobacion`, `recepcion`, `pago` stay mock-ups. Roles stay cosmetic (D-052).

**Proof:** open a request, generate an order against it, see the request close
and the PDF download. Try to order CLP 900,000 with one quotation and be stopped.

### Phase 10 — the Yunt fills the forms · day 16 (scope items 18–19)

**Status:** form one is built locally through migration `018`, including
required-field validation, exact email confirmation and replay safety. Price-
precedent attachment and the order/PDF half remain.

- Cristian emails "necesito 20 sacos de sal para el fundo Raíces antes del 15".
  Claude extracts item, quantity, farm and date into the **same request table**,
  with `created_via = 'yunt'` and the source email id.
- Code attaches the precedent: who supplied that item before and at what price.
  Those numbers come from the Phase 7 price-history tool, never from the model.
- **The exchange Afaq described, which is the actual v1 target:**
  1. *"Quiero comprar sal — ¿dónde la compramos antes y a qué precio?"* The Yunt
     answers from the price-history tool. Nothing is created yet.
  2. *"Ábreme una solicitud."* It fills form one, asks for whatever required
     field is missing rather than inventing it, opens the request, and says the
     request is open and to come back with a quotation or an agreed price.
  3. Cristian either gives a price or says *"usa el último precio"* — in which
     case code fetches the last price paid and fills it in; the model does not
     retype the number.
  4. Above CLP 500,000 it checks the email for the two required quotation
     attachments and **refuses to generate the order while they are missing** —
     the same check the form runs, called from the same function, not a second
     copy of it. Below that, the recorded price is enough.
  5. It produces the numbered PDF.

**Proof:** an email produces a request that is indistinguishable in the
dashboard from one typed by a person, except for a badge saying who opened it.

---

## 5. Data model — new tables

All in the existing Supabase project. Every one needs **its own RLS policies,
`SELECT` and `INSERT`/`UPDATE` granted separately** — a read policy grants
nothing about writes, which is how the assignment dialog nearly shipped broken.

| Table | Purpose | Phase |
|---|---|---|
| `yunt_emails` | every message in and out, Resend id, direction, sender, verdict | 1 |
| `yunt_batches` | one row per ingest: source email, counts, reconciliation, status | 3 |
| `yunt_flags` | one row per data-quality finding, linked to its invoice or line | 4 |
| `yunt_proposals` | sealed proposal group: target rows, expected values, evidence, model reason, state | 5 |
| `yunt_applications` | what was applied and the prior values, for undo | 6 |
| `yunt_refusals` | questions the toolset could not answer | 7 |
| `item_aliases` | **existing** — gains `source` / `confirmed_by`, then ~68 rows | 2.5 |
| `purchase_requests` | form one; `created_via` = `user` \| `yunt` | 9 |
| `quotations` | uploaded files, linked to a request | 9 |
| `purchase_orders` | form two, links to its request, PDF reference | 9 |

Existing tables are **not** altered except by adding columns, and no column is
added that the dashboard would have to be changed to ignore.

---

## 6. Dashboard work

You asked specifically how the Yunt's work shows up. The answer everywhere is:
**it writes to the same tables people write to, and provenance is a column.**

**New:**
- **Yunt activity page** — batches received, what each contained, flags raised,
  proposals made, what was applied and by whom. Nothing the Yunt does is invisible.
- **Proposal review in the existing product/review flow** — a review line with a
  proposal shows the proposed category, the precedent rows behind it, and
  approve/reject for the whole group. Approving is one decision for fifty lines.
- **Flag chips** on invoices and lines that carry one.
- **Requests and orders** (Phase 9) — one list, `created_via` badge, no separate
  "Yunt inbox". A request the Yunt opened sits in the same list, sorted the same
  way, editable the same way.

**Changed:**
- The category-assignment dialog gains "approve this proposal" as a second
  entry point to the write path it already owns. Same Server Action, same rules.

**Pre-existing defects this plan does not fix** (they are on your list, and the
Phase 7 canonical view is where their fixes will land):
`aggregate.ts:88-90` sums COMPRAS and VENTAS into `totalRevenue`;
`aggregate.ts:104-107` counts human picks as auto-accepts, which is why the 67%
figure reads high; `types.ts:194` and `item_summary.sql:35-37` disagree on what
"confirmed" means.

---

## 7. ML backend changes

Small, and none of them blocking.

1. **Lock `/predict-batch` to a service account** (D6). One `gcloud` command.
2. **Batch the encoder.** `routes.py:80` loops `predictor.predict()` once per
   item, so a 500-row batch runs 500 separate ONNX encodes. Batching the encode
   is the single change that makes ingestion fast. Do it when a real batch is
   slow enough to notice, not before.
3. **`Source` in `app/api/schemas.py` lists four values; the database now has
   six** (D-047). The service only ever emits four, so this is not a bug — but
   the Yunt's writer must map, not assume.
4. **Nothing else.** The classifier's cascade, thresholds and artifacts are not
   touched by this workstream. If a retrain happens it is separate work, and
   `ADM-3.1` having zero training rows must be handled first.

---

## 8. Email, concretely

**Receiving** (verified against Resend's docs):
- Inbound arrives at a verified custom domain (MX record) or a `.resend.app`
  subdomain. The subdomain is the fast start; a custom domain is what Cristian
  should actually see.
- Resend POSTs `email.received` to our webhook. **The webhook carries metadata
  and attachment metadata, not the body or the file bytes** — the body is a
  `GET` on the received-email endpoint and attachments come from the Attachments
  API as signed `download_url`s. Plan for two calls, not one.
- Signed with Svix (`svix-id`, `svix-timestamp`, `svix-signature`). Verify
  against the **raw** body.
- Every inbound message is stored by Resend regardless of whether our webhook
  succeeded, so a missed delivery is recoverable rather than lost.
- 40 MB per message. A month of invoices is under 1 MB zipped.

**Sending:**
- One function, one allowlist, no exceptions (D5).
- Acknowledgement within minutes, then the reception report. Both sent even when
  everything failed — silence is the one outcome that is never correct.
- Threading: replies go into the same thread so Cristian's mailbox stays readable.

Sources: [Receiving Emails](https://resend.com/docs/dashboard/receiving/introduction) ·
[Inbound announcement](https://resend.com/blog/inbound-emails) ·
[Verifying webhooks](https://resend.com/docs/dashboard/webhooks/verify-webhooks-requests) ·
[Retrieve received email](https://resend.com/docs/api-reference/emails/retrieve-received-email)

---

## 8b. Where the agent sits relative to ingestion (refines D-051)

D-051 says nothing judgemental sits inside ingestion, and that stands. But the
step *before* ingestion is a judgement call: **which of several things is this
email?** A data batch, a question, an approval, a purchase request.

So the agent is the **front door router**, not a stage in the pipeline. It reads
the message, picks an intent, and calls a tool. **The tool is deterministic and
does the work** — ingestion in particular remains plain code from the ZIP to the
report, and could run with the router removed.

**It is not built until there is a second intent to route to.** Phases 1–3 have
exactly one — "the message carries a ZIP → ingest" — and a router with one
destination is a router with no job. It arrives in Phase 5 with approvals, and
by Phase 7 it is choosing between four.

---

## 9. The agent's contract

The model is used in exactly four places, all of them judgement:

| Where | It decides | It may never |
|---|---|---|
| Category proposals (5) | which precedent applies, how to group, how to explain | name a category outside the live list; cite evidence it was not given; state a number |
| Question answering (7) | which tool, which parameters, which chart, the prose | write SQL; compute a figure; answer outside the toolset |
| Request drafting (10) | item, quantity, farm, date from a sentence | invent a supplier or a price |
| Order drafting (10) | filling form two from a quotation | generate an order with quotations missing |

Three rules across all four:

- **No number in any output is written by the model.** Code computes and renders
  every figure. Where the model writes prose around a figure, it is given a
  reference, not a value — a model handed both a number and a slot writes
  *"casi el doble"* next to a correct number and invents the comparison.
- **Every proposal is refusable.** `insufficient_evidence` is a success.
- **The model never holds a credential and never writes to the database.** It
  returns a structured object; code validates it and code writes.

---

## 10. Deliberately not built in v1

Roles and approval routing (D-052 — the dashboard's six roles only hide menu
items today, and Antillanca has not said who approves what). Goods receipt,
invoice-to-order matching, payment. The Audisoft API path (D-054 — blocked on a
working credential; when it arrives it replaces **only Phase 1**, because parse,
dedupe, classify, store and report are shared). The spreadsheet template for
non-XML data. The ~six unwritten spec patterns of B-4, which are blocked on
Antillanca's confirmation. Any supplier
contact, ever.

---

## 11. What is still needed from you

1. **Clear the Supabase usage-limit block**, then run migrations `011`–`018` in
   numeric order. `005`–`010` are live; the eight pending files are idempotent and
   proved twice locally.
2. **Approve the `/carga` permission design.** Recommendation: a database Yunt
   operator allowlist seeded with Afaq's signed-in email, then Cristian later.
3. **Confirm the Claude model and cost tier.** Opus 5 / medium is temporarily
   pinned from Claude's estimate, not yet ratified by Afaq.
4. **Approval on the day for the first live write**, against a fresh backup and
   the already-built dry run.
5. **Your yes on the 222 harvested aliases**, and on the `Confeccion de Bolos`
   merge (`docs/YUNT_OPEN_DECISIONS.md` items 1 and 3).
