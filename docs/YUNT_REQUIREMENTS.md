# Requirements — Antillanca Yunt

**Status: partly superseded 2026-09-08.** The scope sent to the team is
`docs/Yunt_scope_v1.docx`; this file remains the long-form reference behind it.
Three things here are now out of date: the build order in section 2 puts
ingestion behind the mail channel and the agent (D-051 makes ingestion plain
code that ships standalone), section 8's purchase-order flow includes approval
routing (D-052 defers roles and approval to v2), and nothing here knows about
the Audisoft API (D-054). Sections 6, 7 and 10 still hold.

**Proposal for review. Nothing here is built.**
Every requirement has an ID so it can be accepted, changed or struck individually.

**Date:** 2026-09-07 · **Author:** Afaq Jamshaid
**Read first:** Rodrigo's `yunt_anatomy_engineering.md`. This document is written
in its vocabulary — a Yunt is a role with a role sheet, a boss who signs, cases
as the unit of work, and gates that belong to the boss rather than to engineering.

This says **what the Yunt will do**. It does not say how it will be built.

---

## 1. The role, in one page

This is the ROLE_SHEET in draft. It is the part to argue with; everything after
it is detail.

| | |
|---|---|
| **Profession** | Purchasing and accounting assistant — knows what an invoice line is, what a purchase order is, what a cost centre is, and how a chart of accounts is applied. Shareable with any client in the same trade. |
| **Role at Antillanca** | Receives new invoice data, runs it through the classifier, checks the result, reports what it found, proposes categories with evidence, applies what is approved, answers questions about the data in writing, and prepares purchase orders for a person to sign. |
| **Boss (signs)** | Cristián at Antillanca for anything touching accounting data. Rodrigo for changes to the Yunt's own identity, limits and gates. |
| **Never does** | Decides a category on its own · issues or approves a purchase order · sends anything to a supplier without a person pressing send · states a business cause · produces a figure it did not compute from the data · answers from data it does not hold. |
| **Success metric** | The share of lines arriving in review that a person settles *from the Yunt's proposal alone*, without opening the source invoice — measured monthly, against the batch's own review count. |
| **Channels (v1)** | Mail, and the existing dashboard. Not WhatsApp. |

### Identity layers, filled in

| Layer | For this Yunt | Changes with |
|---|---|---|
| Profession | Invoice lines, purchase orders, cost centres, chart of accounts, Chilean document types (factura, nota de crédito, guía de despacho, liquidación factura) | the trade |
| Role | The paragraph above | Antillanca |
| Persona | Name, register and language — **to be set with the client** (Q-11). Spanish, formal-but-direct, no marketing tone | rarely |
| Relations | **Outward:** Antillanca staff — findings, proposals, reports, questions; never a conclusion presented as settled. **Outward, suppliers:** purchase orders only, and only after a person issues them. **Upward:** us — escalates anything it cannot evidence | the org chart |
| Limits | The "never does" row, plus everything in §10 | regulation and the boss |

---

## 2. Build order — the to-do, in dependency order

Read this as the work plan. Each step exists because the next one cannot be built
without it. **Every step ends with something that runs**, so it can be shown and
argued with before the next begins. Steps are not sized equally; they are ordered.

The order is not a preference. Reading and evidencing data comes before reporting
on it; the mail channel comes before ingestion, because ingestion's whole output
is an email; proposals come before the machinery to apply them, because a
proposal nobody trusts is not worth applying; and the only irreversible step
comes last.

### Track 1 — the Yunt

