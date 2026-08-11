# MCT-37 Blueprint — Invoice Line-Item Classifier (Antillanca)

**End-to-end: train → export → serve → deploy → frontend → feedback loop.**
Aligned with MLMODEL.md (source of truth). Data state at writing: **1,604 gold rows, 70/71 trainable categories covered, 30 categories <15 examples** (`Data/gold/_master_gold.csv`).

---

## 1. Executive summary

A stateless FastAPI + ONNX Runtime inference service on **Google Cloud Run (2GB/1vCPU)** serves a **SetFit-fine-tuned `paraphrase-multilingual-mpnet-base-v2`** encoder (ONNX int8 dynamic quantized) + scikit-learn logistic-regression head, fronted by a **deterministic product-lookup layer**. The **Next.js app on Vercel + Supabase owns all state**: files, parsing, predictions, review queue, corrections, audit trail. The ML service receives parsed JSON line items and returns top-3 predictions with an auto-accept/review decision. Human corrections accumulate in Supabase and feed periodic offline retraining; new model versions ship as new Docker images (artifacts baked in) with instant rollback via Cloud Run revisions.

**Why this shape:** the dataset is small and skewed (30/71 classes under 15 examples), so the product is explicitly human-in-the-loop. The architecture optimizes for (a) shipping V1 now, (b) never letting the ML service become a system of record, (c) a clean retraining loop as feedback accumulates.

---

## 2. ML model — training plan

### 2.1 Why SetFit (not frozen encoder + LR, not a generative LLM)

- With ~20–50 examples/class across 71 classes, a **frozen** generic embedding space cannot separate semantically adjacent categories (e.g. the many `EXP` farm-supply subcategories). SetFit **contrastively fine-tunes the transformer itself** on same-class/different-class pairs, reshaping the embedding space around *these* categories before the LR head is trained. Validated in the SetFit paper down to 8–32 examples/class.
- A generative LLM (API or local) was rejected: per-call cost on 10k-row batches, latency, non-deterministic outputs, and it doesn't produce calibratable class probabilities. Silver-labeling with Ollama already showed models are confidently wrong (see LABELING_RULES.md) — fine for proposing labels offline, wrong for production inference.
- **Do not drift from SetFit.** A prior handover hallucinated "frozen EmbeddingGemma + LR"; that is documented as an incident in MLMODEL.md §7.

### 2.2 Base model: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`

- 278M params, 768-dim, 50+ languages incl. Spanish; the exact model used in the SetFit paper's multilingual experiments.
- Pretrained on **paraphrase detection** — the strongest possible prior for "these two strings mean the same thing," which is literally what SetFit's contrastive step builds on. Benchmarks show it beats larger XLM-R models *for SetFit specifically*.
- Rejected: `BAAI/bge-m3` (560M, ~1GB+, long-document/retrieval focus — overkill for 5–15-token invoice lines, blows the RAM budget); `paraphrase-multilingual-MiniLM-L12-v2` (fits easily but measurably lower ceiling on ambiguous short Spanish text).

### 2.3 Training procedure (local machine, PyTorch — never in production)

```
python -m venv .venv-train && pip install setfit sentence-transformers scikit-learn pandas onnx onnxruntime optimum
```

1. **Build training set** from `Data/gold/_master_gold.csv` only (per LABELING_RULES.md — never raw/keyword data).
   Input text = `item_text` + `" | "` + `description` + `" | "` + `provider` (single concatenated field; SetFit takes one string). Ablate: also train an `item_text`-only variant and compare — provider can help (COOPRINSEM → vet supplies) or hurt (multi-category vendors).
