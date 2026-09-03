# Canonical catalog migration payload

Status: **applied to production Supabase on 2026-08-26. All three steps complete.**

`002_apply_canonical_catalog.sql` was **not** the file that ran — it is 2.6 MB,
which the Supabase SQL editor will not take, and this project holds no Postgres
connection string. It was split into three idempotent steps (D-045):
`003_step_a_schema.sql` (SQL editor, done), a PostgREST apply script (run 2026-08-26, since deleted)
(PostgREST, done), and `004_step_c_unique_index.sql` (SQL editor, done — it
returned `4029 | 11746 | 8` and created `item_catalog_normalized_name_uidx`).
`002` is kept as the generated reference.

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

## What remains

Run `004_step_c_unique_index.sql` in the Supabase SQL editor. It creates the
unique index on the normalized `item_name` — replacing the `(item_name,
description)` constraint step A dropped so the 3,366 renames could proceed — and
runs the referential `left join`. Its success is the proof the migration
completed: if a duplicate normalized name survived, the index cannot be created
and the statement fails naming the collision. Do not force it through.

The pre-migration backup is `backups/supabase_20260825T190718Z/` (all 5 tables,
row counts verified against the server). To revert: restore `item_catalog` from
it and reset each line's `catalog_item_id` from `current_catalog_item_id` in
`invoice_item_catalog_mapping.jsonl`.

Git pushes and the frontend merge remain a separate approval.
