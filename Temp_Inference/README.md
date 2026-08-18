# Temporary Supabase Inference Loader

This folder contains a temporary data-loading script. It is not part of the
FastAPI model service. It parses raw SII DTE XML files, calls the local
`/predict-batch` endpoint, applies a conservative loader-level decision policy,
and upserts rows into Supabase.

## Secrets

Create `Temp_Inference/.env.loader` with:

```text
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SECRET_KEY=your-server-side-secret-key
```

The env file is ignored by git.

## Start Local Inference

Run this in one terminal:

```bash
cd /Users/afaq/Desktop/Mctech/ML-model
.venv-backend/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Smoke Run

Run this before writing to Supabase:

```bash
.venv-backend/bin/python Temp_Inference/classify_raw_invoices_to_supabase.py \
  --limit 1000 \
  --dry-run \
  --threshold-report
```

This writes local reports:

```text
Temp_Inference/threshold_report.csv
Temp_Inference/review_samples.csv
Temp_Inference/smoke_predictions.jsonl
Temp_Inference/loader_errors.jsonl
```

## Small Real Write

```bash
.venv-backend/bin/python Temp_Inference/classify_raw_invoices_to_supabase.py --limit 100
```

## Full Run

```bash
.venv-backend/bin/python Temp_Inference/classify_raw_invoices_to_supabase.py
```

## Normalize Existing Labels

The normalized migration does not rerun inference. It reads the already-loaded
`line_item_predictions` rows and splits them into:

```text
categories
invoices
invoice_items
```

First run the schema in Supabase SQL Editor:

```text
Temp_Inference/normalized_schema.sql
```

Then dry-run the migration locally:

```bash
.venv-backend/bin/python Temp_Inference/migrate_to_normalized_tables.py
```

If the dry run is clean and the tables exist, write the normalized rows:

```bash
.venv-backend/bin/python Temp_Inference/migrate_to_normalized_tables.py --write
```

## Defaults

- Raw XML folders: `data/Raw_Data/dte_96685810_COMPRAS` and `data/Raw_Data/dte_96685810_VENTAS`
- Local API: `http://127.0.0.1:8000`
- Batch size: `500`
- Loader auto-accept top-1 threshold: `0.75`
- Loader auto-accept margin threshold: `0.50`

The database generates `id`, `invoice_period`, and `needs_review`, so the script
does not send those columns.

## Company + Item Catalog Migration

This migration does not rerun inference. It reads the safety snapshot in:

```text
Temp_Inference/snapshots/normalized_before_company_item_split/
```

Then it parses raw XML again to add company, invoice total, quantity, unit,
unit price, discount, tax, and item-code fields.

Run the dry run first:

```bash
python3 Temp_Inference/migrate_to_company_item_schema.py
```

Expected dry-run counts from the current snapshot:

```text
categories: 71
companies: 460
item_catalog: 5,579
invoices: 5,157
invoice_items: 12,071
auto_accept: 6,356
review_required: 5,715
```

After the old normalized tables have been dropped and the new schema has been
created with:

```text
Temp_Inference/normalized_company_item_schema.sql
```

write the migrated rows:

```bash
python3 Temp_Inference/migrate_to_company_item_schema.py --write
```
