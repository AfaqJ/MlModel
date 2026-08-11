# MCT-37 Antillanca Invoice Classifier - Complete Context Handover

Last verified: 2026-08-11

Working directory:

```text
/Users/afaq/Desktop/Mctech/ML-model
```

This document replaces the earlier Codex attachment handover. The earlier handover
described the state before full inference and before the Supabase normalization work.
This file records the current implementation, production data, known failures, and the
recommended recovery sequence.

## 1. Read This First

The current `v1.1.0` model is deployed and technically operational, but it is not safe to
present all of its raw top-1 predictions as confirmed classifications.

The immediate production incident is:

- all 125 `VENTAS` line items in the stored inference run received an `EXP-*` prediction;
- all 125 were correctly marked `review_required` and have `final_code = null`;
- the customer-facing layer nevertheless displayed the preliminary `predicted_name` as if
  it were a final category;
- `VENTA DE LECHE` was not a trained class in the deployed model at all;
- the validation set contained zero income (`ING-*`) examples, so the published aggregate
  validation metrics did not test the client's core revenue lines.

Do not solve this only by lowering or raising the confidence threshold. The incident has
multiple causes: gold-data promotion, rare-class training, missing transaction context,
missing deterministic sales rules, missing business regression tests, and UI misuse of
the prediction/review contract.

## 2. Project Purpose

This project classifies Chilean SII DTE invoice line items for Antillanca, a dairy and
agricultural business, into a 71-category accounting taxonomy.

Examples:

```text
EXP-2.3  Vacunas
EXP-11.3 Petroleo
EXP-14.1 Mantencion Caminos
ADM-1.4  Movilizacion
ING-0.1  VENTA DE LECHE
```

The intended product behavior is human-in-the-loop:

```text
parsed invoice line
  -> deterministic meter/product/business rule when available
  -> semantic classifier for the remaining long tail
  -> confidence and review decision
  -> final code only after auto-accept or human review
```

The ML service is stateless. Supabase owns invoices, line items, predictions, review state,
and final classifications.

## 3. Repository And Worktree State

Git state at handover creation:

```text
branch: main
HEAD: a60e43f Package v1.1.0 backend and model
origin/main: a60e43f
```

Pre-existing uncommitted work must not be reset:

```text
M  .gitignore
M  tests/test_api.py
?? Temp_Inference/
?? call_graphs/
```

The `.gitignore` change protects `Temp_Inference/.env.loader`, generated reports, and
snapshots. The test change makes the expected model version come from the model card rather
than hard-coding `v1.0.0`.

Verification performed on 2026-08-11:

```text
.venv-backend/bin/python -m pytest tests -q
6 passed in 3.67s
```

The current tests are backend smoke tests only. They do not test the sales categories,
transaction-direction invariants, full batch behavior, or customer-facing final-code
semantics.

## 4. Important Directory Map

```text
app/                         FastAPI inference service
app/api/                     API routes and Pydantic contracts
app/core/                    settings, lazy model loader, runtime dependencies
app/inference/               ONNX encoder, LR classifier, lookups, confidence logic
app/data/                    production lookup CSV files

Data/Raw_Data/               original COMPRAS and VENTAS DTE XML files
Data/processed/              extracted line-item CSV
Data/gold/                   audited training source of truth and generated views
Data/silver/                 Ollama/Qwen candidate labels and audit state
Data/stale/                  archived labeling/recovery scripts and intermediate runs
Data/current_context_*/      taxonomy and client-authored rule context

training/                    SetFit train/export code, model maps, logs
models/setfit_base/          full local PyTorch SetFit body + sklearn head
artifacts/v1.1.0/            deployed ONNX int8 artifact bundle
tests/                       backend API smoke tests

Temp_Inference/              temporary XML inference and Supabase migration tooling
Temp_Inference/snapshots/    safety snapshot from the intermediate normalized schema
```

The capitalization in the repository is `Data/` and `Temp_Inference/`. Some scripts use
lowercase `data/`; this works on the current default macOS filesystem but should be fixed
before running on a case-sensitive Linux filesystem.

## 5. Raw And Labeled Data Inventory

### 5.1 Raw XML

```text
Data/Raw_Data/dte_96685810_COMPRAS/  5,107 XML files
Data/Raw_Data/dte_96685810_VENTAS/      88 XML files
Total files                            5,195
```

The current XML parser finds 5,166 DTE documents in those files. Some files are wrappers or
otherwise contain no retained DTE document.

### 5.2 Extracted line items

`Data/processed/line_items.csv` contains:

```text
COMPRAS  11,978 rows
VENTAS      125 rows
Total    12,103 rows
```

Columns in that earlier extraction are:

```text
row_id, source, period, source_file, folio, nro_lin_det,
nmb_item, dsc_item, mnt_item, rzn_soc_emisor, giro_emisor, farm
```

