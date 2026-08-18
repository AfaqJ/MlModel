# ARCHITECTURE — the shape of the system

High-level map only. Implementation detail lives in the code.


## The two halves

This repo does two separate things that are easy to confuse:

1. **A labeling pipeline** (offline) — turn 12,103 raw invoice lines into
   correct accounting categories, and load them into Supabase.
2. **A classifier service** (online) — a FastAPI app that classifies new
   invoice lines on demand, deployed to Cloud Run.

The classifier is a *tool used by* the labeling pipeline. It is not the product.

## Data flow, end to end

```
Data/Raw_Data/dte_*_{COMPRAS,VENTAS}/*.xml    5,195 documents
  │  scripts/10_extract_line_items.py
  ▼
Data/processed/line_items.csv                 12,103 line items
  │
  ├──► Data/silver/         Ollama (qwen3:14b) candidate labels + audit ledger
  ├──► client-supplied rules and examples (imported directly, no Ollama)
  ▼
Data/candidates/recovery_v1_3_2/master_gold.csv   1,837 rows — what v1.3.3 trained on
  │                                               (1,582 distinct model inputs)
  │  training/train_recovery_setfit.py
  ▼
models/setfit_base_recovery_v1_3_2/           PyTorch SetFit body + LR head
  │  training/export_recovery_onnx.py
  ▼
artifacts/v1.3.3-int8/                        ONNX int8 deployment bundle
  │  gcloud builds submit → Artifact Registry → gcloud run deploy
  ▼
Cloud Run `mlmodel` ──► Supabase (5 tables)   11,746 rows, 77 categories, live
```

Note the deploy path: **git is never involved**. The 278 MB `.onnx` is uploaded
in the build context, which is why it cannot become an LFS pointer.

## The model

```
SetFit = contrastive fine-tune of a sentence-transformer
         + sklearn LogisticRegression head

base encoder : sentence-transformers/paraphrase-multilingual-mpnet-base-v2
head         : LogisticRegression, coef_ shape (67, 768)
serve-time   : ONNX Runtime, dynamically quantized int8
model input  : "[transaction_type] | item_text | description | provider"
               transaction_type is REQUIRED — COMPRAS or VENTAS
model label  : category_code string, e.g. "ING-0.1"
```

**77 categories** in the live `categories` table; the deployed model **emits 67**
— `artifacts/v1.3.3-int8/labels.json` → `classifier_classes`, corroborated by
`model_card.json` → `trained_classes: 67`. That artifact is the authority here;
do not derive the number by subtracting from the category table. `AF-1.1`,
`AF-2.1` and `ING-0.7` were added 2026-08-14 and are assigned by rule, not
predicted — see D-028. `ADM-1.9`, `ADM-2.3`, `ING-0.5` and `ING-0.6` carry
`trained: false` and cannot be emitted. 26 classes have fewer than 15 distinct examples and are
routed to review by the weak-class guard. Validation: 312 rows, accuracy 0.7532
(FP32) / 0.7468 (INT8), top-3 0.8654, income slice 21 rows at 1.00.

**The head never sees category names.** `coef_[i]` is 768 numbers learned by
gradient descent from class `i`'s training examples. The human-readable name
(`VENTA DE LECHE`) lives only in `labels.json`, for display. A class with zero
examples has no `coef_` row and **can never be predicted**. This is the single
most important architectural fact in the project — it is what caused BUG-001.

Provider is included in the input because it carries real signal (COPEC → fuel,
veterinary suppliers → animal health), but training uses **provider dropout** so
the encoder cannot lean on it as a shortcut. See D-021.

## The classification cascade (`app/inference/predictor.py`)

Order matters. The first three are deterministic, return score 1.0, and skip the
model entirely. Steps 5–8 can only ever *downgrade* a decision to review — none
of them can promote one.

```
1. meter lookup        COMPRAS + known CdgIntRecep → fixed category
2. business rules      exact sales phrase, VENTAS-only (28 rules)
3. product lookup      COMPRAS only; client's own row-level product labels
                       (696 entries in app/data/product_lookup.csv)
4. model               ONNX encode → LR head → direction mask zeroes
                       impossible cross-direction classes, then renormalise
5. confidence decision top1 ≥ 0.75 and margin ≥ 0.50, plus the weak-class guard
6. ambiguity guard     structural rules → review_required
7. familiarity gate    kNN k=10, agreement 0.4 → review_required
8. unknown-sales rule  any VENTAS row not matched by a business rule → review
```

Steps 1–3 are wrapped by `_invoice_context_guard`. This cascade is the correct
place for known, exact, repeating item names — the model handles the long tail
(5,349 distinct names, 4,115 appearing exactly once).

**Why step 7 exists:** confidence says how sharply the head separated the
classes it *knows*. It cannot say whether the input resembles anything the model
was trained on. That gap is what produced the confident false positives in the
v1.3.1 replay — 163 rows that had cleared 0.75/0.50 and were still wrong.

**Why step 8 exists:** the known operating sales are all handled by step 2. An
unmatched sale is likely an asset disposal or a missing taxonomy class, so a
probabilistic answer is useful for review but unsafe to auto-accept at any
confidence.

## Where state lives

- **Local source of truth:** `Data/` (raw, processed, silver, gold), `models/`,
  `artifacts/`. Raw XML and client evidence are the irreplaceable source;
  artifacts are gitignored and rebuildable from the exporter.
- **Local staged database payload:**
  `reports/recovery_v1_3_3/supabase_upload/` contains complete JSONL snapshots
  of all five tables — `categories`, `companies`, `item_catalog`, `invoices`,
  and `invoice_items`. This is the copy correction scripts modify and script 82
  re-loads wholesale. It is a release payload derived from the source data, not
  a second source of truth. Every correction script must be exact-targeted, dry
  runnable, make a local pre-write backup, and emit a changelog.
- **Item-catalog canonicalization: nothing built, deliberately.** `item_catalog`
  is keyed on item name plus a selective description, so a name carrying a
  changing value spawns a new entry per invoice — 5,411 entries for 11,746
  lines. A local prototype explored a two-table overlay and was deleted on
  2026-08-18 without being applied; its schema was an assumption, and the
  client meeting may invalidate it. Do not rebuild from memory of it. See
  D-034 and `docs/STATE.md`.
- **Supabase (`nkdswofslslrumyraklv`), live:** categories, companies,
  item_catalog, invoices, invoice_items — 11,746 rows, 77 categories, 7,143
  auto / 4,603 review after the verified 2026-08-17 re-load. Supabase owns the
  schema, generated UUIDs, policies, and live reviewer work. Script 82 performs
  no DDL: it upserts whole rows, reads live IDs back, and preserves the schema.
  Writes require an explicit flag on `scripts/supabase_rest.py`.
- **Cloud Run:** stateless. The service is a pure function; it holds no records.
- **Latest backup:** `backups/supabase_20260817T105217Z/` — all five live tables,
  row-count verified immediately before the 2026-08-17 full re-load. Earlier
  snapshots remain at `backups/supabase_20260814T110447Z_pre_corrections/` and
  `backups/supabase_20260812T070037Z/`.

The ML service must never become a system of record. That is a deliberate
constraint, not an accident of the current design.
