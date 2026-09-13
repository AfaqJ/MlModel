# Yunt live acceptance report — 2026-09-12

## Executive summary

The Yunt was exercised through real Outlook email, using the live branch-preview
deployment and the paid Sonnet review where judgement was needed. It can ingest
invoice ZIP files, report invoice-data problems, propose accounting categories
with evidence, answer defined spend questions with files, safely apply and undo
category changes, and open and issue purchase documents by email. Every test
row was removed afterwards; the live database is back to its exact pre-test
baseline.

This report is written entirely in English. The original messages were sent in
Spanish because that is the operating language of the Yunt; quoted commands are
translated or explained here.

## How the email interface works

- Send ordinary email to `antillanca.yunt@mountaincreative.cl` from an allowed
  address. A request may be plain text unless it is an invoice-ingestion test.
- For a change that writes data, the Yunt first sends a preview: exact facts,
  exact consequence, and the required confirmation phrase `SÍ, ADELANTE`
  (meaning **Yes, proceed**) on the first line of the reply. A normal “yes”, a
  phrase lower in the email, or quoted old text cannot approve anything.
- The Yunt never emails a supplier. It can make a purchase request or purchase
  order inside the dashboard and tells the user that Antillanca must send the
  downloaded purchase-order PDF to the supplier.
- A price quotation can be supplied as ordinary written email text. In the
  live test it was explicitly described as a **telephone quotation**, not a
  PDF: supplier, quantity, unit price, total price and delivery date were in
  the message body. Uploading a file and proving that it is genuinely a
  quotation is intentionally still unbuilt (`MCT-165`).

## 1. Invoice intake, review and findings

### What was sent

One new email, subject **“Yunt test — invoice batch 2”**, carried one ZIP
attachment: `yunt_test_6.zip`. It contained six Chilean purchase-invoice XML
files, using new test folios `999201` through `999206`. No old email or old
attachment was referenced. The ZIP was the only input attachment.

### What the Yunt did

It first sent a deterministic reception report — this part does not call the
model — saying that it read six XML files, saved six new documents and seven
lines, found no duplicates, and found one arithmetic discrepancy. It then made
one Sonnet review call and sent a separate grouped findings email.

The one discrepancy was deliberately planted in **folio 999205**:

| Invoice line | Supplier-stated amount | Arithmetic check | Yunt action |
|---|---:|---:|---|
| Liquid nitrogen, 40 × CLP 9,000 | CLP 412,000 | CLP 360,000 | Flagged it for a person; did not change the source amount. |

That is what “1 mismatch” meant. It was a supplier-document inconsistency, not
an incorrect Yunt answer and not a rejected invoice. The system is deliberately
not allowed to alter financial values copied from an invoice.

The ZIP also contained a deliberately meaningless item name, **“DETAIL”**, in
folio `999206`. The Yunt flagged it rather than guessing what was bought. The
grouped findings contained three data-quality findings in total and four
unapplied category proposals. The proposals were grounded in existing
human-confirmed records:

| Test line | Evidence available to Yunt | Result |
|---|---|---|
| Operating rent payment | 17 prior human-confirmed records | Proposed `EXP-15.8` |
| Accounting advisory | 14 prior human-confirmed records | Proposed `ADM-1.8` |
| Rodent control | 80 prior human-confirmed records | Proposed `EXP-7.0` |
| Liquid nitrogen | 9 prior human-confirmed records | Proposed `EXP-3.1`, while separately retaining the arithmetic flag |

The proposals were only suggestions. Nothing changed until a person confirmed.

## 2. Category approvals, corrections and undo

### How it was asked

These actions were replies to the Yunt’s findings/confirmation email; no file
was attached. The live checks covered the following:

1. Approve a proposed category by replying with the required confirmation on
   the first line.
2. Reject a proposal in plain language.
3. Ask for an unsuggested category (`EXP-2.6`) instead of accepting the
   proposal.
4. Send “Undo that” after an applied change.
5. Try the confirmation phrase below another line; the system refused it.

### What happened

The accepted live changes moved one line from `ADM-1.4` to `ADM-1.8` and a
second from its previous category to `EXP-2.6`. Rejection did nothing. For the
unsuggested category, the Yunt restated the intended category and waited for
confirmation rather than changing it immediately. Undo restored every stored
before-value: category, review state and provenance. A misplaced confirmation
did not apply any change.

## 3. Spend questions and attached files

### How it was asked

The question was a normal email asking for 2025 fuel spend, grouped by month.
No invoice, spreadsheet or historical email was attached or referenced.

### What happened

The Yunt queried only the saved invoice data and answered **CLP 93,146,229**.
That number was independently recomputed from the source rows and matched to
the peso. A separate no-data question about 2024 fuel returned “no data”; it
did not invent a total or attach an empty spreadsheet.