The newer migration parser extracts substantially more invoice and line-level fields
directly from XML; see the database section.

### 5.3 Gold training data

Source of truth:

```text
Data/gold/_master_gold.csv
```

Current contents:

```text
rows:                 1,733
taxonomy categories:     71
categories represented:  70
categories with zero:      1
categories under 2:        5 (including the zero category)
categories under 15:      28
categories at least 15:   43
```

Gold sources:

```text
client_product_rule       577
direct_client_example     128
client_service_rule         7
file_audit                384
file_audit_corrected       15
silver_audit              622
```

Gold columns:

```text
gold_id, category_code, leaf, source, item_text, description,
provider, farm, audit_reason, verify_flag
```

Per-category CSVs inside `Data/gold/` are generated views. Do not edit those view files as
the source of truth. Change `_master_gold.csv`, then rebuild views.

### 5.4 Silver data

The current per-category silver files contain:

```text
total rows:          1,672
audited rows:        1,076
nonblank verdicts:   1,076
REJECT verdicts:        64
```

Important columns:

```text
candidate_id, item_text, description, provider, giro, source,
source_file, folio, siblings, top1_conf, audited, verdict, audit_reason
```

Ollama/Qwen labels were candidate labels, not automatically trusted gold. Audited verdicts
were intended to be promoted to gold under `LABELING_RULES.md`.

## 6. Labeling Pipeline History

The active top-level scripts are limited:

```text
scripts/10_extract_line_items.py
scripts/50_build_gold_views.py
scripts/51_build_silver_structure.py
scripts/55_contradiction_audit.py
scripts/60_build_product_lookup.py
```

Many scripts used to construct and audit silver were archived under:

```text
Data/stale/scripts_labeling_pipeline_2026_07_03/
```

That archive includes Ollama silver labeling, targeted/semantic recovery, two-step audits,
promotion, candidate-pool construction, and open-class classification.

The important historical flow was approximately:

```text
raw DTE XML
  -> extracted line items
  -> targeted/semantic candidate retrieval
  -> Ollama/Qwen top-3 proposal
  -> independent audit/reassignment
  -> silver audit ledger
  -> conservative promotion to recovered gold
  -> Data/gold/_master_gold.csv
  -> generated per-category views
  -> contradiction audit
  -> SetFit training
```

### 6.1 Confirmed promotion defect

The historical promotion script is:

```text
Data/stale/scripts_labeling_pipeline_2026_07_03/48_promote_starving_audit.py
```

It deduplicated promoted rows using:

```python
(normalized_item_text, category_code)
```

It ignored description, provider, transaction direction, source invoice, and category
coverage requirements. As a result, many legitimate repeated invoices with the same item
name but different descriptions collapsed to one gold example.

This was the direct cause of the Milk Sales coverage failure:

```text
raw VENTA DE LECHE rows:                       47
silver rows correctly audited as ING-0.1:     47
gold ING-0.1 rows after promotion:              1
deployed classifier contains ING-0.1:          no
```

The deduplication rule was appropriate for avoiding accidental repeated samples but unsafe
because it could starve an entire class. A future promotion pipeline must separately handle:

1. exact duplicate records;
2. repeated business events with useful contextual variation;
3. minimum class coverage;
4. held-out validation coverage;
5. transaction-direction consistency.

## 7. Current Model

### 7.1 Architecture

The actual model is:

```text
SetFit contrastive fine-tuning
base encoder: sentence-transformers/paraphrase-multilingual-mpnet-base-v2
classifier head: sklearn LogisticRegression
serve-time encoder: ONNX Runtime, dynamically quantized int8
deployed artifact version: v1.1.0
```

SetFit does fine-tune the sentence-transformer body. It is not a frozen generic encoder.
The logistic-regression head is then fitted on embeddings from the fine-tuned body.

Model input for `v1.1.0`:

```text
item_text | description | provider
```

Rules:

- blank fields are omitted;
- numeric-only descriptions are omitted;
- provider giro is not used by the selected base variant;
- transaction type is not included;
- invoice metadata is accepted by the API but ignored by the predictor.

### 7.2 Training implementation

Training code:

```text
training/train_setfit.py
```

Training run:

```text
gold rows available:      1,733
train rows:               1,389
validation rows:            340
trained classes:              66
max SetFit steps:           1,500
batch size:                     8
training time:             21.6 minutes
```

Classes with fewer than two examples were excluded before training:

```text
ADM-1.9
ING-0.1
ING-0.3
ING-0.6
```

`ING-0.5` had zero examples and was also absent. The five untrained artifact labels are:

```text
ADM-1.9  gold=1
ING-0.1  gold=1
ING-0.3  gold=1
ING-0.5  gold=0
ING-0.6  gold=1
```

The SetFit contrastive pair generator used `sampling_strategy="oversampling"`, but the
saved logistic-regression head has `class_weight=None`. Rare classes therefore remained
severely disadvantaged during the classification-head stage.

