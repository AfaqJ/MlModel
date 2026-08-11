# CONSTRAINTS — what must never happen

Read this before any change. These are hard boundaries, not preferences.

## Network / data egress

- **Nothing is pushed to Supabase.** No `--write`, no REST POST/PATCH, no upserts.
  All work in the current phase is local-only.
- **Nothing is pushed to git remote.** Commit locally if asked; never `git push`.
- **Nothing is deployed to Cloud Run** in this phase.
- `Temp_Inference/.env.loader` holds live Supabase keys. Never read them into a
  script that also writes, never echo them, never commit them.

## Artifacts and models

- **Never overwrite `artifacts/v1.1.0/`.** It is the deployed model and the
  baseline we compare against. New training produces `v1.2.0`.
- **Never overwrite `models/setfit_base/`** while v1.1.0 is still the reference.
  New training writes to a distinct directory.
- Never delete or modify raw XML under `Data/Raw_Data/`.

## Training data

- `Data/gold/_master_gold.csv` is the only source of truth for training.
  Per-category CSVs in `Data/gold/` are generated views — never edit them directly.
- **Any dedup key applied to training rows must include every field that the
  model consumes.** See DECISIONS.md D-001. Today the model input is
  `item_text | description | provider`, so the dedup key is
  `(item_text, description, provider, category_code)`.
- Never promote a row to gold from an unaudited source. Ollama's first-pass
  guesses (`audited=N`, 596 rows) are not gold.
- Synthetic training rows must be explicitly flagged (`source=synthetic_*`) and
  must never carry a folio, row_id, or any field implying they are a real invoice.

## Model behavior

- A category with fewer than 2 examples cannot be trained (SetFit needs a
  positive pair). This is enforced in `training/train_setfit.py`. It must fail
  loudly, not silently — see BUG-001.
- Never release on aggregate accuracy alone. Income slice accuracy is a
  mandatory gate. See TEST_CHECKLIST.md.
- Never treat `predicted_code` as a final business classification when
  `decision=review_required`.

## Scope discipline

Out of scope for the current phase, by explicit instruction:

- document-type routing (credit notes, exempt/debit invoices) — direction comes
  from the COMPRAS/VENTAS folder, which Supabase already stores;
- auditing the 596 unverified silver rows;
- resolving the 77 conflicting-verdict item names;
- the ~8,000 line items never labeled by Ollama;
- item catalog / alias canonicalization;
- dashboard and display-contract work.