2. **Split:** stratified 80/20 train/validation. For classes with <5 examples, put all in train and accept no val coverage (they're review-routed anyway, §6). Keep a fixed `val.csv` committed with the artifact for reproducible threshold calibration.
3. **Class exclusions:** train on the **71 trainable** categories minus any with <2 examples this round (currently ADM-1.9, ING-0.1/0.3/0.6 at 1 each — a class needs ≥2 for contrastive pairs; realistically ≥8 to be usable). Excluded classes go in `labels.json` as `"weak": true` / `"untrained": true` so the API can still name them in review UX.
4. **Train:**
   ```python
   from setfit import SetFitModel, Trainer, TrainingArguments
   model = SetFitModel.from_pretrained(
       "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
       labels=labels)
   args = TrainingArguments(
       batch_size=16, num_epochs=1,          # 1 epoch of pair generation is the SetFit default sweet spot
       num_iterations=20,                    # pairs per example; raise to 30–40 for tiny classes
       body_learning_rate=2e-5, sampling_strategy="oversampling")  # oversampling counters class imbalance
   Trainer(model=model, args=args, train_dataset=train_ds, eval_dataset=val_ds).train()
   ```
   `trainer.train()` does both phases automatically: contrastive fine-tune of the body, then LR head on the re-embedded training set. ~20–60 min on a laptop CPU/MPS for this data size; no GPU required.
5. **Evaluate:** overall accuracy, **macro-F1** (the honest metric with this imbalance), top-3 accuracy (the product metric — human picks from 3), per-class precision/recall, confusion matrix. Log accuracy-by-confidence-bucket → this calibrates the thresholds in §6.
6. **Run `scripts/55_contradiction_audit.py`** before any training run after gold changes (per LABELING_RULES.md).

### 2.4 Export to ONNX int8

```python
# after training
model.save_pretrained("artifacts/setfit_v1")               # full model, kept for future warm-start retraining
# export body via optimum/sentence-transformers ONNX export, then dynamic-quantize to int8
joblib.dump(model.model_head, "artifacts/classifier.joblib")  # sklearn LR head
```

- **int8 over fp16:** Cloud Run is CPU-only, and ONNX Runtime does not get native fp16 CPU speedups here. The shipped int8 model is about 278MB and passed the parity gate with about a 0.96 percentage-point top-1 validation drop.
- **Parity gate:** after export, embed the full validation set through both PyTorch and ONNX paths; require mean cosine >0.99, prediction disagreement <3%, and accuracy drop <2 points before the artifact ships.
- Artifact bundle (`artifacts/`): `model.onnx`, `tokenizer/` (sentencepiece files), `classifier.joblib`, `labels.json` (index→code→leaf name→weak flag), `taxonomy.json`, `model_card.json` (version, trained date, base model, class count, thresholds, val metrics, sha256 of each file). Backend lookup rules live in `app/data/product_lookup.csv`.

---

## 3. Final architecture

```
┌────────────┐   upload    ┌──────────────────────────────┐
│  Browser   │────────────▶│  Next.js on Vercel           │
│  (user)    │◀───review───│  - UI, auth (Supabase)       │
└────────────┘   queue     │  - file parsing (server rt)  │
                           │  - chunking orchestrator     │
                           └──────┬───────────────▲───────┘
                                  │ JSON items    │ predictions
                        (OIDC ID token / API key) │
                           ┌──────▼───────────────┴───────┐
                           │  ML API — Cloud Run          │
                           │  FastAPI + onnxruntime       │
                           │  2GB / 1 vCPU / concurrency 4│
                           │  1) normalize text           │
                           │  2) product lookup           │
                           │  3) ONNX embed → LR proba    │
                           │  4) confidence → decision    │
                           │  STATELESS (no DB, no files) │
                           └──────────────────────────────┘
        ┌──────────────────────────┐
        │  Supabase                │   owns: invoices, files (Storage),
        │  Postgres + Storage +    │   line_items, predictions, review
        │  Auth                    │   queue, corrections, audit trail
        └──────────────────────────┘
        ┌──────────────────────────┐
        │  Offline (local/CI)      │   train SetFit → export ONNX →
        │  PyTorch training        │   bake into image → deploy revision
        └──────────────────────────┘
```

**Statelessness boundary (hard rule):** the ML service holds *only* the model artifacts loaded at startup and per-request data in memory. No database connection, no file storage, no job state, no feedback ingestion. Everything durable lives in Supabase. This keeps the ML container trivially replaceable, horizontally scalable, and safe to roll back.

### Parsing location: **in the app (option 1)** — decided

- ML API accepts **JSON line items only**, never raw Excel/XML/PDF.
- Reasons: parsing is business logic (per-client formats, Chilean DTE XML quirks) that will change far more often than the model — coupling it to the ML image forces model redeploys for parser fixes; raw files carry the full invoice (RUTs, amounts) which the ML service then needn't see or log; parse errors need user-facing workflow (Supabase state) that a stateless service can't own; and Vercel server routes parse XML/XLSX in milliseconds — no resource problem.
- A separate parsing microservice (option 3) is premature for one client; revisit only if parsing becomes CPU-heavy (OCR on scanned PDFs).

---

## 4. API contract

All endpoints JSON; auth per §8. Errors: `{"error": {"code": "...", "message": "..."}}` with proper HTTP status.

### `GET /health` (unauthenticated, for uptime checks)
```json
{"status": "ok", "service_version": "1.0.0", "model_loaded": true}
```

### `GET /model-info`
```json
{
  "model_version": "v1.0.0",
  "base_model": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
  "artifact_format": "onnx-int8-dynamic",
  "trained_date": "2026-07-15",
  "num_trained_classes": 67,
  "labels": [{"code": "EXP-2.5", "name": "Otros Medicamentos", "weak": false, "trained": true}, "..."],
  "thresholds": {"accept_top1": 0.70, "accept_margin": 0.10},
  "product_lookup": {"enabled": true, "version": "2026-07-01", "entries": 812},
  "artifacts_sha256": {"model.onnx": "…", "classifier.joblib": "…"}
}
```

### `POST /predict`
Request:
```json
{
  "input_id": "li_8842",
  "item_text": "VACUNA CLOSTRIBAC 8 GOLD X 50 DOS.",
  "description": "10000026",
  "provider": "COOPRINSEM",
  "invoice_metadata": {"folio": "12345", "date": "2026-06-01"},
  "top_k": 3,
  "return_debug": false
}
```
Response:
```json
{
  "input_id": "li_8842",
  "model_version": "v1.0.0",
  "source": "model",
  "predictions": [
    {"code": "EXP-2.2", "name": "Vacunas", "score": 0.91},
    {"code": "EXP-2.5", "name": "Otros Medicamentos", "score": 0.05},
    {"code": "EXP-2.6", "name": "Otros Gastos Salud Animal", "score": 0.02}
  ],
  "confidence": {"top1": 0.91, "margin": 0.86, "entropy": 0.41},
  "decision": "auto_accept",
  "reason": null,
  "latency_ms": 38
}
```
`source`: `product_lookup` | `model`. `decision`: `auto_accept` | `review_required`. `reason` (when review): `low_confidence` | `small_margin` | `weak_class` | `untrained_class` | `lookup_model_conflict` | `empty_input`.
For `product_lookup` hits, `predictions[0]` is the lookup category with `score: 1.0`, and positions 2–3 are the model's top-2 (still computed — cheap, and useful signal for conflict detection).

### `POST /predict-batch`
Request: `{"batch_id": "b_17", "items": [<predict-request objects>], "top_k": 3}` — **max 500 items** (413 if exceeded).
Response:
```json
{
  "batch_id": "b_17",
  "model_version": "v1.0.0",
  "results": ["<one /predict response or {\"input_id\":…, \"error\":…} per row, order preserved>"],
  "summary": {"count": 500, "auto_accept": 342, "review_required": 154, "errors": 4},
  "latency_ms": 21000
}
```
Per-row failures (empty text, oversized field) return an error object in that slot; the batch still succeeds. 400 only for malformed envelope.

**Why max 500:** at a conservative ~40–80ms/row on 1 vCPU (mini-batch 64 through ONNX), 500 rows ≈ 20–40s — safely inside a 300s request timeout with 5× margin. **Benchmark this before freezing the number** (open item in MLMODEL.md §8); tune to keep worst-case chunk <60s.

**No `/warmup`, no training endpoints.** Model loads at startup (lazy-load nothing); Cloud Run `min-instances` handles warmth. Training is offline by design.

---

## 5. Batch strategy: V1 app-managed chunking, V2 Cloud Run Jobs

**V1 (build now):** app splits N rows into chunks of ≤500, sends sequentially (or 2–3 in flight — Cloud Run autoscales extra instances), writes each chunk's results to Supabase as it lands, tracks progress in a `prediction_runs` row (`total/done/failed`). UI shows a progress bar; a crashed run resumes from the last stored chunk.
10,000 rows ≈ 20 chunks ≈ **7–15 min end-to-end** with 2 concurrent chunks. Retry failed chunks with exponential backoff (idempotent — same input, same output).

**Why this beats Cloud Run Jobs for V1:** zero extra infra (no job state, no GCS handoff, no polling endpoints), the ML service stays stateless, progress/resume logic lives where state already lives (Supabase), and the measured chunk latency makes timeouts a non-issue. MLMODEL.md's Cloud Run Jobs pattern was designed against an *unbenchmarked* ~83-min whole-batch estimate; chunking dissolves that problem by never holding one long request open.

**V2 trigger:** move to **Cloud Run Jobs** only if (a) batches grow ≫10k, (b) per-row cost rises (e.g. heavier model), or (c) users need fire-and-forget uploads with email notification. Design: app writes parsed rows to GCS/Supabase, triggers a Job with the object path + callback URL; the Job (same image, `python -m app.batch_worker`) writes results back and POSTs completion. The API contract for a row's result stays identical, so V2 is additive.

---

## 6. Confidence, decision policy, weak classes

Decision logic (in `confidence.py`, thresholds from `model_card.json`, overridable by env var):

```
if source == product_lookup and model_top1 == lookup_category: auto_accept
if source == product_lookup and model disagrees strongly:      review (lookup_model_conflict)
                                                               # lookup still ranked first — tier-1 client truth
elif predicted class is untrained:                             review (untrained_class)   # can't happen from LR; guarded anyway
elif predicted class is weak (<15 gold examples):              review (weak_class)
elif top1 < 0.70:                                              review (low_confidence)
elif top1 - top2 < 0.10:                                       review (small_margin)
else:                                                          auto_accept
```

- **0.70 / 0.10 are calibrated from the current validation sweep.** In this run, margins 0.10, 0.20, and 0.30 behaved the same at top1 0.70, but the shipped model card currently records 0.10. Recalibrate on each retrain.
- **Calibration:** LR probabilities over 60+ classes from few-shot data will be miscalibrated (typically overconfident). V1: don't block on it — thresholds tuned on val data absorb miscalibration. V1.1: track accuracy-by-confidence-bucket from real human feedback; if buckets are badly off, fit **Platt scaling or isotonic regression** on the accumulated feedback and add it as a tiny post-processing artifact.
- **Weak classes** (currently 30 <15 examples; list frozen into `labels.json` at export time): always review-routed regardless of score. This is the honest handling of ING-*, ADM-1.9 etc. — the model may still *rank* them top-3 for the human.
- **Adjacent-category ambiguity is a feature:** per LABELING_RULES.md, cases like the three electricity buckets are deliberately kept ambiguous in gold; the top-3 UI, not the model, resolves them. Expect and accept a persistent review rate for these.

---

## 7. Product lookup layer

**Location: inside the ML service** (versioned artifact in the image) — it's deterministic tier-1 client truth and belongs in the same decision function that arbitrates lookup-vs-model conflict; putting it in the app would split the decision logic across two codebases.

- Source: `Products list Antillanca` sheets (+ servicios + direct examples) → compiled to `app/data/product_lookup.csv` (`item_text, provider, category_code, rule_source`) for the backend.
- **Normalization** (shared by lookup keys and incoming text): uppercase → strip accents (NFD) → collapse whitespace → strip punctuation except intra-word hyphens → normalize units (`LTS|LT|LITROS→L`, `KGS|KILOS→KG`, `CC→ML` etc.) → strip trailing pack sizes for a secondary looser key.
- Matching ladder: exact normalized match (with provider if the rule has one) → exact match ignoring provider → *(V1.1)* fuzzy ≥0.93 token-set ratio, only when the fuzzy match's category agrees with the model's top-1 (fuzzy alone must not auto-accept).
- Servicios rules are forward-looking standardized descriptions — exact-match will start hitting as the client rolls out purchase-order templates. Free accuracy over time.

---

## 8. Security

**V1 (ship this):**
- ML API deployed with `--no-allow-unauthenticated`; Vercel server routes obtain a **Google OIDC ID token** (service-account key in Vercel env → `google-auth-library` `getIdTokenClient(audience=cloud-run-url)`). Google's infra rejects unauthenticated calls before they touch the container — better than any app-level API key, and free.
- If OIDC setup stalls, interim fallback: static bearer key in Secret Manager, checked in FastAPI middleware, `--allow-unauthenticated`. Replace within a sprint.
- Browser **never** calls Cloud Run; all calls via Next.js server routes (secrets stay server-side).
- No CORS headers at all on the ML API (no browser origin should ever pass preflight).
- FastAPI/Pydantic validation: max item_text 512 chars, max 500 items, reject unknown fields; uvicorn body limit ~2MB.
- Logging: **never log item text** by default — log `input_id`, text length, predicted code, score, decision, latency. `return_debug=true` responses excluded from logs.

**Production-grade (later):** dedicated SA per environment with only `roles/run.invoker`; Workload Identity Federation from Vercel (no exported keys); per-client rate limiting in the app layer; Cloud Armor only if ever exposed beyond the app.

---

## 9. Deployment — Google Cloud Run

**Verified against current Cloud Run docs/pricing (July 2026 — re-verify at implementation):** request timeout configurable to 3600s (default 300s), memory to 32GiB (2GiB needs ≥1 vCPU), concurrency default 80 (we set 4 — CPU-bound inference), pricing ~\$0.000024/vCPU-s + \$0.0000025/GiB-s active, ~10× cheaper idle rate with `min-instances`; 2M requests + generous compute in free tier.

| Alternative | Verdict |
|---|---|
| Vercel functions | ❌ model size + runtime limits; frontend only |
| AWS Lambda | ❌ 10GB image workable but cold-loading 600MB model per concurrent env + 15-min cap + worse ergonomics |
| ECS/Fargate | ❌ capability-equivalent, ~2–3× the setup/ops surface, no scale-to-zero without extra work |
| Render | viable fallback (~\$25/mo flat, simplest) if GCP friction ever outweighs cost |
| Fly.io | viable (~\$2–3/mo) but no advantage over Cloud Run; weaker managed-auth story |
| Railway | ❌ ~\$60/mo, no scale-to-zero |

**Config:** 2GB RAM / 1 vCPU / `--concurrency=4` / `--timeout=300` / `--no-allow-unauthenticated` / `min-instances=1` during business hours via two Cloud Scheduler jobs flipping the revision setting (0 overnight/weekends), `max-instances=5`. Startup probe on `/health` with 60s initial delay (model load ~10–30s). **Cost: ~\$4–6/month.**

**RAM headroom check (from MLMODEL.md §5, verified):** static ~823MB (FastAPI 80 + ORT 50 + tokenizer 50 + model 560 + numpy 35 + sklearn 47 + LR 1) + batch peak ~72MB ≈ **~895MB of 2048MB** — comfortable. 1 vCPU is enough because concurrency is capped and chunked batches keep requests short; if p95 latency disappoints, first lever is `--cpu=2` (still pennies), not architecture change.

### Docker / artifact strategy — **bake artifacts into the image (V1)**

```dockerfile
FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .                     # onnxruntime, fastapi, uvicorn, numpy,
RUN pip install --no-cache-dir -r requirements.txt   # scikit-learn, joblib, tokenizers, pydantic
COPY app/ app/
COPY artifacts/ artifacts/                  # last layer that changes per model version
ENV MODEL_DIR=/srv/artifacts
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

- **Why bake, not GCS-at-startup:** image *is* the version — `image tag == model version == git tag`, rollback = route traffic to previous Cloud Run revision (one command, seconds), no startup network dependency, no artifact/code version skew possible. ~800MB image is well within Artifact Registry norms.
- Switch to GCS-at-startup only if model >2–3GB or model updates must decouple from code deploys. The `MODEL_DIR` env var already abstracts this.
- **No PyTorch in the image, ever** — deliberate ~350MB RAM saving (MLMODEL.md §7 guardrail).

### CI/CD (GitHub Actions)

1. PR → lint + pytest (unit tests with a tiny stub ONNX model so CI doesn't need the real 560MB artifact).
2. Merge to `main` → build image → push `us-…-docker.pkg.dev/PROJECT/ml/invoice-classifier:v{X.Y.Z}` → deploy to **staging** Cloud Run service → smoke test (`/health`, `/model-info`, golden-file `/predict` assertions on ~20 canonical items).
3. Manual approval → deploy same image to **production** with `--tag` + gradual traffic (100% is fine at this scale).
4. Model-only release = same pipeline, bump artifact dir + version. Rollback = `gcloud run services update-traffic --to-revisions=PREV=100`.
5. Real artifacts live in **GCS** (`gs://mct37-models/v1.0.0/…`) as the archive of record; CI pulls the pinned version into the build context by sha256 from `model_card.json`.

---

## 10. Supabase schema (app-owned state)

```sql
invoices(id, file_path, uploaded_by, status, created_at, …)
line_items(id, invoice_id, raw_text, item_text, description, provider, parsed_meta jsonb)
predictions(id, line_item_id, model_version, source, predictions jsonb,  -- top-3
            top1_score, margin, decision, reason, created_at)
reviews(id, line_item_id, prediction_id, assigned_state,                 -- pending|done
        selected_code, selected_by, selected_at, was_correction boolean)
prediction_runs(id, invoice_id, total, done, failed, status, model_version, created_at)
-- feedback export view: every review row where selected_code is final =
--   (item_text, description, provider, selected_code, was_correction, model_version)
```

Auto-accepted rows also get a `reviews` row (`assigned_state=done`, `selected_code=top1`, `was_correction=false` unless a user later overrides) — **overrides of auto-accepts are the drift alarm**, so they must be first-class data.

---

## 11. Frontend plan (Next.js on Vercel)

Pages/flows (Supabase Auth gating everything):
1. **Upload** — drag-drop Excel/XML/PDF → Supabase Storage → server route parses to line items → `invoices` + `line_items` rows → kicks off chunked prediction run with live progress (Supabase Realtime or polling `prediction_runs`).
2. **Invoice view** — table of line items: predicted category, confidence badge, ✅ auto-accepted / ⚠ needs review. Inline override on any row.
3. **Review queue** — the core screen. One item at a time or grid: item text + provider, **three big top-3 buttons** (code + Spanish leaf name + score), searchable dropdown of all 72 categories as fallback, keyboard shortcuts (1/2/3, arrows). Every choice writes `reviews` + audit fields. Show `reason` (“weak category — few training examples”) so users trust the routing.
4. **Export** — final categorized items to Excel/CSV for the accounting flow.
5. **Admin/metrics** — model version, auto-accept rate over time, correction rate, per-category correction hot-spots, review backlog.

Server routes: `POST /api/invoices` (upload+parse), `POST /api/invoices/:id/classify` (chunk orchestrator → Cloud Run), `POST /api/reviews/:id` (selection), `GET /api/metrics`.

---

## 12. Human-in-the-loop retraining lifecycle

```
predictions → auto-accept OR review → user selection → reviews table
     ▲                                                      │
     │                                   monthly (or ~300+ new labels)
     │                                                      ▼
new revision ◀─ CI build ◀─ export ONNX ◀─ retrain ◀─ export feedback CSV
                                              ▲                │
                                              └── merge into gold per
                                                  LABELING_RULES (audited,
                                                  source=user_feedback tier)
```

- Feedback export = SQL view → CSV matching gold-master columns; **human corrections enter gold only through the existing audit rules** (they're tier-3-like until spot-checked — add `source=user_feedback` to LABELING_RULES when first batch arrives).
- Retrain cadence: after the first ~300–500 corrections, then monthly. Each retrain: full SetFit run from the updated gold master (dataset is small — no incremental complexity worth it), fresh val split, threshold recalibration, model card diff (per-class F1 vs previous) reviewed before deploy.
- Success loop: descriptive future invoices (client promise) + servicios templates + corrections → weak classes cross the 15-example line → `weak` flags retract → auto-accept rate climbs. **Report this rate to the client monthly** — it is the product's KPI.

---

## 13. Observability

- **Structured JSON logs** (Cloud Logging): request_id, input_id, batch_id, model_version, source, top1 code+score, margin, decision, reason, latency_ms, batch size. **No invoice text.**
- **Metrics** (log-based metrics or Cloud Monitoring): request count, p50/p95/p99 latency, error rate, cold-start count, memory utilization, auto-accept vs review ratio, per-reason review counts, confidence histogram, predicted-label distribution.
- **Alerts:** error rate >2% (5 min), p95 >5s, memory >85%, auto-accept rate shifts >10 points day-over-day (**drift proxy**), instance count pinned at max.
- **Drift/quality (app-side, from Supabase):** weekly correction rate overall + per category; accuracy-by-confidence-bucket (feeds calibration §6); alert when a category's correction rate >30%.

---

## 14. Repository structure

```
ml-service/
  app/
    main.py                 # FastAPI init, startup model load, middleware
    api/routes.py           # /health /model-info /predict /predict-batch
    api/schemas.py          # Pydantic request/response models
    inference/
      predictor.py          # orchestrates lookup → encode → classify → decide
      onnx_encoder.py       # ORT session, tokenization, mini-batch=64 loop
      classifier.py         # joblib LR wrapper
      confidence.py         # thresholds + decision policy (§6)
      product_lookup.py     # normalization + matching ladder (§7)
      normalize.py          # shared text normalization
    core/config.py          # env-driven settings (MODEL_DIR, thresholds, auth mode)
    core/logging.py         # structured JSON, redaction guarantee
    core/model_loader.py    # loads + sha256-verifies artifact bundle at startup
  artifacts/                # baked at build; pulled from GCS by CI (not committed)
  training/                 # NOT shipped in image
    train_setfit.py  export_onnx.py  evaluate.py  calibrate_thresholds.py
    build_lookup_artifact.py
  tests/                    # stub-model unit tests + golden-file API tests
  Dockerfile  requirements.txt  requirements-train.txt  README.md
```

(Improvement over the draft: `training/` in-repo but outside the image — training code must be versioned with the artifact recipe; `normalize.py` shared so lookup and any future preprocessing can't diverge.)

---

## 15. V1 implementation checklist (ordered)

1. ✅ Train SetFit on current 1,604 gold rows (`training/train_setfit.py`); record macro-F1, top-3 acc, per-class report. **Do not wait for Audisis** — this is the honest-baseline V1; weak classes are review-routed anyway.
2. ✅ Export ONNX int8 + parity gate; assemble artifact bundle + model card.
2a. ✅ Build backend product lookup CSV from client product/service/example rules.
3. ☐ Benchmark: single-row and 500-row latency on a 1 vCPU container locally (`docker run --cpus=1 -m 2g`). Freeze max batch size from data.
4. ☐ Calibrate thresholds on val set (accept-rate/accuracy curve).
5. ☐ Build FastAPI service per §4/§14 + tests.
6. ☐ Dockerfile, Artifact Registry, staging Cloud Run deploy, smoke tests.
7. ☐ OIDC service-to-service auth from a Vercel server route.
8. ☐ Supabase schema (§10) + parsing route + chunk orchestrator.
9. ☐ Review-queue UI + invoice table + export.
10. ☐ Logging/metrics/alerts (§13). Production deploy + Cloud Scheduler min-instance schedule.
11. ☐ First-week shadow period: everything review-routed (thresholds forced high) to validate real accuracy before enabling auto-accept.

## 16. V2 roadmap

- Cloud Run Jobs batch path (only on §5 triggers). Isotonic/Platt calibration from feedback. Fuzzy lookup tier. Provider-conditioned features or per-provider priors. GCS artifact loading if model grows. Multi-client tenancy (per-client lookup + thresholds; model shared until data says otherwise). Retraining automation (scheduled export → train → eval-gate → staged deploy).

## 17. Risks & mitigations

| Risk | Mitigation |
|---|---|
| 30 classes <15 examples → poor recall on them | weak-class review routing; servicios templates + feedback close the gap; report per-class coverage monthly |
| ING-* nearly absent (sales, not purchases) | untrained/weak flags; explicit fallback UX; wait for client sales data — **do not fabricate** |
| LR overconfidence → wrong auto-accepts | threshold calibration on val; week-1 shadow mode; bucket-accuracy tracking; correction-rate alarm on auto-accept overrides |
| Latency worse than estimated on 1 vCPU | benchmark is checklist item 3 *before* freezing batch size; lever: `--cpu=2` |
| Architecture drift (frozen-encoder hallucination, again) | MLMODEL.md + this file are the guardrails; any deviation requires editing them first |
| Client data delay blocks "final" model | ship baseline V1 now; versioned retrains are the designed path, not a workaround |
| Cold starts annoy business-hours users | scheduled min-instances=1; startup probe; 60s worst case only off-hours |
| Sensitive invoice data in logs | redaction-by-default in `core/logging.py`; only IDs + scores logged |

## 18. Questions to confirm before implementation

1. Auto-accept accuracy tolerance — is 95%-of-accepted-rows-correct acceptable, or stricter? (sets thresholds)
2. Expected volume: invoices/week and rows/invoice? (validates chunking math + cost)
3. Business hours for min-instances schedule (America/Santiago)?
4. May corrected labels be used for retraining without per-item client sign-off? (feedback-loop legal/consent)
5. Excel/XML DTE format samples for the parser — which exact layouts must V1 parse?
6. Who reviews? one accountant or a team? (queue assignment UX)
7. GCP project + billing owner: MC Tech or Audisis? (SA/IAM setup)
