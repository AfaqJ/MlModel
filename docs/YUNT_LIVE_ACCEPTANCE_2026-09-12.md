# Yunt live acceptance report — 2026-09-12

This is the current, shipped behaviour observed in the real Outlook threads.
Earlier replies that appear in those threads but are called out as pre-fix below
are historical defects, not the behaviour to demonstrate.

| Capability | What was asked | Observed final behaviour | Result |
|---|---|---|---|
| Invoice intake | A ZIP with new folios `999201`–`999206` | Reception reported 6 new documents, 7 lines and 1 mismatch. | Passed |
| Review and proposals | Review that new batch | One grouped findings email gave 3 concrete flags and 4 unapplied category proposals, each with grounded prior-record evidence. | Passed |
| Category governance | Approve, reject, correct, undo | Exact first-line approval applied live changes; rejection did nothing; an unsuggested category was restated before applying; undo restored all four original values. | Passed |
| Spend questions | 2025 fuel spend and monthly artefacts | The answer matched an independent recount to the peso (CLP 93,146,229). The delivered spreadsheet, PDF and chart were opened and inspected: data and totals were correct, months chronological, attachment formats genuine. | Passed |
| Refusal | A question outside the available data | The agent refused rather than invented an answer and wrote a real refusal record. | Passed |
| Purchase request by email | “20 sacos de sal mineral … Fundo Raíces” with an incomplete date | It asked for the missing year, then previewed all facts and waited for `SÍ, ADELANTE`. Only then it created `SOL-2026-0001`; it explicitly said this was open, not an order, and no supplier was contacted. | Passed |
| Purchase order by email | Quote Agro Uno, 20 × CLP 30,000, delivery 2026-10-30 | It drafted the exact CLP 600,000 order and waited for confirmation. With one quote it refused using the two-quotation rule, without workaround. After `Agro Dos` at CLP 620,000 was recorded, it re-staged Agro Uno. Exact confirmation created `OC-2026-0001`; the request moved to `ordered`. | Passed |

## Representative current replies

- Missing data: “¿para qué año es el 30 de octubre?” — it did not invent a date.
- Before a purchase request: “Esto crea una solicitud abierta; no crea una orden ni contacta a un proveedor.”
- Two-quote refusal: “El sistema exige dos cotizaciones cuando el monto supera CLP 500.000 …”
- Completed order: “El PDF se descarga desde el panel; Antillanca lo envía directamente al proveedor.”

## Historical defects found during acceptance, now fixed

- Proposal lookup compared a Resend UUID with an RFC Message-ID, so live lookup had never worked (D-081).
- Client-facing category evidence showed model filler rather than the actual precedent.
- Report line breaks, chart ordering, chart truncation and a promised-PDF/SVG mismatch were invisible to automated checks; opening the attachments exposed them.
- Purchase threads lost the request identity after an intermediate reply and after the two-quote refusal. The branch preview now walks the reply chain and preserves the pending order's request id. The second quote test above is the live proof.

## How to demonstrate safely next time

Use a small synthetic batch for deterministic flags and guardrails. For category-quality testing, use a small, contiguous set of human-confirmed real rows as a held-out set: back up first, remove both the invoice and its lines so dedup does not block re-ingest, then restore exactly to baseline. This tests the full pipeline against a known answer key; catalog aliases may still supply context, so it is not a cold-start test. Every test row must be tagged and removed after acceptance.

## Scope and remaining work

`MCT-149`, `MCT-141`, `MCT-160`, `MCT-150`, `MCT-152`, `MCT-156`, and
`MCT-157` have live evidence and are Done. `MCT-153` remains open: it has a
real refusal, but its completion criterion requires a product change built from
the refusal list. The quotation-authenticity ticket is deliberately separate.