### 7.3 Validation limitation

Artifact metrics:

```text
validation top-1 accuracy: 0.7441
validation macro-F1:       0.6768
validation top-3 accuracy: 0.8765
```

These numbers are real for the recorded validation split, but the split contains:

```text
income validation rows: 0
total validation rows: 340
```

Therefore those metrics provide no evidence that the model works on Milk Sales, Cow Sales,
Heifer Sales, Calf Sales, or any other income category.

### 7.4 Local and deployable artifacts

```text
models/setfit_base/      full PyTorch SetFit model, about 1.1 GB
artifacts/v1.1.0/       ONNX deployment package, about 282 MB
```

The deployment bundle includes:

```text
model.onnx
classifier.joblib
model_card.json
labels.json
taxonomy.json
provider_giro_map.csv
tokenizer/
```

The ONNX export has a parity gate comparing PyTorch and ONNX embeddings/predictions. The
sales incident was reproduced with the original PyTorch body/head as well as ONNX, so the
incident is not an ONNX quantization or Cloud Run export defect.

## 8. Inference Service

### 8.1 Current deployment

Known Cloud Run URL:

```text
https://mlmodel-988859051589.europe-west1.run.app
```

Verified on 2026-08-11:

```json
GET /health
{"status":"ok","service_version":"1.1.0","model_loaded":false}
```

`/artifact-check` confirmed that `/srv/artifacts/v1.1.0` contains real artifact files, not
Git LFS pointers. The deployed ONNX file is 278,255,693 bytes.

The health endpoint deliberately does not load the model. Lazy loading happens on the first
prediction request.

The known URL responded without an identity token for health/artifact checks. The original
blueprint planned private Cloud Run invocation through OIDC, so deployment authentication
and public-route policy should be reviewed before the next release.

### 8.2 Endpoints

```text
GET  /health
GET  /model-info
GET  /artifact-check
POST /predict
POST /predict-batch
```

The maximum batch size is 500. Larger batches receive HTTP 413. The batch implementation
currently loops through rows and calls `predictor.predict` for each row; it is not a single
vectorized ONNX batch across all 500 rows.

The API does not parse XML. It accepts parsed JSON line items.

### 8.3 Request shape

```json
{
  "input_id": "optional correlation id",
  "item_text": "required",
  "description": "",
  "provider": "",
  "meter_code": null,
  "invoice_metadata": {},
  "top_k": 3,
  "return_debug": false
}
```

`invoice_metadata` currently has no effect on classification. There is no explicit
`transaction_type` field in `PredictRequest`.

### 8.4 Response contract

```json
{
  "input_id": "...",
  "model_version": "v1.1.0",
  "source": "model|product_lookup|meter_lookup",
  "predictions": [
    {"code": "EXP-2.3", "name": "Vacunas", "score": 0.91}
  ],
  "confidence": {"top1": 0.91, "margin": 0.40, "entropy": 0.20},
  "decision": "auto_accept|review_required",
  "reason": null,
  "latency_ms": 42,
  "debug": null
}
```

`predictions[0]` and `predicted_code` mean "the model or lookup's original suggestion."
They do not always mean "the accepted business classification." The accepted value is the
separate final code.

## 9. Current Classification Cascade

The implemented order in `app/inference/predictor.py` is:

1. known electricity meter lookup;
2. product lookup;
3. SetFit/ONNX model;
4. confidence decision.

### 9.1 Meter lookup

```text
app/data/electricity_meter_map.csv
entries: 22
```

Known `CdgIntRecep` meter values resolve deterministically and skip the model. They return
score 1.0 and `auto_accept`.

### 9.2 Product lookup

```text
app/data/product_lookup.csv
entries: 604
```

Matching is based on normalized item/provider rules in `product_lookup.py`. Lookup hits are
placed first with score 1.0. The model is still run for product lookup and can trigger a
`lookup_model_conflict` review if it strongly disagrees.

There are currently no deterministic rules for:

```text
VENTA DE LECHE
VENTA DE VACAS
VENTA DE VAQUILLAS
VENTA DE TERNERAS
VENTAS TERNEROS
```

### 9.3 Backend confidence policy

Artifact thresholds:

```text
accept_top1:  0.70
accept_margin: 0.10
```

Backend logic:

```text
shadow mode                          -> review_required
lookup/model conflict                -> review_required
product or meter lookup              -> auto_accept
predicted weak class                 -> review_required
top1 < 0.70                           -> review_required
margin < 0.10                         -> review_required
otherwise                            -> auto_accept
```

### 9.4 Temporary loader policy used for the production run

The temporary loader added a stricter model threshold:

```text
model top1 >= 0.80
margin >= 0.10
backend must already allow auto_accept
```

This is confirmed by the stored data: the minimum top-1 among model auto-accept rows is
0.8005. Direct product and meter mappings auto-accept regardless of this loader threshold.

