# ARCHITECTURE — the shape of the system

High-level map only. Implementation detail lives in the code and in
`guides/backend_codebase_guide.md`.

## The two halves

This repo does two separate things that are easy to confuse:

1. **A labeling pipeline** (offline, one-time) — turn 12,103 raw invoice lines
   into correct accounting categories. This is the actual deliverable right now.
2. **A classifier service** (online, ongoing) — a FastAPI app that classifies
   new invoice lines on demand. Secondary; used lightly after the backfill.

The classifier is a *tool used by* the labeling pipeline. It is not the product.

## Data flow, end to end

```
Data/Raw_Data/dte_*_{COMPRAS,VENTAS}/*.xml    5,195 documents
  │  scripts/10_extract_line_items.py
  ▼
Data/processed/line_items.csv                 12,103 line items
  │
  ├──► Data/silver/         Ollama (qwen3:14b) candidate labels + audit ledger
  │      _candidate_pool.csv      4,135 rows sent to Ollama
  │      <CODE> <name>.csv        1,672-row audit ledger (1,076 verdicts)
  │
  ├──► client-supplied rules and examples (imported directly, no Ollama)
  │
  ▼
Data/gold/_master_gold.csv                    training source of truth
  │  scripts/50_build_gold_views.py
  ▼
Data/gold/<CODE> <name>.csv                   generated views (read-only)
  │  training/train_setfit.py
  ▼
models/setfit_base/                           PyTorch SetFit body + LR head
  │  training/export_onnx.py
  ▼
artifacts/vX.Y.Z/                             ONNX int8 deployment bundle
  │
  ▼
app/  FastAPI service ──► Supabase (5 tables)  [FROZEN this phase]
```

## The model

```
SetFit = contrastive fine-tune of a sentence-transformer
         + sklearn LogisticRegression head

base encoder : sentence-transformers/paraphrase-multilingual-mpnet-base-v2
head         : LogisticRegression, coef_ shape (n_classes, 768)
serve-time   : ONNX Runtime, dynamically quantized int8
model input  : "item_text | description | provider"
model label  : category_code string, e.g. "ING-0.1"
```

**The head never sees category names.** `coef_[i]` is 768 numbers learned by
gradient descent from class `i`'s training examples. The human-readable name
(`VENTA DE LECHE`) lives only in `labels.json` for display. A class with zero
examples has no `coef_` row and can never be predicted. This is the single most
important architectural fact in this project — it is what caused BUG-001.

## The classification cascade (`app/inference/predictor.py`)

```
1. electricity meter lookup   (app/data/electricity_meter_map.csv, 22 entries)
2. product lookup             (app/data/product_lookup.csv, 604 entries)
3. SetFit / ONNX model
4. confidence decision        → auto_accept | review_required
```

Deterministic lookups return score 1.0 and skip the model. This cascade is the
correct place for known, exact, repeating item names — the model is for the
long tail (5,349 distinct names, 4,115 appearing exactly once).

## Where state lives

- **Local, authoritative:** `Data/` (raw, processed, silver, gold), `models/`,
  `artifacts/`.
- **Supabase, frozen this phase:** categories, companies, item_catalog,
  invoices, invoice_items — holds the v1.1.0 prediction run.
- **Local snapshot of that run:**
  `Temp_Inference/snapshots/normalized_before_company_item_split/invoice_items.json`
  (12,071 rows with predictions, confidence, and amounts). This is the baseline
  for before/after comparison and needs no network access.
