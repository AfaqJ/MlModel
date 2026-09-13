# Yunt live acceptance — 13 September 2026

## Purpose

Final live proof for the two reopened deliverables: formatted report attachments
(`MCT-152`) and email-driven purchase orders (`MCT-157`). All messages were
sent by the permitted test sender to the deployed Yunt. This is an evidence
record, not a test plan.

## Purchase order by email

1. A neutral email requested **20 bags of mineral salt for Fundo Raíces on
   2026-10-30**. Yunt proposed a purchase request; direct `SÍ, ADELANTE`
   created `SOL-2026-0002`.
2. An email recorded one telephone quotation from Agro Uno: **CLP 30,000 per
   bag, CLP 600,000 total**. The order was above the CLP 500,000 threshold, so
   it was not issued with one quote. This exposed an unanswered expected
   preflight path.
3. The narrowly-scoped repair in preview commit `8bec6c2` converts that known
   preflight into a short request for the second quotation. Its regression
   script proves the old raw-error behavior fails the check.
4. A second telephone quotation from Agro Dos was recorded at **CLP 31,000 per
   bag, CLP 620,000 total**. Yunt proposed the exact Agro Uno order:
   20 bags × CLP 30,000, delivery 2026-10-30.
5. A direct reply containing only `SÍ, ADELANTE` created `OC-2026-0002`, closed
   the request, and returned an email with `OC-2026-0002.pdf` attached to the
   requester. Yunt did not contact the supplier.

## Report attachments by email

Three fresh live emails asked for purchases grouped by month during 2025.

| Requested output | Returned attachment | Result |
|---|---|---|
| Spreadsheet | monthly-purchases XLSX | Received in the live reply. The generator's rendered workbook was visually checked: title band, criteria, readable widths, frozen header, formatted amounts. |
| PDF report | `compras-2025-por-mes-2026-09-13.pdf` | Received in the live reply. Rendered PDF visually checked: branded header, criteria, summary cards, table, footer. |
| Line chart | `compras-mensuales-2025-2026-09-13.svg` | Received in the live reply. The live response states month grouping; the generator is checked to retain chronological ordering rather than sorting by value. |

The actual figures are queried by code. The model selects a supported output,
but does not supply the numbers in a file.

## Rollback

`python3 scripts/90_yunt_live_test_undo.py --apply --sender
afaq@mctechstudio.com` removed the nine test inbound requests, one purchase
request, two quotations and one order. It then verified every tracked table at
its saved baseline, including zero Yunt test artifacts and no production invoice
change.