| # | Step | Delivers | Cannot start until | Done when |
|---|---|---|---|---|
| **1** | **The role exists and can read.** The Yunt folder, its role sheet, one read tool over the existing data, and a receipt attached to every answer | R-0.1, R-0.2, G-3 | — | It answers *"how many lines are in review for August?"* with a number, the filter used, and a receipt showing where the number came from |
| **2** | **Questions and reports over existing data.** No new data, no email, nothing written. Runs against the 11,746 lines already held | R-C1 – R-C4, R-C6, R-B6 (the history comparisons) | 1 | Three real questions from Antillanca are answered correctly and reproducibly, and a fourth — outside the data — is refused with a reason |
| **3** | **The mail channel.** Dedicated mailbox, sender list, a case opened per incoming mail, and the answer sent straight back to whoever wrote | R-A1, R-0.3, R-C1 by mail | 1 · **Q-1** | A question sent by email opens a case and gets its answer back by return mail, with no step in between. An unlisted sender is recorded and ignored |
| **4** | **Ingestion.** Parse, de-duplicate, classify, store, acknowledge, report | R-A2 – R-A8, R-B1, R-B2 | 3 · **Q-2** | Antillanca emails a real batch and, with no manual step by us, gets an acknowledgement, then a reception report, and sees the lines in the dashboard |
| **5** | **Findings.** The arithmetic, structural, duplication, outlier and direction checks over each batch | R-B3 – R-B8 | 4 (needs a batch), 2 (needs the history reads) | The reception report carries findings, each naming the line, the check, the expected value and the observed one. Nothing was changed by a finding |
| **6** | **Proposals — drafted, not applied.** Grouped, evidenced, marked confident / uncertain / your call | R-B9 – R-B12 | 4 · 2 · helped enormously by **Q-10** | Antillanca reads a real set of proposals and tells us whether they are any good. **This is the decision point for the whole product** — if the proposals are weak, step 7 is not worth building yet |
| **7** | **The write path.** Approval bound to a specific proposal, apply-all-or-nothing, written confirmation, undo | R-B13 – R-B17, G-1, G-2 | 6 · **Q-3** · internal decision 3 (§13) | A group is approved, exactly those lines change, the change is recorded with who approved it, and undo restores them. Built and proven against a copy of the data before it points at the live database |
| **8** | **Scheduled reports.** Month-end, post-ingestion digest, weekly still-in-review | R-C5 | 2 · 3 · 4 | Each fires on time, and a schedule whose precondition fails sends nothing **and records why**. Deliberately late: a schedule firing the wrong figure is worse than no schedule |
| **9** | **The learning loop.** Corrections become proposed changes to the written conventions, approved by the boss, each with a test added | R-B18, R-B19 | 7 (there must be corrections to learn from) | One real correction changes a convention, the boss approved it, and a test covers it |

**Q-4 and Q-5 (credit notes, liquidación facturas) sit outside this order.** They
do not block any step. They decide whether certain *figures* are trustworthy, and
until they are answered those figures are reported as pending rather than as
numbers (R-C6). Answer them any time before reports are relied on.

### Track 2 — purchase orders

Independent of Track 1 and can run alongside it. Internal decision 1 (§13) is
whether it ships in the same delivery.

| # | Step | Delivers | Cannot start until | Done when |
|---|---|---|---|---|
| **P1** | **Requisition, quotes, approval — real.** Phases 1–3 of the existing screens, with data behind them and the competition rule enforced | R-D1 – R-D4 | **Q-6** · **Q-8** · **Q-9** | A requisition is raised, two quotes attached, one selected, approval routed by amount and given. Attempting to skip a quote is blocked, not warned |
| **P2** | **The purchase order itself.** Numbering, PDF, issue, send to supplier, immutability, status, search, export | R-D5 – R-D11 | P1 · **Q-7** | An OC is issued as a PDF, emailed to a real supplier, and found afterwards by number and by supplier. An issued OC cannot be edited |
| **P3** | **The Yunt joins in.** Drafts a requisition or an OC from a plain request, pre-fills supplier, last price and category from history, flags price jumps, new suppliers and duplicate requests | R-D12 – R-D14 | P2 (there must be an OC to draft) · Track 1 step 2 (the history reads) | A person asks for something in plain language, gets a draft with its evidence, corrects it, and issues it. The Yunt never issued anything itself |

### The shortest path to something Antillanca can use

Steps **1 → 2** alone already deliver a working capability against data that
exists today, with nothing written and nothing sent. If the schedule tightens,
that is what ships first.

---

## 3. Why this exists

Antillanca has a classifier that sorts invoice lines into 78 accounting
categories, and a dashboard that shows the result and lets a person confirm it.
Two gaps remain.

1. **New data has no way in.** Every batch so far was loaded by hand, by us.
2. **Buying is not represented.** The dashboard contains a seven-phase visual
   model of the purchase process — requisition, quotes, approval, consolidation,
   purchase order, receipt, payment — with a banner on every screen saying the
   figures are examples and nothing is connected.

The Yunt closes the first gap completely and the second partly.

### What already exists — the starting line

