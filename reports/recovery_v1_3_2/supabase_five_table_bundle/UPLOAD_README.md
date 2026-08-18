# v1.3.1 Supabase bundle (local only)

This bundle matches the current five-table schema. It contains natural keys because local data cannot know Supabase-generated UUIDs. A future importer must resolve category code, company RUT, invoice `(seller_rut, document_type, invoice_folio)`, and catalog `(item_name, description)` keys.

Before changing remote data, export/backup the five tables. In one transaction: upsert categories, companies, catalog and all 5,195 invoice headers; resolve UUIDs; upsert the 11,766 retained item lines; then delete only the explicit 440 keys in `reconcile_delete_junk_lines.jsonl`. Roll back the transaction if any count/hash/invariant differs from `manifest.json`. The 29 DTE-43 Liquidacion invoices and their 103 genuine livestock lines are retained, but those lines remain review-required until the client supplies the correct purchase-side accounting category.
