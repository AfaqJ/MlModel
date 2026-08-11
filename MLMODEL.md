# MCT-37 — Invoice Line-Item Classifier (Antillanca / Audisis)

**Status as of: July 5, 2026**
**This document is the source of truth for architecture decisions. Do not drift from this without explicit re-discussion.**

---

## 1. What this project is

An invoice line-item classification system for **Antillanca**, a Chilean dairy/agriculture client of Audisis / Grupo ProGestión.

**Input:** Spanish invoice line-item text — `item_text`, `description`, `provider` fields (e.g. `VACUNA CLOSTRIBAC 8 GOLD X 50 DOS.`, `TERIL 5 LTS.`, `FERTILIZACION UREA 50 kg`).

**Output:** Top-3 category predictions with confidence scores, for human-in-the-loop review when confidence is low.

---

## 2. The data

- Taxonomy: **71 current model categories** in `Data/current_context_2026_06_30/taxonomy_from_plan.csv`, plus 7 excluded accounting/no-XML categories in `excluded_categories.csv`.
- Gold labeled dataset: **1,604 audited rows**, stored at `Data/gold/_master_gold.csv`.
- Coverage: **70/71 categories have at least one gold row**; `ING-0.5` has zero.
- Weak data: **31 categories have fewer than 15 gold examples** and must be review-routed.
- Trained classes: **66**. Categories with fewer than 2 examples were excluded from the LR head: `ADM-1.9`, `ING-0.1`, `ING-0.3`, `ING-0.6`; `ING-0.5` is also untrained because it has zero examples.
- Client product/service/example rules are now compiled into `app/data/product_lookup.csv` for deterministic lookup before model judgment.

---

## 3. The ML model — FINAL, do not drift from this

### Framework: SetFit (few-shot fine-tuning)

**Not** a frozen encoder + logistic regression setup. This distinction matters and was the source of a prior hallucination-drift incident in a handover prompt (see Section 7).

**How it works:**
1. SetFit generates sentence pairs from the labeled examples — positive pairs (same class, "should be close") and negative pairs (different class, "should be far apart").
2. It contrastively fine-tunes the sentence transformer itself on these pairs, reshaping the embedding space so that items in the same category cluster together — not just generically similar Spanish text, but similarity specific to *these 69 categories*.
3. After fine-tuning, all labeled examples are re-embedded using the now-fine-tuned transformer.
4. A logistic regression head is trained on those fine-tuned embeddings (this happens automatically as part of `trainer.train()` — not a separate manual step).

**Why SetFit and not frozen encoder + LR:** With only 20–50 examples per class across 69 classes, a frozen generic embedding space doesn't have enough signal for logistic regression to draw 69 reliable decision boundaries, especially between semantically adjacent categories (e.g. multiple `EXP` subcategories that are all farm supplies). SetFit's contrastive fine-tuning step is specifically designed to work with few-shot data (originally validated down to 8–32 examples per class) and shapes the embedding space around the actual categories first, making the classifier's job far easier.