| | State today |
|---|---|
| Classifier service | Live. Takes a batch of lines, returns top-3 categories with a confidence score and a decision: settle it, or send it to a person. |
| Taxonomy | 78 accounting categories, in use. |
| Database | 11,746 invoice lines across 5,195 documents, loaded and worked. |
| Dashboard — analytics | Live. |
| Dashboard — line review | Live. A person confirms a category here. |
| Dashboard — purchase flow | **Demonstration only.** Seven screens, example figures, nothing behind them. |
| Roles | Six, with per-screen access already wired: Solicitante, Jefatura, Adquisiciones, Bodega, Finanzas, Admin. |
| Getting new data in | **Does not exist.** |

---

## 4. How work is organised: the case

Everything the Yunt does happens inside a **case** — one folder, one identifier,
openable by a person, exportable to an auditor.

| Case type | Opened by | Closed when |
|---|---|---|
| **Ingestion** | An email arriving with invoice data | The reception report is sent and its proposals are resolved |
| **Query** | A question by email or in the dashboard | The answer is delivered |
| **Purchase** | A requisition | The purchase order is issued, or the requisition is cancelled |

| ID | Requirement |
|---|---|
| **R-0.1** | Every case holds: the original request, the raw material it was given, the work done, what was delivered, the event record, and the signature of whoever approved anything applied. |
| **R-0.2** | A case's state is readable without running the system — by opening its folder. |
| **R-0.3** | Messages on any channel about the same case are written into that case, so the Yunt has the whole history regardless of where the conversation started. |
| **R-0.4** | **Precedent is read from the database through a tool, never from old cases.** The Yunt does not learn from its own previous output. |
| **R-0.5** | **A reply goes back to whoever wrote, with no approval step.** Approval is required for changing data and for anything reaching a supplier — never for answering the person who asked the question. |

---

## 5. Part A — Ingestion

**The promise:** Antillanca sends one email; the data is in the system.

| ID | Requirement |
|---|---|
| **R-A1** | A dedicated mailbox receives invoice batches. Only addresses on an agreed list are acted on. Anything else is recorded and ignored — never half-processed. |
| **R-A2** | **Format 1, preferred: a ZIP of SII electronic invoice XML**, exactly as Antillanca receives them, unmodified. Purchases and sales in separate folders inside the ZIP (`COMPRAS/`, `VENTAS/`) — the direction cannot be recovered from the file and the classifier requires it. |
| **R-A3** | **Format 2, fallback: a spreadsheet** (`.xlsx`/`.csv`) on a template we supply, for data with no XML. Columns: document type, folio, date, counterparty RUT and name, direction, line number, item text, description, quantity, unit price, line amount. A row missing a required column is rejected on its own and reported; it never fails the batch. |
| **R-A4** | Limits stated up front: 50 MB per email, 5,000 lines per batch. Both are configuration and can be raised. |
| **R-A5** | **Acknowledgement within 15 minutes**, saying how many documents and lines were read and how many were rejected, with reasons — sent even when everything failed. |
| **R-A6** | **Duplicates are detected, not re-loaded.** Same issuer RUT + document type + folio as something already held is reported and skipped. Sending the same email twice changes nothing. |
| **R-A7** | The original file is kept untouched as the case's evidence. |
| **R-A8** | New lines appear in the dashboard under the same review workflow used today. |

```
Email arrives  →  sender, format and size checked   → rejected? reply saying exactly why
               →  documents and lines read, duplicates removed
               →  lines sent to the classifier
               →  results stored: confident lines settled, the rest in review
               →  Reception Report sent (§6)
```

---

## 6. Part B — Classification assistance

About a third of lines land in review. Today a person works that pile alone.

### B1 · The reception report

| ID | Requirement |
|---|---|
| **R-B1** | One written report per batch, in Spanish: documents and lines received, settled automatically, sent to review, rejected with reasons, the total amount covered, and the date range. |
| **R-B2** | The report links into the dashboard. The email and the dashboard never disagree — both read the same data. |

### B2 · Findings — what the classifier cannot see

**A finding never changes a line.** It is information for a person.