For the artefact request, the reply carried files, not just a number in email:

| File | What it is | What was checked |
|---|---|---|
| Spreadsheet attachment | UTF-8, semicolon-delimited `.csv`, designed to open correctly in Chilean Excel | Accents, columns, filter header and row total were correct. |
| PDF attachment | Actual `.pdf` report | Opened without PDF errors; all 12 months were chronological and the total matched. |
| Chart attachment | A chart file, explicitly labelled as a chart | Months were ordered by time rather than spend amount; no months were silently hidden. |

The attachment inspection matters: three bugs were found only by opening the
delivered files — line-break formatting, chart ordering/truncation, and an
early reply that claimed a PDF while attaching a chart file. Those are fixed;
the report now describes the actual attachment type rather than promising a
different one.

## 4. Questions the Yunt cannot answer

### How it was asked

The live refusal question was: **“What profit margin does FEROSOR AGRICOLA make
on what it sells us?”** No attachment was supplied.

### What happened

The Yunt refused instead of calculating a plausible-looking guess, because
purchase invoices contain what Antillanca paid, not the supplier’s own costs,
sale prices or margin. It recorded the original user wording once in the
refusal backlog.

This proves safe refusal. It does **not** prove a completed product feature for
supplier-margin analysis. The temporary refusal record was removed with all
test data during baseline restoration.

## 5. Purchase request by email

### How it was asked

The first message was plain text: **“I need 20 sacks of mineral salt for Fundo
Raíces, for 30 October.”** No document or quote was attached.

### What happened

The Yunt did not guess the year. It asked: **“Which year is 30 October?”**
After the reply **“2026-10-30”**, it sent a preview containing all facts:
20 sacks, mineral salt, Fundo Raíces, date, planned priority, one-time product
purchase, and no estimated budget. It explicitly said that confirmation would
create an open request, not a purchase order and not supplier contact.

After the exact confirmation, it created **`SOL-2026-0001`** and replied in
English meaning: “The request is open until a purchase order is generated; no
supplier has been contacted. When you have a quotation, send supplier, quantity
and price.”

## 6. Purchase order and quotation rule

### How it was asked

In the same email thread, the first quotation was written in the message body:

> Telephone quotation from Agro Uno: 20 sacks, CLP 30,000 per sack, CLP 600,000
> net total; requested delivery 2026-10-30.

There was no quotation PDF. The Yunt initially exposed a thread-context bug;
after the repair, the same written quotation produced an exact order preview.
The preview named Agro Uno, 20 sacks, CLP 30,000 each, CLP 600,000 total,
delivery date, selected quote, request closure consequence, and the fact that
Yunt would not contact the supplier.

### What happened

After confirmation with only that one quotation, the database itself refused
the order because CLP 600,000 is above the CLP 500,000 threshold. The Yunt
explained that a second quotation was required; it did not split the order or
work around the rule.

The second quotation was also plain text: **Agro Dos, CLP 620,000 total, CLP
31,000 per sack, 20 sacks.** The Yunt recorded it, re-prepared the Agro Uno
order and waited for confirmation again. The final exact confirmation created
**`OC-2026-0001`** for Agro Uno: 20 sacks at CLP 30,000, CLP 600,000 total,
delivery 2026-10-30. The request became `ordered`. Its final reply said the
purchase-order PDF is downloaded from the dashboard and sent to the supplier
by Antillanca, not by Yunt.

## Current limits and remaining tickets

| Status | Meaning |
|---|---|
| 19 tickets done | Earlier capability evidence remains valid; four tickets reopened for new acceptance requirements. |
| `MCT-153` done | Its completed scope is safe refusal plus recording the original rejected wording once. Later review of real refusals and feature selection is separate product work. |
| `MCT-142` in progress | Parent reopened while the three changed child capabilities are re-proved. |
| `MCT-152` in progress | The files open and contain correct figures, but their CSV/basic-PDF/SVG presentation does not yet meet the required document standard. |
| `MCT-156` / `MCT-157` in progress | The preview now retains replies in the opening Outlook thread; it will warn about the two-quotation rule before confirmation and email the purchase-order PDF. Migration `029` plus live proof remain. |
| `MCT-154`, `MCT-143` parked | Deliberately deferred, not silently dropped. |
| `MCT-165` separate Backlog | It would validate that an uploaded file looks like a quotation before that file counts toward the two-quotation rule. It is deferred: a written/telephone quotation is already valid v1 input, and file inspection cannot prove a supplier's price is truthful. |

## Final data safety result

The test invoice ZIP, temporary invoice rows, review records, category changes,
request, quotations, purchase order and inbound records were removed. The
rollback verified every watched table against the saved baseline: 5,195
invoices, 11,746 invoice lines, 4,002 catalog items, zero test purchase
documents and zero Yunt test records.