The backend threshold and loader threshold are therefore different. Do not discuss "the
threshold" without specifying which layer.

## 10. Temporary Full-Inference Loader

Primary historical loader:

```text
Temp_Inference/classify_raw_invoices_to_supabase.py
```

It:

- parses COMPRAS and VENTAS XML;
- extracts line-level fields needed by the first prediction table;
- creates `input_id = transaction_type|provider_rut|folio|line_number`;
- sends batches of at most 500 to `/predict-batch`;
- retries transient HTTP errors;
- applies the stricter loader decision policy;
- writes top-3, confidence, prediction source, decision, and final code;
- originally upserted into `line_item_predictions`.

The old `line_item_predictions` production table has been dropped. Do not rerun this loader
with writes in its current form: its default target no longer exists and its output shape is
not the current five-table schema.

The original full-run elapsed time was discussed in chat, but no durable timing log was
written to the repository. Do not repeat an unverified timing number. Add a machine-readable
run manifest with start/end/duration before the next backfill.

### 10.1 Filtered detail lines

The loader classified 12,071 of 12,103 extracted detail lines. It intentionally skipped 32:

```text
23 header rows: CODIGO DESCRIPCION / A@CODIGO DESCRIPCION
 9 numeric-only rows
```

The nine numeric-only rows belong to nine HDI SEGUROS invoices and have meaningful amounts.
Examples:

```text
item_text=61891841 description=27054 amount=142385
item_text=61829115 description=22514 amount=118493
item_text=61849994 description=43820 amount=230634
```

Because each of those nine invoices had only a numeric line, the invoices themselves are
also absent from the normalized production tables. These should not be silently called junk.
They lack enough semantic text for the model, but the invoice and line should be retained and
routed to review or enriched through provider/policy context.

## 11. Supabase Evolution

The database went through three designs.

### 11.1 Initial single table - dropped

```text
line_item_predictions
```

It stored invoice identity, raw line fields, prediction, top-3, confidence, and review state
in one row. It used a generated UUID primary key and a unique composite `input_id` string.
This table was the target of the full inference run and the source for the first migration.
It no longer exists through the REST schema.

### 11.2 Intermediate normalized schema - replaced

Defined in:

```text
Temp_Inference/normalized_schema.sql
```

It created:

```text
taxonomy_categories
invoices
invoice_items
```

The migration did not rerun inference. It split existing predictions and reparsed XML for
seller/buyer metadata. Before this schema was replaced, a complete safety snapshot was made.

### 11.3 Current five-table schema

Defined in:

```text
Temp_Inference/normalized_company_item_schema.sql
```

Current tables:

```text
categories
companies
item_catalog
invoices
invoice_items
```

All five tables have RLS enabled. The SQL grants CRUD to `service_role`; it does not define
browser/authenticated-user policies. The web application will need explicit least-privilege
RLS policies or server-side access before normal users can read/write these tables.

## 12. Current Production Database

Counts were verified through read-only Supabase REST calls on 2026-08-11.

```text
categories:          71
companies:          460
item_catalog:     5,579
invoices:         5,157
invoice_items:   12,071
```

Invoice direction:

```text
COMPRAS invoices: 5,069
VENTAS invoices:     88
```

Prediction sources:

```text
model:          7,833
product_lookup: 2,651
meter_lookup:   1,587
```

Decisions:

```text
auto_accept:      6,356
review_required:  5,715
reviewed=true:        0
needs_review=true: 5,715
final_code null:   5,715
```

Decision by source:

```text
model + auto_accept:          2,118
model + review_required:      5,715
product_lookup + auto_accept: 2,651
meter_lookup + auto_accept:   1,587
```

Company roles:

```text
is_seller=true: 429
is_buyer=true:   37
both roles:       6
```

The role counts reconcile as `429 + 37 - 6 = 460` unique companies.

The old REST resources `line_item_predictions` and `taxonomy_categories` return 404 and
should be treated as dropped.

## 13. Current Database Relationships

```text
companies.company_id
  <- invoices.company_id

invoices.invoice_id
  <- invoice_items.invoice_id

item_catalog.catalog_item_id
  <- invoice_items.catalog_item_id

categories.categories_id
  <- invoice_items.predicted_categories_id
  <- invoice_items.final_categories_id
```

`invoices.company_id` means the other party:

```text
COMPRAS -> seller/vendor company
VENTAS  -> buyer/customer company
```

The invoice still stores both seller and buyer RUT/name/address fields for transparency and
invoice fidelity. `invoice_items` does not duplicate `company_id`; it reaches the company
through its invoice.

## 14. Current Table Semantics

### 14.1 `categories`

```text
categories_id uuid primary key, database generated
code          text unique not null
name          text not null
```