| ID | The check |
|---|---|
| **R-B3** | **Arithmetic** — line amount ≠ quantity × unit price; document total ≠ sum of its lines; tax inconsistent with net. |
| **R-B4** | **Structural** — zero or negative amounts; missing or malformed RUT; a date outside the period the batch claims; an unrecognised document type. |
| **R-B5** | **Duplication** — the same folio twice in the batch, or already held. |
| **R-B6** | **Outliers against history** — a unit price far outside what that item has cost before; a document far larger than anything previous from that supplier; a supplier never seen. Reported *with* the comparison: the item, its usual range, the value observed. |
| **R-B7** | **Direction conflicts** — a category that can only apply to the opposite direction. |
| **R-B8** | Every finding names the document and line, the check, the expected value and the observed one. The Yunt reports what is inconsistent; never why. |

### B3 · Opinions on lines in review

The highest-value capability, and the one needing the tightest definition.

| ID | Requirement |
|---|---|
| **R-B9** | For a line in review, the Yunt may **propose** a category when it can support the proposal: previously confirmed lines with materially the same text, and/or a written Antillanca convention on file. |
| **R-B10** | A proposal always shows its evidence in plain language — *"12 previous lines reading 'MANGUERA 2\"' were confirmed into EXP-14.3."* No evidence, no proposal: the line stays in review, untouched. |
| **R-B11** | Proposals are **grouped**. Lines sharing the same reasoning arrive as one item with a count and a total, so approving is one decision rather than fifty. |
| **R-B12** | Three states, always stated: **confident** (strong precedent), **uncertain** (weak or conflicting — shown and flagged), **your call** (no basis — no proposal offered). |
| **R-B13** | **Nothing is applied without approval** from a named person. |
| **R-B14** | On approval the Yunt applies **exactly the approved lines and nothing else**. All of them are written or none are, and it says which. |
| **R-B15** | Every applied change is recorded permanently: lines, previous category, new category, evidence, approver, timestamp. Exportable. |
| **R-B16** | After applying, the Yunt confirms in writing what changed. Nothing is applied silently. |
| **R-B17** | Any applied group can be **undone as a unit**, restoring the previous categories. The undo is itself recorded. |

### B4 · Learning from corrections

| ID | Requirement |
|---|---|
| **R-B18** | When a person overrules a proposal, the correction is captured with its reasoning as a **proposed change to the Yunt's written conventions** — not applied silently. |
| **R-B19** | A correction takes effect only when the boss approves it, and a test case is added at the same time so the same mistake cannot come back. |

---

## 7. Part C — Reports and queries

| ID | Requirement |
|---|---|
| **R-C1** | A question can be asked in Spanish by email or in the dashboard, and gets a written answer with figures. |
| **R-C2** | A list arrives as **XLSX**; a formatted report as **PDF**; a single figure in the message body. |
| **R-C3** | Every answer states the exact filter used — period, direction, categories, suppliers — and the data cut-off, so a figure can be reproduced. |
| **R-C4** | The same question on the same data returns the same number. |
| **R-C5** | **Recurring reports**, a fixed small set: a month-end summary, a digest after each ingestion, and a weekly list of what is still in review. Antillanca chooses which are on and who receives them. |
| **R-C6** | When the data cannot answer, the Yunt says so and says what would be needed. It never estimates and presents the estimate as a figure. |

**Answerable, because the data exists:** spend and income by category, supplier, document type and period · counts and totals by state · supplier concentration · price history for an item · period-over-period comparison with what moved and by how much · filtered listings and exports (*"every line in review over CLP 1,000,000 in August"*) · unusual values as defined in R-B6.

**Refused, with the reason given:** payment status, overdue, cash flow (no payment data) · stock on hand (no inventory data) · budget versus actual (no budget loaded) · *why* a figure moved (the Yunt will not invent a business cause).

---

## 8. Part D — Purchase orders

### 7.1 What a purchase order is, and why it belongs here

A purchase order (*Orden de Compra*, OC) is the document the **buyer** issues to a
supplier **before** anything is bought: what is ordered, how much, at what price,
delivered where and when, against which internal account. The invoice is its
mirror — the supplier's document, issued after. The OC is the commitment; the
invoice is the claim against it.

Two consequences matter here:

1. **The OC carries the accounting category before the money is spent.** Today
   the category is recovered afterwards, by a model, from the wording of an
   invoice line. A purchase that began as an OC already has a category chosen by
   a person — so the invoice arriving against it does not need to be guessed at.
   This is what makes purchase orders part of *this* product rather than a
   separate one.
2. **The OC is the control.** Without one, the only question anyone can ask of an
   invoice is "does this look right?" With one, it is "did we order this, at this
   price?"

### 7.2 Which phases become real

