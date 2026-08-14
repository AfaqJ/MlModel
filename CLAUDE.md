# MCT-37 — invoice line-item classifier for Antillanca

Classifies Spanish invoice line items into accounting categories for
**Antillanca**, a Chilean dairy/agriculture client of Audisis / Grupo ProGestión.

**Status:** v1.3.3 live on Cloud Run — service `mlmodel`, `europe-west1`,
revision `mlmodel-00014-lrp`, 100% traffic. Supabase holds 11,746 corrected
lines as of 2026-08-14.
**Branch:** `codex/transaction-aware-retrain-v2` (dirty — see `docs/STATE.md`).

## What this is

Input is an invoice line: `item_text`, `description`, `provider`, plus the
COMPRAS/VENTAS direction from the folder the document came from. Output is top-3
category codes with confidence, and a decision: `auto_accept` or
`review_required`.

The product is **human-in-the-loop by design**. 74 categories are live, but the
deployed model emits only 67 — the three added on 2026-08-14 are rule-assigned
and it cannot predict them (D-028). `Data/gold/_master_gold.csv` holds 2,577 rows
across 73 classes, 2,329 of them distinct model inputs. Many classes have very
few examples, so the model cannot be trusted alone: the review gate is a feature,
not a shortfall. Of 11,746 lines, 7,014 (60%) are auto-accepted and 4,732 (40%)
sit in review.

The system is two halves that are easy to confuse: an **offline labeling
pipeline** (raw XML → gold → Supabase) and an **online classifier service**
(FastAPI on Cloud Run). The classifier is a tool used by the pipeline.

## Hard limits

- `predicted_code` is **never** a final business classification when
  `decision=review_required`. Displaying it as one caused the production
  incident. Root cause is D-001; the full trace is in git history.
- Any dedup key on training rows must contain **every field the model
  consumes**. The input template is now
  `[transaction_type] | item_text | description | provider`, so dedup happens on
  the *built* string — see D-013, which supersedes D-001's narrower key. A key
  narrower than the input is what destroyed 47 milk-sale rows.
- Never promote an unaudited row to gold. See `docs/LABELING_RULES.md`.
- A client-sourced label outranks any number of rows that disagree with it.
  See `docs/CLIENT_CONVENTIONS.md` — counting rows got this wrong twice.
- Supabase is already loaded. Re-load with `scripts/82_apply_label_corrections.py`;
  script 80 is first-load only and will refuse.
- Never modify `Data/Raw_Data/` — it is the only irreplaceable thing here.
- Never overwrite `artifacts/v1.0.0/` or `artifacts/v1.1.0/` (protected paths).
- Never release on aggregate accuracy alone. The income slice is a mandatory
  gate — see `docs/TEST_CHECKLIST.md`.
- Supabase writes require an explicit flag. `Temp_Inference/.env.loader` holds
  live keys: never echo them, never commit them.
- A class with fewer than 2 examples cannot be trained and must fail **loudly**.

## Where to look

| Need | File |
|---|---|
| Where we are, recent sessions, next steps | `docs/STATE.md` |
| How the system is built | `docs/ARCHITECTURE.md` |
| Why it is built that way | `docs/DECISIONS.md` |
| What may enter the gold dataset | `docs/LABELING_RULES.md` |
| How the client wants things labelled | `docs/CLIENT_CONVENTIONS.md` |
| What counts as proof before shipping | `docs/TEST_CHECKLIST.md` |
| How to undo a deploy, an upload, a retrain | `docs/ROLLBACK.md` |
| Hard boundaries, in full | `docs/CONSTRAINTS.md` |

Every file listed above is current. Nothing here is historical — superseded
docs are deleted, not archived, and live only in git history.

## Conventions

Two virtualenvs, deliberately: `.venv-train` has PyTorch, `.venv-backend` does
not. PyTorch must never reach the production container.

```bash
.venv-backend/bin/python -m pytest tests/ -q     # 98 tests, all must pass
```

Deploy is **container-only** — `gcloud builds submit` → Artifact Registry →
`gcloud run deploy`. Git is never in the path, which is what keeps the 278 MB
`.onnx` from becoming an LFS pointer. `.gcloudignore` is **required**: without
it `gcloud` falls back to `.gitignore`, which excludes `artifacts/*`, and the
image builds fine with no model inside.
