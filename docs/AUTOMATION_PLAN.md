# AUTOMATION_PLAN — every case we handle by hand, and how it becomes code

**This is the top-priority living document.** Right now the data is being
cleaned manually so we can *see* the shape of the mess. That manual pass is not
the product. The product is a backend that handles each of these cases without
us. Every decision, pitfall and correction we make from here gets an entry —
written the day it happens, not reconstructed later.

**Update rule:** any session that decides something, hits a new failure mode, or
overturns an assumption edits this file in the same session. If a `D-NNN` is
added to `DECISIONS.md`, its automation consequence lands here.

## Status legend — be honest about which is which

| | meaning |
|---|---|
| **SOLVED** | Implemented and verified in production. |
| **DECIDED** | Design is fixed and written down. Not built. |
| **GUESS** | Plausible approach, never validated against real data. Treat as unproven. |
| **OPEN** | We do not have an answer. |

Most of this file is GUESS or OPEN. That is the accurate picture and it should
stay visible — a plan that reads as finished when it isn't is how the 3am page
happens.

---

## A. Ingestion — raw invoice → row

### A-1. Row accounting from raw XML · **OPEN**

`docs/ARCHITECTURE.md` says the pipeline turned **12,103 raw invoice lines**
into the **11,746** that are live. **357 rows are unaccounted for and no
document explains them.** Until that gap is explained we cannot claim the
client's spend is fully represented.

The suspected causes — none verified:
- separator / filler rows in the source XML that carry no line item;
- lines where the description sits on one physical row and the price on the
  next, merged into one logical line;
- rows dropped for a missing required field.

**Automation requirement:** the ingestion writer must emit a per-invoice
reconciliation — raw lines in, logical lines out, and a typed reason for every
difference. A silent drop is not acceptable once we own this.

**Today's task:** reconstruct the 357 and classify them. This is item 1 on the
audit list because everything downstream inherits it.

### A-2. Multi-physical-row line merging · **OPEN**

Believed to happen, not documented, no rule written. Needs: the exact condition
under which two physical rows are one logical line, and what happens to the
`item_text` of the second.

### A-3. Quantity parsing · **OPEN (known broken)**

`GASOLINA 93` reports 62,648,532 litres. Chilean decimal format (`1.006,50`) is
being read with `.` as a thousands separator. **Amounts are correct; quantities
are not.** Any per-unit price analytics built on `quantity` is wrong today.

---

## B. Catalog naming — one product, one canonical ID

Design detail lives in `docs/CATALOG_MATCHING_PROPOSAL.md` (the resolver order)
and `reports/catalog_merge_2026_08_26/PATTERNS.md` (the pattern ledger). This
section records **which failure mode each tier answers** and how sure we are.

### B-1. Identical name · **SOLVED**

Exact match on `catalog_normalize_label(item_name)` — lower, trim, collapse
whitespace. Resolves **3,148 of 5,331** distinct historical wordings, 59%,
before anything cleverer runs. `item_catalog_normalized_name_uidx` enforces it.

### B-2. Same wording, different accents or punctuation · **SOLVED**

Same normalization absorbs a further **565**.

### B-3. Different wording, same product · **DECIDED, barely populated**

The alias table. `item_aliases.catalog_item_id` is a foreign key to the
canonical row, so one lookup returns the client-facing item. Schema is right and
live; **content is not** — 8 rows, all fuel.

- **131 candidates measured**, across 18 canonical items, 278 invoice lines.
  They collapse to **68 distinct shapes**, so ~68 alias rows, not 131.
- Test that identifies one: *none of the canonical name's meaningful words
  appear in the invoice wording*. `G93` vs `Gasolina 93`; `clavo cte.6 x5 bol`
  vs `Clavos`.
- **Not yet approved.** See `reports/` and the review artifact.

**Missing from the schema:** no `source` / `confirmed_by` / `confidence` column.
Once tier 4 writes aliases back from human confirmations, we cannot tell an
alias Afaq approved from one the machine proposed. Given that a client-sourced
label outranks everything (D-030), **add that column before the first bulk
insert.**