**Base model: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`**
- 278M parameters, supports 50+ languages.
- This is the exact model used in the original SetFit research paper for Spanish/multilingual experiments.
- Chosen over `BAAI/bge-m3` (560M params, ~1GB, designed for long documents/hybrid retrieval — overkill for short invoice text) and over `paraphrase-multilingual-MiniLM-L12-v2` (smaller, ~85MB, but lower quality ceiling).
- Research comparing multilingual models for SetFit found `paraphrase-multilingual-mpnet-base-v2` outperforms larger models like XLM-RoBERTa-Large for this specific use case, because it was pretrained on paraphrase detection — a strong prior for "these mean the same thing," which is exactly what SetFit builds on.

**Output / inference:**
```python
model.predict_proba(["TERIL 5 LTS."])
# Returns array of 69 probabilities, one per class
# Sort descending, take top 3, return (label, score) pairs
```

---

## 4. Deployment — ONNX serve-time optimization

**Important context:** this is **cloud-hosted, not on the client's machine.** (An earlier handover incorrectly described EmbeddingGemma-300m + frozen LR sized for Vercel serverless limits — that was a deviation tied to a since-abandoned Vercel-only deployment idea. Current plan deploys on Google Cloud Run.)

**Training (local machine):**
- PyTorch + sentence-transformers
- SetFit fine-tuning happens here, never in production

**Export step (after fine-tuning):**
- Export the fine-tuned model to ONNX fp32, then apply **ONNX int8 dynamic quantization**.
- Int8 was chosen over fp16 because Cloud Run is CPU-only and ONNX Runtime does not get native fp16 CPU speedups for this model. Int8 is smaller and faster on CPU, with only about a 0.96 percentage-point top-1 validation drop.

**Serve-time container:**
- Only `onnxruntime` is installed — **PyTorch is never deployed to production**
- This saves ~350MB RAM vs. a PyTorch-based deployment
- mpnet ONNX int8: ~278MB on disk

**Classifier:**
- scikit-learn LogisticRegression, trained on the SetFit-fine-tuned embeddings
- Weight matrix for 69 classes × 768 dims is trivial in size (~1MB)

---

## 5. RAM budget (2GB / 1 vCPU Cloud Run instance)

**Static (always loaded):**

| Component | RAM |
|---|---|
| Python + FastAPI + uvicorn | ~80 MB |
| ONNX Runtime library | ~50 MB |
| Tokenizer (sentencepiece) | ~50 MB |
| mpnet ONNX int8 model weights | ~278 MB |
| numpy | ~35 MB |
| scikit-learn runtime | ~47 MB |
| LR classifier weights | ~1 MB |
| **Static total** | **~823 MB** |

**Batch job (additional, during a 10,000-row processing run):**

| Component | RAM |
|---|---|
| Raw text data (10k rows) | ~5 MB |
| Pandas DataFrame | ~25 MB |
| One mini-batch of tokens (batch size 64) | <1 MB |
| All 10k embeddings accumulated (float32) | ~29 MB |
| LR probability output (10k × 69 classes) | ~3 MB |
| Results DataFrame | ~10 MB |
| **Batch peak** | **~72 MB** |

**Peak total is expected to stay comfortably inside the 2GB Cloud Run budget.** The actual artifact is smaller than the older fp16 estimate, but final memory should still be checked inside Docker before production.

Batch processing uses mini-batches of 64 rows fed through ONNX sequentially — only one mini-batch of token data exists in RAM at any moment. Embeddings accumulate linearly (29MB for 10k rows) but token/input data does not.

---

## 6. Infrastructure

- **Backend:** FastAPI + uvicorn on **Google Cloud Run**
- **Config:** 2GB RAM, 1 vCPU
- **Scheduling:** `min-instances=1` during business hours (via Cloud Scheduler), scale-to-zero outside business hours
- **Estimated cost:** ~$4–6/month (verified against Google Cloud Run pricing: ~$0.000024/vCPU-second active, ~$0.0000025/vCPU-second idle, ~$0.0000025/GiB-second memory; idle instances during business hours billed at the reduced idle rate, not the active rate)
- **Batch pattern for V1:** the app parses uploads, splits line items into chunks, and calls the Cloud Run service `/predict-batch`. Cloud Run Jobs remain a V2 option only if batches become much larger or users need fire-and-forget processing.
- **Frontend:** Next.js, deployed on Vercel (frontend only — backend was explicitly rejected from Vercel due to its 800-second function timeout, which cannot accommodate a ~83-minute batch job for 10,000 rows)

### Rejected alternatives
- **Vercel for backend:** 800s timeout vs. ~5,000s batch job — hard incompatibility
- **AWS Lambda:** 15-minute hard timeout — same class of problem, just longer
- **Roboflow / hosted model APIs:** these are real-time single-item inference APIs. They don't solve the timeout problem (the backend calling them would still need to make 10,000 sequential/batched calls and would itself time out) and introduce per-call cost unsuitable for a weekly 10k-row batch. Rejected.
- **AWS ECS Fargate:** comparable capability to Cloud Run but ~12 setup steps vs. Cloud Run's ~5, no clear advantage for this use case
- **Render:** simplest setup (~$25/month flat, no scale-to-zero) — viable fallback if simplicity is prioritized over cost, but not the primary choice
- **Railway:** ~$60/month, no scale-to-zero — not recommended
- **Fly.io:** ~$2.32/month with scale-to-zero — viable alternative, no clear advantage over Cloud Run

---

## 7. Key learnings & guardrails

**SetFit architecture must not drift.** Any future handover prompt or session that suggests a frozen encoder + logistic regression setup (instead of SetFit's contrastive fine-tuning of the transformer itself) is incorrect and should be corrected back to this document. This exact drift happened once already — a handover prompt described EmbeddingGemma-300m ONNX + frozen LogisticRegression, sized for a Vercel serverless budget that no longer applies. It was traced back to LLM hallucination drift across sessions and corrected back to the original SetFit decision after reviewing the actual gold-labeled dataset.

**ONNX for serve-time, PyTorch for training only.** Keeping PyTorch out of the production container is a deliberate RAM-saving decision, not an oversight.

**Chunked Cloud Run service first; Cloud Run Jobs later if needed.** The current blueprint uses app-managed chunks so the ML service stays stateless and simple.

**Verify before stating figures.** RAM, cost, and model-size figures in this document were checked against current sources/benchmarks rather than estimated from memory. Re-verify if reused much later, as pricing and benchmark numbers can shift.

---

## 8. Open items / not yet done

- ✅ Model trained and exported as `artifacts/v1.0.0/`
- ✅ Reference inference works without PyTorch/SetFit/sentence-transformers
- ✅ Product lookup CSV generated at `app/data/product_lookup.csv`
- ❌ `ING-0.5` has zero examples; `ADM-1.9`, `ING-0.1`, `ING-0.3`, `ING-0.6` have too few examples for training
- 🟡 FastAPI backend skeleton exists but still needs full dependency install, HTTP test run, Docker benchmark, and deployment validation
- ✅ Dockerfile written; still needs local Docker build/benchmark
- ❌ Deployment not yet executed — currently in planning/architecture phase
- ❌ SetFit inference latency per row / per 10k-row batch not yet benchmarked

---

*MC Tech Studio internal document — MCT-37, Antillanca invoice categorization (Audisis / Grupo ProGestión). Last updated: June 2026.*
