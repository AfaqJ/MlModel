# Catalog matching proposal

Status: schema and data payload prepared; future ingestion matching is logged
but intentionally not implemented.

## Ownership and current system boundary

Catalog matching belongs in the **backend ingestion path**, immediately before
an invoice line is written to Supabase. The frontend only reads and displays
catalog IDs; making it choose IDs would duplicate business rules in browsers
and would not cover imports that bypass the UI.

Today this repository has no online Supabase ingestion writer. Cloud Run's
`/predict-batch` route is a stateless accounting-category classifier: it returns
predictions and does not insert invoice rows. The repository's Supabase writers
are offline release/correction scripts. Therefore the future matcher must be
added to, or called by, the real ingestion writer once that component is
identified. It should not be bolted onto the frontend or silently added to
`/predict-batch` before the write flow is known.

## Minimal persisted model

`item_catalog` remains the user-facing canonical catalog. One new table,
`item_aliases`, stores only meaningful alternate wording:

- `alias_id` — stable UUID;
- `catalog_item_id` — the canonical catalog row;
- `alias_name` and generated case/spacing-insensitive `normalized_alias`;
- optional `company_id` for supplier-specific meanings.

The initial table has eight aliases: fuel abbreviations/brand wording plus the
COPEC-specific description `GASOLINA NU 1203`. `DETALLE`, `ITEM`, `MATERIALES`,
individual `SEGUN OT 81/82/...` strings, nail sizes, electricity quantities and
monthly installment strings are not reusable aliases.

## Proposed resolver order

For a future invoice line, preserve the received item name and description
first. The resolver then returns a suggestion; it never rewrites that evidence.

1. Exact case/spacing-normalized canonical name.
2. Exact supplier-scoped alias, checked against item name and description.
3. Exact global alias, checked against item name and description.
4. An approved, narrow pattern that removes only known volatile data and
   retains the actual identity. Example: `SEGUN OT <number>` for Multimotos;
   installment/month patterns must retain the contract or equipment identity.
5. Fuzzy similarity only to retrieve review candidates.

Do not create a generic rule that strips all numbers. `93`, `95`, `97`, vehicle
plates, contract IDs, models and grades can define identity. Specification
patterns must be product-family-specific and added only after examples are
approved.

A useful backend result shape is:

```json
{
  "suggested_catalog_item_id": "uuid-or-null",
  "match_type": "canonical_exact | alias_supplier | alias_global | pattern | fuzzy | none",
  "reason": "human-readable evidence",
  "requires_review": true
}
```

Exact canonical/alias matches may later be made automatic once ingestion
ownership and conflict handling are confirmed. Pattern and fuzzy matches should
start as suggestions exposed by the backend for review.