### B-4. Same product, varying specification · **DECIDED for two families, GUESS in general**

Narrow, scoped patterns that strip volatile data and keep identity.

- **P-01 livestock lots — SOLVED**, applied 2026-08-26. 35 rows → 8. Strips head
  count, breed/colour, brand mark and location; keeps animal type **and grade**.
- **P-02 instalment payments — DECIDED, not applied.** 9 rows → 4. Must drop
  `abono` from its strip list first: in `Traslado De Abono` it means fertilizer,
  not a payment.
- Everything else is **GUESS.** Roughly **1,389 wordings** are mechanical
  variation (kWh readings, `mes de MM/YYYY`, `segun ot N`, `planilla numero N`,
  pack sizes, dimensions) and would need about six more patterns. None written.

**The rule that governs every pattern:** never strip all numbers. `93`, `95`,
`97`, plates, contract IDs, models and grades *are* identity. Every pattern is
scoped to a supplier, category or product family.

**Why patterns and not aliases here:** these sets are **unbounded**. Every new
month, meter reading and OT number would need another alias row, forever. This
is the reasoning behind D-044's exclusion list, and it is the correct one.

### B-5. One wording, several possible parents · **OPEN**

**6 wordings** (`fundo raices`, `servicios`, `materiales`, `item`, …) point at
more than one canonical item. They cannot be aliases — an alias has one parent,
and the unique index rejects them. Today the description disambiguates by hand.
**No automated rule exists.** This is the hardest remaining catalog case.

### B-6. Generic placeholders · **DECIDED**

`item`, `detalle`, `mano de obra` name no product; the description carries the
meaning. Barred from the alias table. The resolver must fall through to review
and read the description — **which nothing does automatically yet.**

---

## C. Accounting category — the classifier half

### C-1. The review gate is the product, not a shortfall · **SOLVED**

7,927 auto-accepted, 3,819 in review (2026-09-03). Never release on aggregate accuracy —
the income slice is a mandatory gate (`docs/TEST_CHECKLIST.md`).

### C-2. `predicted_code` is never a business classification on a review row · **SOLVED**

D-001. The frontend rendered `predicted_code` on rows awaiting review — the same
error class as the original production incident. **Fixed 2026-09-02**: one
decision-aware resolver now sits in front of every surface that shows a category,
merged to `feature/dashboard`. Not yet confirmed live in production; the branch
is merged but the production deploy path is a CLI `vercel --prod`, so verify
before claiming it.

### C-2b. A person can now correct a label in the dashboard · **SOLVED, and it is the point**

The review gate produced 3,819 rows nobody could act on from the UI. The
category-assignment dialog closes that loop: click a product's category badge,
tick invoice lines, choose a category, save (D-048). Assignments are written as
`user_selected`, which is the only tag in the column that means a human at
Antillanca chose it.

**Automation consequence:** these are the highest-quality training rows the
project will ever get — client-chosen, on real invoice wording. The next retrain
should treat `prediction_source = 'user_selected'` as a gold candidate stream,
subject to `docs/LABELING_RULES.md`. Nothing consumes them yet.

### C-3. Client authority outranks row volume · **DECIDED, applied by hand**

D-030, D-040. Where the client filed the same kind of item consistently, that
filing beats the model. Applied manually so far. **Automating it means encoding
`docs/CLIENT_CONVENTIONS.md` as rules** — not attempted.

### C-4. Six categories cannot be predicted · **SOLVED by rule**

D-028. Rule-assigned, not model output. `EXP-15.6` still has 0 rows and would
trip the "fewer than 2 examples must fail loudly" limit on the next retrain.

### C-5. Undertrained phrasing, not ambiguity · **OPEN**

68% of review rows (3,529) are cases the model has simply never seen —
`"Traslado de terneras"` → Freight at 0.40. More labelled data fixes these; no
rule will. **This is what the client's next labelled batch should target.**