| Phase | v1 |
|---|---|
| 1 · Requisition (*levantamiento*) | **Yes** |
| 2 · Quotes (*cotización*) | **Yes** |
| 3 · Approval (*aprobación*) | **Yes** |
| 4 · Consolidation (*unión*) | No — §9 |
| 5 · Purchase order (*orden de compra*) | **Yes** |
| 6 · Receipt and SII (*recepción*) | No — §9 |
| 7 · Match and payment (*pago*) | No — §9 |

| ID | Requirement |
|---|---|
| **R-D1** | **Requisition.** An authorised user records what is needed, why, urgency, product or service, one-off or recurring, and cost centre. Editable until submitted. |
| **R-D2** | **Quotes.** Supplier quotes attach as files, each with supplier, net amount and delivery time. One is selected, with a recorded reason. |
| **R-D3** | **The competition rule is enforced, not displayed.** Above an agreed amount — the demo screen currently shows CLP 500,000 (Q-6) — a requisition cannot reach approval with fewer than two quotes. |
| **R-D4** | **Approval** routed by role and amount against an agreed threshold table. Approve, reject with a reason, or return with observations. Each action recorded with person and time. |
| **R-D5** | **The document.** The OC is generated as a PDF: OC number, issue date, Antillanca's details, supplier and RUT, lines with quantity, unit price, net, tax and total, delivery address and date, payment terms, cost centre, accounting category per line, approver. |
| **R-D6** | **Numbering is sequential and gap-free.** A cancelled OC keeps its number, marked cancelled. Numbers are never reused. |
| **R-D7** | **Issue and send.** An authorised person issues it; it is emailed to the supplier with the PDF and stored. Sends and re-sends are recorded. |
| **R-D8** | **An issued OC is immutable.** Changing it means cancelling and issuing a replacement that points back to it. |
| **R-D9** | **Status is always visible** — draft → pending approval → approved → issued → closed / cancelled / rejected — and every OC is findable by number, supplier, requester, cost centre, category, date or status. |
| **R-D10** | **Every OC line carries an accounting category** from the same 78-category taxonomy. This is what lets a later invoice be matched to its OC instead of classified from scratch. |
| **R-D11** | An OC exports to PDF; lists of OCs export to XLSX. |

### 7.3 What the Yunt does here

| ID | Requirement |
|---|---|
| **R-D12** | **Drafts** a requisition or an OC from a plain-language request, pre-filling supplier, last price paid and accounting category from purchase history — each shown with the evidence used. |
| **R-D13** | **Flags before approval:** a price materially above history for that item; a supplier not used before; a requisition duplicating one already open. |
| **R-D14** | **Never approves and never issues.** Both are human actions by an authorised role. The Yunt prepares; a person signs. |

---

## 9. Explicitly not in v1

| Not included | Why |
|---|---|
| Goods receipt, dispatch notes, SII invoice validation (phase 6) | Needs an SII integration we do not have |
| Three-way match and payment authorisation (phase 7) | Needs phase 6 first, plus treasury and bank data |
| Consolidating requisitions across suppliers (phase 4) | Only worth building once real OC volume exists |
| Inventory and stock levels | No inventory data |
| Budget versus actual | No budget loaded (Q-9) |
| A supplier-facing portal | Suppliers receive email |
| Retraining the classifier on newly ingested data | Ingestion feeds the database; retraining stays a separate, deliberate exercise |
| WhatsApp | Mail and the dashboard first |
| Acting on its own initiative | Every action starts from an email, a schedule Antillanca configured, or a person in the dashboard |
| A direct connection to Antillanca's accounting or ERP system | Email in; email and dashboard out |

---

## 10. What is gated, and who holds the gate

Gates are listed here because Rodrigo's note is explicit that loosening one is
his decision, not an engineering default. This is the capability contract: what
the Yunt can do at all, and what it cannot do without a signature.

| What it can do | Gate |
|---|---|
| Read invoice lines, documents, categories, conventions, purchase history | none |
| Run the classifier over a batch | none |
| Compute a figure, build a list, build a report | none |
| Draft a proposal, a reply, a requisition, an OC | none — a draft has no effect |
| **Apply an approved category change** | **a named person's approval, bound to that exact proposal** |
| Reply to the person who wrote to it | none — the answer goes back to whoever asked, and to nobody else |
| **Send anything to a supplier** | **never automatic — a person issues it** |
| **Change its own conventions or limits** | **the boss** |
| Cancel a scheduled report or a pending draft | none — removing a future effect is always safe |