The UUID is the database foreign-key identity. The category code remains the ML/business
identity. The migration maps model codes to UUIDs before inserting invoice items.

### 14.2 `companies`

```text
company_id  uuid primary key
rut         text unique not null
company_name text not null
is_seller   boolean
is_buyer    boolean
giro, address, commune, city
```

Companies are grouped by normalized RUT. For fields that vary across invoices, the migration
chooses the most common nonblank value. Role means "appears as this role in at least one
invoice," not a permanent legal type.

### 14.3 `invoices`

Identity and relationships:

```text
invoice_id uuid primary key
company_id foreign key to companies
unique(seller_rut, document_type, invoice_folio)
```

Folio alone is not globally unique. A folio is the issuer-assigned document number; different
sellers can issue the same folio. The business key therefore includes seller RUT and document
type.

Stored invoice fields:

```text
transaction_type, invoice_folio, document_type, invoice_date,
generated invoice_period,
seller_rut/name/giro/address/commune/city,
buyer_rut/name/giro/address/commune/city,
receiver_internal_code,
net_amount, iva_amount, exempt_amount, total_amount,
due_date, payment_form
```

### 14.4 `item_catalog`

```text
catalog_item_id uuid primary key
item_name       text not null
description     text not null default ''
unique(item_name, description)
```

Current migration identity logic:

- for the configured generic names `DETALLE`, `FECHA-GUIA`, `ITEM`, `PRODUCTO`, `SERVICIO`,
  `SERVICIOS`, and `TOTAL`, the catalog identity is `(item_name, description)`;
- for every other name, catalog description is forced to empty and the identity is effectively
  exact `item_name` only;
- identity is case-sensitive and does not canonicalize accents, punctuation, aliases, sizes,
  periods, or transaction-specific numbers.

This is a raw-reference catalog, not yet a clean inventory/master-product catalog.

Known example: three PC Factory invoice rows use item name `...` and three different laptop
descriptions. Because `...` is not in the generic-name set, all three currently share one
catalog UUID. Their descriptions are not lost; they remain in `invoice_items.description`,
but the catalog row itself is only `...` with an empty description.

Known alias families also remain separate, for example:

```text
G93
Gasolina 93
93 S/P
Gasolina 93 octanos sin plomo
Aramco Gasolina 93
```

See `Temp_Inference/client_item_naming_examples.md` for client-discussion examples. The next
catalog design should probably separate canonical items from raw aliases rather than destroy
raw invoice text through renaming.

### 14.5 `invoice_items`

Identity:

```text
item_id uuid primary key
unique(invoice_id, invoice_line_number)
```

Raw/financial fields:

```text
invoice_id, catalog_item_id, invoice_line_number,
item_text, description, item_codes, meter_code,
quantity, unit, unit_price, amount,
discount_pct, discount_amount, recargo_amount,
tax_exempt, additional_tax_code
```

Prediction/review fields:

```text
model_version, prediction_source,
predicted_categories_id, predicted_code, predicted_name,
top1_score, margin, entropy, top3,
decision, generated needs_review, reviewed,
final_categories_id, final_code
```

`top3` candidates were remapped to include `categories_id`, code, name, and score.

The production review contract is:

```text
auto_accept:
  final_code = predicted_code
  final_categories_id = predicted_categories_id
  reviewed = false

review_required before human action:
  final_code = null
  final_categories_id = null
  reviewed = false
  needs_review = true

after human review:
  final_code = human-selected code
  final_categories_id = matching category UUID
  reviewed = true
  needs_review becomes false
```

The current schema does not store `reviewed_by`, `reviewed_at`, prediction creation time, or
model run ID. It also lacks consistency constraints ensuring the code and UUID columns always
refer to the same category. These are recommended schema improvements.

## 15. XML Backfill Completeness

The current migration reparsed XML and populated the following among 12,071 stored items:

```text
quantity:                 11,002
unit:                      7,996
unit_price:               10,983
discount_pct:                887
discount_amount:             926
recargo_amount:                32
tax_exempt=true:              702
additional_tax_code:        1,303
item_codes nonempty:        7,937
```

The migration dry run currently reports:

```text
duplicate invoice keys: 0
duplicate line keys:    0
migration mapping errors: 0
```

The source snapshot has exactly the same 71/5,157/12,071 category/invoice/item counts as the
current production tables.

## 16. Safety Snapshot And Recovery

Snapshot location:

```text
Temp_Inference/snapshots/normalized_before_company_item_split/
```

Files:

```text
taxonomy_categories.json  71 rows
invoices.json           5,157 rows
invoice_items.json     12,071 rows
manifest.json
```

This snapshot preserves the already-computed predictions before the company/item-catalog
migration. The current final schema can be rebuilt from this snapshot plus the raw XML using:

```text
Temp_Inference/migrate_to_company_item_schema.py
```

Dry run only:

```bash
python3 Temp_Inference/migrate_to_company_item_schema.py
```

