# MCT-37 — invoice line-item classifier for Antillanca

Classifies Spanish invoice line items into accounting categories for
**Antillanca**, a Chilean dairy/agriculture client of Audisis / Grupo ProGestión.

**Status:** v1.3.3 live on Cloud Run — service `mlmodel`, `europe-west1`,
revision `mlmodel-00014-lrp`, 100% traffic. Supabase holds 11,746 corrected
lines as of 2026-08-19: **7,335 auto-accepted, 4,411 in review**, 77 categories.

**Live and the staged payload are identical — nothing is pending.** Both
uploads of 2026-08-19 landed and were verified independently against live.
`002_add_manual_recategorisation_source.sql` is **applied to production**; live
carries all 8 `prediction_source` values. Latest backup:
`backups/supabase_20260819T064303Z/`.
**Branch:** `codex/transaction-aware-retrain-v2` (dirty — see `docs/STATE.md`).

`app/data/product_lookup.csv` was audited entry by entry on 2026-08-18 by an
independent Codex pass — **1 finding in 696, not actionable.** It is clean; do
not re-audit it. The client brief listing every open question is at
https://claude.ai/code/artifact/47769557-4221-4b7d-a29c-00ca2d3d88a7

**Item-catalog canonicalization is parked, awaiting a client meeting.** Live
`item_catalog` holds 5,411 entries for 11,746 invoice lines, because the item
name is the key and it often carries a changing value (a meter reading, a
contract number, a date). No cleanup has been applied and none should be
started until the client answers the open questions — see `docs/STATE.md`.

## What this is

Input is an invoice line: `item_text`, `description`, `provider`, plus the
COMPRAS/VENTAS direction from the folder the document came from. Output is top-3
category codes with confidence, and a decision: `auto_accept` or
`review_required`.

The product is **human-in-the-loop by design**. 77 categories are live; the
deployed model emits **67** — read it from `artifacts/v1.3.3-int8/labels.json`
(`classifier_classes`), never by subtracting from the category table. The six
added on 2026-08-14/17 are rule-assigned and cannot be predicted (D-028); four
more carry `trained: false`. `Data/gold/_master_gold.csv` holds 2,577 rows
across 73 classes, 2,329 of them distinct model inputs. Many classes have very
few examples, so the model cannot be trusted alone: the review gate is a feature,
not a shortfall. Of 11,746 lines, 7,335 (62%) are auto-accepted and 4,411 (38%)
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
  See `docs/CLIENT_CONVENTIONS.md` — counting rows got this wrong twice. Where
  the client filed the same kind of item consistently, that filing beats the
  model too (D-040); the model disagreeing is usually the undertraining.
- Never resolve in the payload a question currently open with the client (D-041).
- Read the backing gold `source`, never the `prediction_source` tag —
  `client_evidence_backfill` asserts an authority none of its 612 rows has (D-042).
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
| The complete staged Supabase payload | `reports/recovery_v1_3_3/supabase_upload/` |
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

For a full database re-load, mutate only the staged JSONL payload through a
numbered correction script, run it dry, back up live with script 81, then use
script 82. Script 82 preserves the existing Supabase schema and re-resolves all
database-generated IDs from live before upserting whole rows.

Deploy is **container-only** — `gcloud builds submit` → Artifact Registry →
`gcloud run deploy`. Git is never in the path, which is what keeps the 278 MB
`.onnx` from becoming an LFS pointer. `.gcloudignore` is **required**: without
it `gcloud` falls back to `.gitignore`, which excludes `artifacts/*`, and the
image builds fine with no model inside.
