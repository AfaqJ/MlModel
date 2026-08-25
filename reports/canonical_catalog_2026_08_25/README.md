# Canonical catalog migration payload

Status: **generated and locally validated; not applied to Supabase**.

This directory is the complete review payload for the approved 2026-08-25
catalog cleanup. It reduces 5,411 catalog rows to 4,029 while keeping all
11,746 invoice lines and every original `item_text` and `description` intact.

## Files

- `item_catalog.jsonl` — the complete proposed canonical `item_catalog`.
- `item_aliases.jsonl` — eight meaningful alternate wordings. It deliberately
  excludes case-only variants, dimensions, quantities, months and OT numbers.
- `invoice_item_catalog_mapping.jsonl` — one audit row per invoice line, with
  its old ID, new canonical ID, canonical name and original evidence.
- `invoice_items.jsonl` — complete post-migration invoice-line payload. Only
  `catalog_item_id` differs from the snapshot.
- `001_item_aliases_schema.sql` — schema proposal in isolation.
- `002_apply_canonical_catalog.sql` — one transactional migration containing
  preflight guards, schema, remapping, catalog cleanup, aliases and post-checks.
- `manifest.json` — counts, invariant results and payload checksums.

## Verified result

The generated SQL was run against a disposable PostgreSQL 18 database seeded
from the fresh read-only Supabase snapshot. It committed successfully with:

| Check | Result |
|---|---:|
| Canonical catalog rows | 4,029 |
| Invoice lines | 11,746 |
| Aliases | 8 |
| Catalog rows removed | 1,382 |
| Raw item/description SHA before and after | identical |
| Missing or invalid catalog references | 0 |

Approved examples in the migrated database: `Gasolina 93` 691 lines,
`GASOLINA` 50, `Clavos` 89, `Tirafondos` 8, `Materiales` 3, `SEGUN OT` 22,
`Aplicación de cal` 6 and `Tractor de jardín John Deere S140` 1.

## Production gate

Do not execute the SQL from this directory yet. Before production, take a new
backup and snapshot. The SQL refuses to run if the 11,746 line IDs, their old
catalog IDs, `item_text`, or `description` differ from this payload. If the
database changed, regenerate the payload from the new snapshot instead of
weakening the guard.

After Afaq explicitly approves the data migration, run
`002_apply_canonical_catalog.sql` as one transaction and independently recheck
the manifest invariants. Git pushes and the frontend merge remain a separate
approval.