Do not run `--write` against production unless the target schema and expected empty/current
state are explicitly verified. The script performs upserts, but database changes still need
a fresh backup and count checks.

## 17. Sales Classification Incident

### 17.1 Stored production blast radius

The 125 stored `VENTAS` line items break down as:

```text
50 VENTAS TERNEROS
47 VENTA DE LECHE
18 VENTA DE VACAS
 3 VENTA CAMIONETA
 2 VENTA DE ACTIVO FIJO
 2 VENTA DE VAQUILLAS
 1 VENTA DE TERNERAS
 1 OTROS INGRESOS
 1 maquinaria
```

Every one of the 125 received an `EXP-*` top-1 prediction. Every one was
`review_required`; none has a final code.

Prediction examples:

```text
VENTA DE LECHE:
  44 -> EXP-14.1 Mantencion Caminos
   3 -> EXP-15.3 Fletes

VENTA DE VACAS:
  18 -> EXP-14.1 Mantencion Caminos

VENTA DE VAQUILLAS:
   2 -> EXP-14.1 Mantencion Caminos

VENTAS TERNEROS:
  50 -> EXP-1.1 Otros Gastos RRHH

VENTA DE TERNERAS:
   1 -> EXP-14.1 Mantencion Caminos
```

Top-1 score ranges:

```text
VENTA DE LECHE       0.1224 - 0.2162, mean 0.1545
VENTA DE VACAS       0.2427 - 0.4032, mean 0.3127
VENTA DE VAQUILLAS   0.2056 - 0.2981
VENTA DE TERNERAS    0.3284
VENTAS TERNEROS      0.3862 - 0.5693, mean 0.5075
```

These were clearly uncertain model outputs. The database decision gate protected them from
auto-accept. The customer-facing display did not respect that protection.

### 17.2 Gold/silver/raw evidence

```text
Category      Raw obvious rows  Gold rows  Deployed status
ING-0.1 milk              47          1   untrained
ING-0.2 cows              18          3   trained, severely weak
ING-0.3 heifers            2          1   untrained
ING-0.4 calves            51          2   trained, severely weak
```

For Milk Sales, all 47 obvious raw rows reached silver, were audited `Y`, and had verdict
`ING-0.1`, generally with Ollama/Qwen confidence 0.98-0.99. Only one entered gold because of
the promotion deduplication key.

The gold cow examples also contain a semantic problem: purchased `vacas` / `vacas prenadas`
rows from `COMPRAS` were labeled as `ING-0.2 VENTA DE VACAS`. These should be quarantined or
reassigned after the client defines the proper livestock-purchase/capital treatment.

The screenshot case `VAQUILLAS PRENADAS -> Mantencion Maquinaria` is a separate `COMPRAS`
invoice. Its top-1 score is 0.2024. It should not automatically be described as a sale.

### 17.3 Root causes

1. Historical silver-to-gold deduplication collapsed repeated exact names too aggressively.
2. The trainer excluded one-example classes from the deployed head.
3. Classes with two or three examples were technically trained but underfit.
4. The LR head had no class weights.
5. The validation split contained no income examples.
6. Aggregate metrics were accepted without business-critical slice gates.
7. `transaction_type` was parsed/stored but not sent into model decision logic.
8. A `VENTAS` row was allowed to compete against all heavily represented expense classes.
9. No deterministic sales-name lookup existed for obvious business rules.
10. No regression tests asserted the expected sales categories or sales/expense invariant.
11. The consumer displayed `predicted_name` even when `decision=review_required` and
    `final_code=null`.

### 17.4 What was ruled out

- not an Ollama failure for the obvious milk rows;
- not an ONNX quantization failure;
- not a GCP/Cloud Run corruption issue;
- not primarily a confidence-threshold failure;
- not a database constraint failure.

## 18. Required Recovery Plan

### P0 - stop incorrect customer presentation

1. In the web/API consumer, never display `predicted_code` or `predicted_name` as the final
   classification when `decision=review_required` or `final_code is null`.
2. Display a clear `Needs review` state and the top-3 only as suggestions.
3. Use `final_code` / `final_categories_id` as the business classification.
4. Audit any exports or dashboards already built to determine whether they also used
   `predicted_code` instead of `final_code`.

### P0 - deterministic income routing

Add normalized transaction-aware business rules before the model, at minimum:

```text
VENTAS + VENTA DE LECHE      -> ING-0.1
VENTAS + VENTA DE VACAS      -> ING-0.2
VENTAS + VENTA DE VAQUILLAS  -> ING-0.3
VENTAS + VENTA DE TERNERAS   -> ING-0.4
VENTAS + VENTAS TERNEROS     -> ING-0.4
```

The exact mapping list should be represented as versioned data/config, not scattered `if`
statements. A deterministic business rule should produce source such as `business_lookup`
or a more specific source, score 1.0, and an auditable rule version. Adding a new source will
require updating API literals and the Supabase source constraint.