**2026-09-02: that batch now exists and the client offered it unprompted.** He
has been using this project's categories in his own accounting since July 2026
and has two months already categorised by his team. This is the highest-value
input available to the project and it costs one email. See
`docs/CLIENT_CONVENTIONS.md` §9.7.

### C-6. Gold defects · **OPEN**

`FUNDO CHAPICAHUIN` and `FUNDO RAICES` — farm names memorised as products
(`EXP-4.2`, `EXP-6.3`). Must be fixed before any retrain.

### C-7. Three client answers that become rules · **DECIDED 2026-09-02, not built**

From the client's reply of that date (`docs/CLIENT_CONVENTIONS.md` §9). Each is a
supplier-or-material rule that a resolver can apply without a model:

- **GEA `HORA TECNICA` -> `EXP-10.1`**, regardless of the technician initials
  that follow. 30 lines. Trivially automatable: supplier + item-text prefix.
  Dry run written: `scripts/97_apply_gea_mantencion_sala.py`.
- **Any plumbing material -> `EXP-14.3`**, farm and building alike. The client
  collapsed the distinction we were about to build, so the resolver needs to
  tell *plumbing from non-plumbing* only — one vocabulary, not two. The hard
  part is the vocabulary, and it must be built from the data: see
  `reports/client_reply_2026_09_02/`.
- **Bank and auction commissions -> a category that does not exist yet.** Blocked
  on C-9.

**The generalisable shape:** all three are *supplier + wording* rules, which is
the same shape as the fuel and meter rules already live. That is the tier the
resolver should grow next, not a smarter model.

### C-8. A correlation the client killed · **SOLVED, as a lesson**

We had built a contractor->silage/hay hypothesis from real counts: Valenzuela
18 of 19 silage, Agricola J-S-E 4 of 4 hay. The client's answer was flat: *"No, a
same contractor can do different jobs."*

**18/19 was not a rule and no amount of extra rows would have made it one.** The
signal was real and the causal claim behind it was false. Any future automatic
rule proposed from a within-data correlation must be confirmed by the client
before it is applied, exactly as D-030 says. Worth keeping because the numbers
here were more convincing than most of what we will find later.

### C-9. Categories dropped at intake on an unverified claim · **OPEN**

Seven categories were excluded because they *"normally do not have XML"*. Tested
against live data, four families all have XML-backed lines, one of them worth
CLP 418 million (`docs/CLIENT_CONVENTIONS.md` §10).

**Automation requirement:** intake must never drop a category on an assumption
about the client's paperwork. If a category is excluded, the pipeline has to
record the exclusion as a testable claim and re-check it against every load —
"0 lines matched this category this month" is a fact; "these normally have no
XML" is a guess. Two of four guesses here were wrong.

Immediate consequence: `Impuestos, comisiones, multas` has to be created before
44 review lines can be settled, and a brand-new category has **zero training
rows**, so it must be rule-assigned and flagged the way D-028's six are, or the
next retrain trips the "fewer than 2 examples must fail loudly" limit.

---

## D. What must be true before we hand ingestion to a backend

1. A-1 closed — every raw row accounted for, with typed reasons.
2. A-3 fixed — quantities parse, or `quantity` is marked untrustworthy in the UI.
3. The resolver (B-1…B-6) exists as one callable component with the result shape
   in `docs/CATALOG_MATCHING_PROPOSAL.md`, returning `requires_review`.
4. Alias table carries provenance (B-3) and is populated.
5. Pattern set written, scoped and reviewed — not the two we have.
6. C-2 fixed in the UI.
7. Every automatic assignment is reversible and logged with its `match_type`.

**None of these are done.** There is no online Supabase ingestion writer in this
repository at all — `app/api/routes.py` serves `/health`, `/model-info`,
`/artifact-check`, `/predict`, `/predict-batch`, and every Supabase write is an
offline script. That absence, not the matcher design, is the blocker.

---

## E. Open questions we cannot answer ourselves

- What component will own ingestion, and who writes it?
- Does the client want `SEGUN OT` numbers preserved as separate items?
- The 141 vague-named rows the description rescues (CLP 106,758,176) — automated
  description fallback, or always human?
