# CONTEXT — the words this project uses, and what they mean

A glossary and nothing else. No decisions (those are `docs/DECISIONS.md`), no
state (`docs/STATE.md`), no design (`docs/ARCHITECTURE.md`).

Terms are here because they were actually confused at least once. Several of
these look like synonyms and are not.

---

## The two kinds of classification, which are not the same thing

**Category** — the *accounting* class of a line: `EXP-14.3`, `ING-0.1`. 78 of
them live in the `categories` table. This is what the ML model predicts and what
Antillanca's accountant cares about. A category answers *"which account does this
spend belong to?"*

**Catalog item** — the *product* a line names: `Gasolina 93`, `Agujas
desechables`. 4,002 of them in `item_catalog`. A catalog item answers *"what
thing was bought?"*

They are independent. Two lines can share a catalog item and sit in different
categories, and vice versa. Conflating them is the single easiest mistake to
make here, because both sound like "classifying the line".

---

## Alias versus pattern — the distinction the whole resolver rests on

**Alias** — a *memorised observation*. "This exact wording has been seen to mean
this exact catalog item." `cloro organico 5 kg` → `Cloro Organico`. Bounded: a
finite set of wordings, each written down once. Safe, because it asserts nothing
beyond what was observed.

**Pattern** — a *derived rule*. "Wordings of this shape mean this kind of item,
with the varying part stripped." `SEGUN OT <n>` → `SEGUN OT`. Unbounded by
design: it must cover wordings never seen. Powerful and dangerous, because it
generalises — and a wrong generalisation is applied silently to everything.

**The test for which to use:** does the wording recur, or is each occurrence
unique? Recurring → alias. Unbounded → pattern. This is why you never need to
answer "should `5 kg` be stripped from `cloro organico 5 kg`?" — as an alias you
record the observation and never form the rule that would break `Gasolina 93`.

---

## Line-level states, where the names lie slightly

**`decision`** — `auto_accept` or `review_required`, on `invoice_items`.

**⚠ `auto_accept` does not mean "the machine accepted it".** The dashboard's
category dialog sets `decision = 'auto_accept'` when a *person* picks a category
(`productos/actions.ts:76`), and `aggregate.ts:104-107` then counts that row as
automatic. So the "67% auto-accepted" figure is contaminated and reads high. The
column means **"settled"**, not "settled by the machine". Read
`prediction_source = 'user_selected'` to find human picks.

**`needs_review`** — a GENERATED column. Postgres derives it from `decision`.
Writing it returns 400 and takes the whole batch down. Never include it in a
write.

**`prediction_source`** — how a line got its category: `model`,
`product_lookup`, `meter_lookup`, `business_rule`, `cleanup`, `user_selected`
(D-047). **`cleanup` means only "a pass we ran once"** — it is not provenance,
and 592 client-sourced labels are hidden inside it. Never reconstruct authority
from this column.

---

## Documents

**DTE** — Documento Tributario Electrónico. The SII's electronic invoice XML.
Every file in `Data/Raw_Data/` is one.

**Folio** — the document's number, unique per issuer per document type. Identity
is `(issuer RUT, document type, folio)`, which is what duplicate detection keys on.

**RUT** — a Chilean tax ID, `76360720-8`. **Supabase stores it with the hyphen
stripped and the check digit uppercased** (`763607208`). Every one of 11,000+
stored values is in that shape. Matching the DTE's format instead makes every
document look new.

**COMPRAS / VENTAS** — purchase / sale. **Cannot be recovered from the file**:
the same document type appears on both sides, and the classifier requires it.
That is why it comes from the folder, and why the ZIP layout is part of the
agreement with Cristian rather than an implementation detail.

**Meter code** — the receiver's internal service number (`CdgIntRecep`). For
electricity it identifies the account more precisely than the supplier's line
wording does.

**Patente** — the DTE transport field. On petrol purchases Antillanca uses it
for either a vehicle plate or a spelling of *bidón*; that value determines
vehicle travel versus farm petrol. An absent or unrecognised value is unresolved.

**Document types** — `33` factura electrónica · `34` exenta · `56` nota de
débito · `61` nota de crédito · `43` liquidación factura. Type 43 names its body
`<Liquidacion>`, not `<Documento>`.

---

## Purchasing

**Request** (*solicitud*) — what someone needs. Opened before a supplier or
price is known. Stays **open** until an order is generated against it, which is
how "asked for but not yet ordered" is one status filter.

**Quotation** (*cotización*) — a price a supplier gave. **Obtained outside this
system.** Nothing here contacts a supplier; the file is uploaded after the fact.

**Order** (*orden de compra, OC*) — the commitment: supplier, agreed price,
quantity, delivery date. Generating it closes its request. It carries the
**accounting category before the money is spent**, which is the reason purchase
orders belong in this product at all.

**Handover sample** — five complete original purchase invoices (twelve lines)
intentionally removed from live so the team can email their unchanged XML as new
input. It is a reversible ingestion exercise, not a fresh model-quality test.
Its exact row snapshot and recovery instructions are in
`handover/yunt-team-test/MAINTAINER.md`. It is the only deliberate difference
between live and the saved baseline at handover.

---

## The Yunt

**The Yunt** is the part of the system that exercises **judgement**. It is not
the pipeline. Reading mail, unzipping, parsing, deduplicating, classifying,
storing and reporting are plain code and would run with the Yunt switched off
(D-051).

Its scope is exactly: choosing which precedent applies to an unclear line,
reading a free-text question and picking which prepared query answers it, and
drafting a purchase request from a sentence. **It never writes a number, never
writes a query, and never writes to the database** — it returns a structured
answer, and code checks and writes it.

**Email allowlist** — the shared inbound/outbound permission gate. A listed
mailbox may send Yunt a request and receive its reply. An entry such as
`@mctechstudio.com` matches the exact domain only; it excludes subdomains and
lookalikes. The original protected list is combined with the additive team list
so expanding access does not overwrite existing recipients.