Do not globally map every `VENTAS` row without examining credit notes, asset sales, other
income, and categories absent from the taxonomy. Use transaction type to constrain or route,
not to erase accounting nuance.

### P0 - preserve unclassifiable invoice lines

Retain the nine HDI insurance invoices and their numeric-only lines. Store them with raw
fields and force review rather than deleting the invoice because semantic text is missing.

### P0 - regression tests

Add tests that assert:

- every canonical sales phrase maps to its expected `ING-*` category;
- `VENTAS` cannot silently auto-accept an `EXP-*` category;
- `review_required` cannot be presented or exported as final;
- `final_code` is populated for auto-accept and null before human review;
- each production-critical taxonomy class has at least one golden behavior test;
- batch responses preserve input correlation and row count.

### P1 - rebuild training data

1. Audit transaction type alongside every income label.
2. Remove/quarantine purchase rows mislabeled as sales.
3. Promote audited silver without collapsing a class below its coverage target.
4. Keep genuinely diverse descriptions/providers/farms/time periods, while removing true
   duplicate records.
5. Set explicit minimums before a class can be deployed or auto-accepted. A practical target
   is at least 8-15 diverse training examples plus a separate held-out set, not 1-3 rows.
6. Create a fixed business validation suite containing every income class regardless of
   frequency.
7. Consider `class_weight="balanced"` or a balanced head-training sample and compare against
   the current head.
8. Evaluate transaction-aware routing, a label mask, or separate income/expense classifier
   paths rather than relying only on concatenating the word `VENTAS` into text.

Repeated identical item names do not justify asking ML to rediscover a known mapping. Use a
rule for exact canonical names and train SetFit on useful variation and the ambiguous long
tail.

### P1 - retrain as a new version

Never overwrite `v1.1.0`. Produce `v1.2.0` or a clearly named candidate.

Before training:

```bash
python3 scripts/55_contradiction_audit.py
python3 scripts/50_build_gold_views.py
```

Training pattern:

```bash
.venv-train/bin/python training/train_setfit.py \
  --variant base \
  --max-steps 1500
```

Export pattern:

```bash
.venv-train/bin/python training/export_onnx.py \
  --variant base \
  --version v1.2.0
```

Do not deploy merely because aggregate accuracy improves. Release gates must include income
slice accuracy, deterministic rule tests, top-3 behavior, confidence calibration, and
PyTorch/ONNX parity.

### P1 - repair stored sales rows without rerunning everything

The current sales rows are already isolated by `invoices.transaction_type='VENTAS'` and all
are review-required. After the business rules are approved:

1. take a fresh database backup;
2. dry-run the new rules against the 125 sales lines;
3. manually inspect every distinct sales name and exceptional asset/other-income case;
4. update only the rows covered by approved deterministic rules;
5. preserve the old prediction fields for audit;
6. record the rule/model version and correction provenance;
7. verify counts and final codes before exposing them again.

The current schema lacks a separate prediction history table, so preserving the original
prediction while changing final fields is especially important.

### P2 - improve the item catalog

The catalog problem is separate from accounting-category prediction.

Recommended conceptual model:

```text
canonical_items
item_aliases (raw name/description/provider -> canonical item)
invoice_items (immutable raw invoice facts + alias/canonical reference)
```

This would allow `G93`, `Gasolina 93`, and `93 S/P` to resolve to one canonical gasoline item
without deleting the original invoice wording. Placeholder names such as `...`, `DETALLE`,
and `SERVICIOS` need description-aware handling and sometimes semantic/manual canonicalization.

Do not promise that the current `item_catalog` is an inventory-management SKU catalog. It is
currently an exact/grouped reference catalog derived from noisy invoice text.

### P2 - database hardening

Consider adding:

- `created_at`, `updated_at` and source/run timestamps;
- `reviewed_by`, `reviewed_at`, and review reason/comment;
- `prediction_run_id` and rule/model version history;
- constraints or triggers ensuring category UUID and code agree;
- a constraint requiring final category when `reviewed=true`;
- explicit handling of auto-accepted final category;
- RLS policies for actual authenticated application roles;
- a prediction/review history table rather than overwriting provenance;
- generated or trigger-maintained normalization keys where database idempotency matters.

## 19. Safe Local Commands

### Start the local API

```bash
cd /Users/afaq/Desktop/Mctech/ML-model
.venv-backend/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Run backend tests

```bash
.venv-backend/bin/python -m pytest tests -q
```

### Inspect service without loading the model

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/artifact-check
```

### Reproduce a local prediction

```bash
curl -X POST http://127.0.0.1:8000/predict \
  -H 'Content-Type: application/json' \
  -d '{"input_id":"debug-1","item_text":"VENTA DE LECHE","provider":"ANTILLANCA SPA","top_k":3}'
```

