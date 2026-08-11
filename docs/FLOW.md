# FLOW — how execution actually travels

Call paths for the parts being modified. Update this when the path changes.

## Training path

```
training/train_setfit.py
  main()
   ├─ load_rows()                    reads Data/gold/_master_gold.csv
   │    └─ build_text(item, desc, prov, giro)      line 40
   │         └─ returns "item_text | description | provider"
   │            ── THIS is the model's input. Any dedup key must cover
   │               every field this function reads.  (DECISIONS.md D-001)
   │
   ├─ stratified_split(rows)                        line 65
   │    ├─ len(items) < 2          → excluded, class never trained   ← BUG-001
   │    ├─ len(items) < 5          → all to train, NO validation row ← BUG-001
   │    └─ else                    → 80/20, ≥1 validation row
   │
   ├─ SetFitModel.from_pretrained(BASE_MODEL, labels=sorted(counts))
   │    └─ labels = category_code strings only; names never involved
   │
   ├─ trainer.train()
   │    ├─ stage 1: contrastive fine-tune of the sentence-transformer body
   │    │           sampling_strategy="oversampling"
   │    └─ stage 2: LogisticRegression head on the body's embeddings
   │                class_weight  ← D-007 changes this
   │
   └─ evaluate(model, val_rows, labels)             line 88
        └─ writes metrics into the model card
           ── aggregate only today; income slice must be separate (D-008)
```

**The two exclusion points on lines 76 and 79 are the trap.** A class with 1
example is dropped entirely; a class with 2–4 examples is trained but gets no
validation row, so it appears in `classifier_classes` while being invisible to
every metric. `ING-0.2` (3 rows) and `ING-0.4` (2 rows) took the second path —
that is why they are absent from `per_class_f1` even though they were trained.

## Inference path

```
app/inference/predictor.py :: Predictor.predict()
  │
  ├─ meter_code given?
  │    └─ bundle.meter_lookup.match(meter_code)         line 44
  │         └─ hit → _meter_response(), score 1.0, RETURNS EARLY
  │                  (model never runs)
  │
  ├─ bundle.lookup.match(item_text, provider)           line 48
  │    └─ product_lookup.csv, 604 entries
  │
  ├─ build_text(item_text, description, provider)       line 19
  │    └─ numeric-only description dropped
  │       ── mirrors training/train_setfit.py :: build_text
  │          these two MUST stay in sync
  │
  ├─ bundle.encoder.embed([text])        ONNX int8      line 50
  ├─ bundle.head.predict_proba(embedding)               line 51
  │    └─ LogisticRegression, coef_ (n_classes, 768)
  │       ── a class with no coef_ row can never be returned  ← BUG-001
  │
  ├─ lookup hit? → lookup code placed first at score 1.0, model
  │                becomes the conflict check (line 63)
  │
  └─ confidence.decide(...)                             line 77
       ├─ shadow_mode              → review_required
       ├─ lookup_model_conflict    → review_required
       ├─ source is a lookup       → auto_accept
       ├─ code1 in weak_classes    → review_required
       ├─ top1 < 0.70              → review_required
       ├─ margin < 0.10            → review_required
       └─ else                     → auto_accept
```

### Two different thresholds — never say "the threshold"

```
backend  (artifacts/*/model_card.json):  top1 ≥ 0.70, margin ≥ 0.10
loader   (Temp_Inference/…loader):       top1 ≥ 0.80, margin ≥ 0.10
```

The production backfill used the stricter loader policy. Confirmed by the data:
the minimum top-1 among model auto-accepted rows is 0.8005. Meter and product
lookups auto-accept regardless of either threshold.

## Promotion path (the one being fixed)

```
Data/silver/<CODE> <name>.csv          audit ledger, 1,672 rows
  │   filter: verdict non-empty AND not REJECT AND item_text non-empty
  │           → 1,012 usable rows
  │
  ├─ OLD  scripts_labeling_pipeline_2026_07_03/48_promote_starving_audit.py
  │        key = (nz(item_text), category_code)              ← BUG-001
  │        seen pre-seeded with existing gold, so one row per
  │        (name, category) for all time
  │
  └─ NEW  scripts/56_promote_silver_to_gold.py
           key = (nz(item), nz(desc), nz(prov), code)
           skips the 77 conflicting-verdict names
           → +680 rows

Data/gold/_master_gold.csv
  │  scripts/50_build_gold_views.py
  ▼
Data/gold/<CODE> <name>.csv            generated views, never edited by hand
```

## Local comparison path (this phase)

```
Temp_Inference/snapshots/normalized_before_company_item_split/invoice_items.json
   12,071 rows, v1.1.0 predictions + confidence + amount
   │
   ├─ copied to Data/stale/inference_v1.1.0_<ts>/     baseline preserved
   │
   └─ joined against a fresh local v1.2.0 run over Data/processed/line_items.csv
        → before/after per row: predicted_code, top1, decision
```

No network call anywhere in this path.
