# CONSTRAINTS — what must never happen

Read this before any change. These are hard boundaries, not preferences.

The worst of them are repeated in the root `CLAUDE.md`, which auto-loads every
session. This file is the full list.

> **Note on phase constraints.** The Aug-11 recovery phase froze Supabase
> writes, git pushes and Cloud Run deploys. **Those constraints have expired** —
> the v1.3.3 upload and deploy both happened on 2026-08-12 and were the intended
> outcome. What remains below are permanent boundaries. If a future phase needs
> a freeze, add it under a dated heading and remove it when the phase ends.

## Data that cannot be replaced

- Never delete or modify raw XML under `Data/Raw_Data/`. Everything else in the
  project is derivable; this is not.
- **The gold that v1.3.3 actually trained on is
  `Data/candidates/recovery_v1_3_2/master_gold.csv`** — 1,837 rows, 1,582
  distinct model inputs, with `split_seed42.csv` beside it.
  `Data/gold/_master_gold.csv` (2,262 rows) is the *older* lineage and is not
  what production runs on. Do not conflate them.
- **Trap:** `training/train_recovery_setfit.py` still *defaults* to
  `Data/candidates/recovery_v1_3_1/`. `training/export_recovery_onnx.py`
  defaults to `recovery_v1_3_2`. Always pass `--gold` and `--split` explicitly;
  never rely on the trainer's default, or you will silently retrain on the
  previous generation's data.
- The per-category CSVs in `Data/gold/` are generated views — never edit them
  directly.
- Never promote a row to gold from an unaudited source. Ollama's first-pass
  guesses (`audited=N`) are not gold. See `LABELING_RULES.md`.
- Synthetic training rows must be flagged (`source=synthetic_*`) and must never
  carry a folio, row_id, or any field implying they are a real invoice.

## Training

- **Any dedup key applied to training rows must include every field the model
  consumes.** The input template is now
  `[transaction_type] | item_text | description | provider`, and
  `transaction_type` is **required**. Dedup therefore happens on the *built*
  string — see D-013, which supersedes D-001's narrower field tuple. If the
  template changes again, the key changes in the same commit. A key narrower
  than the input is what destroyed 47 milk-sale rows and caused the incident.
- A category with fewer than 2 examples cannot be trained (SetFit needs a
  positive pair). This must fail **loudly**, not silently. See BUG-001.
  `ADM-1.9` and `ADM-2.3` are currently excluded as untrained; 26 classes have
  fewer than 15 distinct examples and are review-routed by the weak-class guard.
- Never release on aggregate accuracy alone. The income slice is a mandatory
  gate. See `TEST_CHECKLIST.md`.

## Artifacts and models

- Never overwrite `artifacts/v1.0.0/` or `artifacts/v1.1.0/` — protected paths.
- Never overwrite `models/setfit_base/` — it is the base encoder and a protected
  path in the trainer. New training writes to a distinct directory.
- `models/setfit_base_recovery_v1_3_1` is the A/B baseline in `scripts/77`;
  `models/setfit_base_v1_2_0` and `setfit_base_recovery_v1_2_0` are still
  referenced by `scripts/58`, `61`, `62`. Delete those scripts before reclaiming
  the ~2.2 GB.
- **PyTorch must never reach the production container.** That is a deliberate
  RAM decision (~350 MB), not an oversight. `.venv-backend` has no torch.
- INT8 substitution can never be silent. Both gate ceilings are explicit flags
  defaulted tight (`--allow-top1-disagreement` 0.03,
  `--allow-threshold-decision-disagreement` 0.0) and are stamped into the model
  card. On every retrain, re-measure — flip count is a property of the specific
  weights, not of quantization in general.

## Runtime behaviour

- **Never treat `predicted_code` as a final business classification when
  `decision=review_required`.** This is the display error that caused the
  incident, and it is still live in the frontend today.
- The ML service must never become a system of record. Supabase owns state.
- Guards in `app/inference/` may only ever *downgrade* a decision to review.
  None of them may promote one.
- No hardcoded per-word Spanish gates in the runtime. Twelve were added once and
  removed on Afaq's instruction — the fix belongs in data and training. See
  D-023.

## Secrets and writes

- `Temp_Inference/.env.loader` holds live Supabase keys. Never read them into a
  script that also writes, never echo them, never commit them.
- Supabase writes require an explicit flag on `scripts/supabase_rest.py`. Dry
  run is the default and must stay the default.
- `.gcloudignore` must exist and must keep its `artifacts/*` re-exclude line.
  Without the file, `gcloud` falls back to `.gitignore` and ships an image with
  no model inside.

## Scope discipline

Out of scope by explicit instruction, unless reopened:

- document-type routing (credit notes, exempt/debit invoices) — direction comes
  from the COMPRAS/VENTAS folder, which Supabase already stores. See D-010.
- auditing the remaining unverified silver rows;
- resolving the 77 conflicting-verdict item names;
- **all** item-catalog canonicalization work, including local prototypes. Parked
  2026-08-18 pending a client meeting; the earlier prototype was deleted rather
  than kept, so there is nothing to resume. Do not restart it — not the schema,
  not the clustering, not a "quick" normalisation pass — until the client's
  answers are in. See D-034 and `docs/STATE.md` Next #1.