### Guarantees

| ID | |
|---|---|
| **G-1** | Never changes accounting data without a named approval, and applies only what was approved. |
| **G-2** | Every change is reversible and permanently recorded — what changed, from what, to what, on whose approval. |
| **G-3** | **Never invents a figure.** A number is **verified** only when a tool computed it from the data and the case holds that result. Anything the model merely stated is marked as such and is never presented as a figure. |
| **G-4** | Never asserts a business cause. It reports what changed and by how much. |
| **G-5** | Uncertainty is stated. A weak proposal is labelled weak; no basis means no proposal. |
| **G-6** | A suggestion is never presented as settled while the line is still in review. |
| **G-7** | Only listed senders are acted on. Text inside an invoice, an attachment or a forwarded message is data, never an instruction. |
| **G-8** | Volume limits are fixed and account-wide — messages per period, lines per proposal. Hitting one stops and reports; it never proceeds quietly. |
| **G-9** | **Failure is visible.** A batch that fails, a schedule that does not fire, a proposal that cannot apply — each produces a message. Silence never means success. |

---

## 11. What we need from Antillanca

Each blocks only the item beside it.

| ID | Decision | Blocks |
|---|---|---|
| **Q-1** | Which addresses may send data, and which receive reports | R-A1, R-C5 |
| **Q-2** | Which format they will send, and confirmation that purchases and sales can be kept separate | R-A2, R-A3 |
| **Q-3** | Who may approve a category change, and whether one approver is enough | R-B13 |
| **Q-4** | **How credit notes should count.** 103 of them, CLP 87,885,532, currently held as positive amounts. Does a credit note reduce the period it was issued in, or the period of the invoice it cancels? Until answered, any figure it touches is reported as pending rather than as a number | R-C1, R-C6 |
| **Q-5** | **How *liquidación factura* (type 43) should count** — 29 documents, CLP 292,085,987 — where the underlying sale may already be recorded separately. Same treatment until answered | R-C1, R-C6 |
| **Q-6** | The approval threshold table for purchases, and confirmation of the two-quote threshold | R-D3, R-D4 |
| **Q-7** | The official OC template, legal wording and Antillanca's issuing details | R-D5 |
| **Q-8** | The supplier list — RUT, name, contact email, payment terms — or permission to derive it from invoice history and have Antillanca correct it | R-D2, R-D7 |
| **Q-9** | Cost centres, and the budget per cost centre if budget checking is wanted later | R-D1, §9 |
| **Q-10** | **The July–August 2026 invoices Antillanca already categorised.** Offered previously and never collected. The single highest-value input available, and it directly improves every proposal the Yunt makes | R-B9 |
| **Q-11** | The Yunt's name and register | Persona |

---

## 12. Acceptance

| Part | Accepted when |
|---|---|
| **A · Ingestion** | Antillanca emails a real batch and, with no manual step by us, gets an acknowledgement, then a reception report, and finds the new lines in the dashboard. |
| **B · Assistance** | For that batch the Yunt reports findings, proposes categories with evidence for at least one group, Antillanca approves one group, and exactly those lines change — checked against the record. Undo restores them. |
| **C · Reports** | Antillanca asks three questions of its own choosing and gets correct, reproducible answers with the filters stated; a question outside the data is refused with an explanation. |
| **D · Purchase orders** | A requisition is raised, quotes attached, approval routed and given, an OC issued as a PDF and emailed to a supplier, and found afterwards by number and by supplier. |

Before the first real case, the test set includes a **trap**: a request whose
data is missing. Passing means the Yunt asks. Inventing anything is a failure.

---

## 13. Open for internal decision before this goes to the client

1. **One delivery or two?** Ingestion and classification assistance are one
   continuous flow and should ship together. Purchase orders are independent and
   could be a second delivery.
2. **Is the two-quote threshold ours to propose or Antillanca's to state?** The
   demo screen already shows them CLP 500,000.
3. **Does approval by email reply satisfy the audit expectation, or must every
   approval happen in the dashboard where the person is authenticated?** The most
   consequential question in this document — it decides whether mail is a full
   channel or only a notification channel.
4. **Is the success metric in §1 the right one to be measured on?** It is the
   only number in this document we would be held to.