This command currently reproduces the defect because transaction type and sales rules have
not yet been implemented.

### Cloud Run smoke helper

```bash
python3 app/inference/cloud_run_smoke_test.py \
  https://mlmodel-988859051589.europe-west1.run.app
```

The smoke helper performs a real prediction and may cold-start the model. Health/artifact
checks alone are cheaper and do not load the model.

### Supabase migration dry run

```bash
python3 Temp_Inference/migrate_to_company_item_schema.py
```

## 20. Secrets And Access

Supabase connection material is stored locally in:

```text
Temp_Inference/.env.loader
```

Expected variable names:

```text
SUPABASE_URL
SUPABASE_PUBLISHABLE_KEY
SUPABASE_SECRET_KEY
SUPABASE_JWKS_URL
```

The current migration/load scripts use Supabase REST with the server-side secret key. Never
commit or expose the secret key to browser code. No pgAdmin or MCP connection is required for
the existing scripts.

The `.env.loader` file is ignored by git. When sharing this handover, share only the variable
names, never their values.

## 21. Documentation That Is Stale

Treat this handover and executable code/artifacts as newer than the following statements:

- `README.md` still tells users to place `v1.0.0` artifacts manually;
- `MLMODEL.md` says the gold dataset has 1,604 rows and deployment is not executed;
- `blueprint.md` describes planned schemas and infrastructure that differ from production;
- `Temp_Inference/README.md` still describes the intermediate migration and states the loader
  default threshold without clearly distinguishing it from the production run;
- comments mentioning 72 taxonomy files are stale; the current taxonomy has 71 rows.

Update those documents after the P0 recovery design is agreed. Do not delete them before
extracting useful architectural rationale and historical decisions.

## 22. Known Open Questions Requiring Product/Client Input

1. What is the correct accounting category for purchases of cows/heifers, including pregnant
   animals? The current taxonomy is sales-oriented for `ING-*` and the old gold contains
   purchase/sale contradictions.
2. How should sales of fixed assets, vehicles, and machinery be represented?
3. Are all `VENTAS` documents revenue, or are credit notes/adjustments present and how should
   document type affect routing?
4. Should exact canonical sales names always auto-accept, or should some require review by
   document type/company?
5. What does the client want `item_catalog` to represent: raw invoice item references,
   canonical spend items, or inventory SKUs?
6. Which aliases should be merged, and which variations represent genuinely different items?
7. What level of accepted-error risk is allowed for auto-accept in each category?

## 23. Recommended First Session After This Handover

Do the work in this order:

1. add failing regression tests for the exact sales incident;
2. trace the web/dashboard code that displayed `predicted_name` as final;
3. implement the final-code/review display contract;
4. add transaction type to the API and deterministic sales routing;
5. dry-run the rules across all 125 `VENTAS` lines and audit exceptions;
6. preserve the nine HDI numeric-only invoices instead of dropping them;
7. rebuild/audit income gold data and create a real income validation split;
8. retrain/export a new candidate version;
9. run local, ONNX parity, batch, and business regression tests;
10. deploy a new Cloud Run revision and reclassify only approved affected rows;
11. update stale documentation and commit the temporary migration tools intentionally.

## 24. Non-Negotiable Guardrails

- Do not delete or overwrite raw XML.
- Do not overwrite `artifacts/v1.1.0` or `models/setfit_base` while diagnosing it.
- Do not rerun the old loader against production in its current form.
- Do not drop current Supabase tables without a fresh export and verified restoration plan.
- Do not treat `predicted_code` as final when review is required.
- Do not use aggregate validation accuracy as the only release gate.
- Do not train a category with one or two examples and describe it as production-ready.
- Do not silently discard invoices because item text is numeric or semantically weak.
- Do not merge catalog aliases destructively; preserve raw invoice facts.
- Do not expose `SUPABASE_SECRET_KEY` to the frontend, logs, commits, or handovers.

## 25. Final Current-State Summary

```text
Model:
  v1.1.0 SetFit + LogisticRegression, ONNX int8, deployed and reachable

Training:
  1,733 gold rows, 66 trained classes, 28 weak labels
  aggregate validation exists, but no income validation coverage

Raw production data:
  5,195 XML files, 12,103 extracted detail lines

Stored production data:
  5,157 invoices, 12,071 invoice items
  6,356 auto-accepted, 5,715 awaiting review, 0 human-reviewed

Database:
  categories, companies, item_catalog, invoices, invoice_items
  old line_item_predictions and taxonomy_categories dropped
  intermediate normalized snapshot retained locally

Critical defect:
  all 125 sales lines predicted as expenses, all review-required
  UI/customer layer displayed preliminary predictions as classifications

Immediate direction:
  repair review/final display contract, add transaction-aware deterministic sales rules,
  add business regression tests, rebuild income gold/validation, retrain as a new version
```
