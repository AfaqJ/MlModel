# Handover prompt — paste this into a new session

Copy everything below the line into a fresh Claude Code session in
`/Users/afaq/Desktop/Mctech/ML-model`.

---

You are continuing work on MCT-37, the Antillanca invoice classifier. Read the
documents listed below **before writing any code**. They exist because this
project had a production incident and a lot of hard-won detail would otherwise be
re-derived wrongly.

## Read these first, in this order

1. `docs/README.md` — the whole story in plain English. Start here. Covers what
   broke, why, what was fixed, what got worse, and mistakes made along the way.
2. `docs/HANDOVER.md` — current state, key numbers, and the traps a new session
   falls into.
3. `docs/DECISIONS.md` — 11+ numbered decisions with reasoning. Do not reverse
   any of these without reading the entry first; several encode expensive
   lessons.
4. `docs/BUG-001-milk-sales-misclassification.md` — the incident, fully traced
   with evidence.
5. `docs/RESULTS-v1.2.0.md` — before/after numbers for the retrained model,
   including the regressions.
6. `docs/CONSTRAINTS.md` — hard boundaries. **Read before touching anything.**
7. `docs/TEST_CHECKLIST.md` — what must pass before anything ships.
8. `docs/ROLLBACK.md` — how to undo each step.
9. `docs/ARCHITECTURE.md` and `docs/FLOW.md` — system shape and call paths.
10. `CONTEXT_HANDOVER.md` (repo root) — long-form background from an earlier
    session. Older than `docs/`; where they disagree, `docs/` wins.

## The one-paragraph summary

A dairy client's milk-sale invoices were shown as road-maintenance expenses. Root
cause: a de-duplication script compared training rows by item name only,
collapsing 47 distinct milk rows to 1; the trainer then silently dropped any
category with fewer than 2 examples, so "milk sales" was never a class the model
could predict. It scored 15% confidence and the system correctly flagged all 125
sales lines "needs review" — but the dashboard displayed those guesses as final
answers and hid the confidence. **Two failures: a missing category, and a
display contract that presented uncertainty as fact.** The second one is what
destroyed client trust and is still unfixed.

## What is already done

- **Gold training data repaired.** 1,733 → 2,262 rows, 66 → 69 trainable
  categories, and **zero contradictory rows** (verified). Milk went 1 → 48
  examples with 10 held out for honest testing.
  - `scripts/56_promote_silver_to_gold.py` — re-promotes audited silver with a
    dedup key matching the model's real input, and refuses to add a row that
    contradicts established gold.
  - `scripts/57_harvest_sales_gold.py` — harvests sales rows from raw invoices,
    quarantines purchases mislabeled as sales, adds synthetic floor rows, marks
    a holdout slice.
  - Both are dry-run by default and back up gold before writing.
- **Training pipeline hardened** (`training/train_setfit.py`): holdout-aware
  split, synthetic rows can never reach validation, loud reporting of excluded
  and unvalidated classes, refuses to overwrite an existing model directory,
  income-slice metrics reported separately.
- **Deterministic business rules + direction masking** (NEW, in the inference
  path, tested end-to-end but NOT yet re-run over the full dataset):
  - `app/data/business_rules.csv` — versioned rules keyed on
    (transaction_type, item_text). Two actions: `assign` a known category, or
    `review` meaning "this line has no correct category in the taxonomy".
  - `app/inference/business_rules.py` — the lookup plus `direction_mask`.
  - `app/inference/predictor.py` — rules run before the model; a COMPRAS
    (purchase) line can never score an ING-* (income) category.
  - `app/api/schemas.py` — `transaction_type` added to the request.
  - Verified: `VENTA DE LECHE` + VENTAS → ING-0.1 at 1.000 auto-accept;
    `VENTA DE ACTIVO FIJO` → no prediction, review_required. **Without
    `transaction_type` the old broken behaviour reproduces**, so every caller
    must pass it.

## TWO DATA BUGS FOUND LATE — both fixed, both change the numbers

These were found after `docs/RESULTS-v1.2.0.md` was written, so **every number in
that file is stale.** Re-measure before quoting anything.

**Bug 1 — contradictory training rows (fixed).** The dedup key was
`(item, description, provider, category_code)`. Because the *code* is part of the
key, a row with the same text but a DIFFERENT code produced a different key,
passed the duplicate check, and was appended next to the row it contradicts. The
model was then shown one input with two correct answers. Gold had **zero** such
contradictions before this session and **46** (96 rows) after the first
promotion. Fixed by adding a second key without the label, in both scripts 56 and
57: established gold always wins, and contradicted silver rows are logged to
`Data/gold/_contradicted_not_promoted_*.csv` (53 rows) for human adjudication.
Verified: gold now has **0** contradictions.

**Bug 2 — train/validation leakage (fixed).** Gold contains rows that are
distinct records but produce an IDENTICAL model input after `build_text()` — e.g.
36 rows carrying the exact same text for EXP-11.1. These landed on both sides of
the split, so the model was tested on strings it had memorised. Measured: **56 of
448 validation rows (12.5%) had their exact text in training.** This is
pre-existing — it affected v1.1.0 too, so **its published 0.7441 accuracy was
inflated by the same mechanism**. Fixed in `training/train_setfit.py::load_rows`,
which now collapses rows producing an identical model input (253 rows collapsed,
2,262 → 2,009 distinct inputs). Verified leakage is now **0**, no class starved
below the 2-example floor, income categories untouched.

Bug 2 also revealed that some categories were far weaker than they looked:
`ADM-2.2` 29 → 5 distinct examples, `EXP-6.3` 23 → 3, `ADM-1.7` 117 → 57. Their
apparent strength was duplicate inflation.

**Correction to a claim in RESULTS-v1.2.0.md:** the "20 of 20 income rows correct
on data the model never saw" figure is real but overstated. All 20 validation
income rows share their `item_text` and label with training rows (e.g.
`venta de leche` appears dozens of times in training). It demonstrates the model
reliably recognises a repeated phrase — which is exactly what this labelling job
needs — but it is NOT evidence of generalisation to unseen wording. Do not
present it as such to the client.

## What is in flight right now

A training run on the cleaned gold: `models/setfit_base_v120`, frozen
embeddings, followed by `scripts/58_local_inference_compare.py`. Logs in the
session scratchpad (`train_v120.log`, `compare_v120.log`). **If it did not
finish, re-run it — this is the first model trained on data that is both
contradiction-free and leakage-free, so it is the first trustworthy set of
numbers.**

Also present: `models/setfit_base_A` (frozen embeddings, 10.2 min, acc 0.6853 /
macroF1 0.6863 / top3 0.8482) — trained on contradiction-free but NOT
leakage-free data, so it is already superseded. `models/setfit_base_B` failed on
a network error (could not reach HuggingFace), not a memory error.

Three independent audit agents were launched (gold data quality, model
errors/calibration, pipeline code review). **All three died before reporting** —
two hit the account session limit, one hit a network outage. Their partial notes
flagged: a possible leakage confound (confirmed and fixed above, Bug 2), the
electricity categories being "textually inseparable", and a suggestion to check
for encoding corruption. **Re-run these audits** — the leakage lead they surfaced
turned out to be real and serious, so the remaining leads deserve the same
scrutiny.

## The open question nobody has answered yet

**Auto-accepts went DOWN after retraining on more and better data** (6,356 →
5,947 of 12,071), and validation accuracy fell 0.7441 → 0.7002 while macro-F1
rose 0.6768 → 0.6932. The leading hypothesis is that `class_weight="balanced"`
on the LogisticRegression head flattened the probability distribution, so the
model is equally accurate but less confident, and a fixed 0.80 confidence gate
therefore accepts fewer rows. **This was not yet proven.** Test it by re-fitting
the head with `class_weight=None` on the same embeddings and comparing accuracy,
macro-F1, and the confidence distribution. Note that 710 of the 834 rows that
moved to "review" kept the same label and only lost confidence — that is
calibration, not a labeling regression.

Also unresolved: whether 0.80 is simply the wrong gate for the new model. Produce
a calibration curve (bucket by predicted confidence, measure actual accuracy per
bucket) before changing any threshold.

**Important caveat now that Bug 2 is fixed:** the old auto-accept comparison was
measured against a leaky model, so part of v1.1.0's apparent confidence was
memorisation. Re-measure the auto-accept delta with the new leakage-free model
before concluding anything about `class_weight`. It is entirely possible the
"confidence regression" shrinks or disappears once both sides are honest.

Three concrete candidate causes to separate, in order of likelihood:
1. `class_weight="balanced"` flattening the probability distribution;
2. removal of duplicate rows that were inflating certain classes' priors;
3. genuine accuracy loss on frequent classes.

## Known issues to fix

1. **The dashboard is the highest priority and is outside this repo.** It must
   never present a `review_required` row as final, and it must show the
   confidence score. This caused the incident. Not started.
2. **Engine oil misclassified.** `"Item | 968042 JD Plus 50 II 15W40"` (John
   Deere 15W40 oil) went to ADM-1.6 "office supplies" at 0.814 confidence; it
   should be EXP-13.1 "machinery maintenance". 2 rows. These were the only rows
   in 12,071 where a previously-confident answer was replaced by a different
   confident answer. Note the item_text is the placeholder `"Item"` — 3.5% of all
   rows have placeholder names (`Item`, `DETALLE`, `Total`, `Fecha-Guía`,
   dashes), which is a systemic weakness worth investigating.
3. **Seven rows have no correct category.** `VENTA DE ACTIVO FIJO` (2),
   `VENTA CAMIONETA` (3), `maquinaria` (1), `OTROS INGRESOS` (1). Every ING-*
   code is operating revenue; selling a truck is not. The new `review` rules now
   route these correctly, but the client must decide the accounting treatment.
4. **Two categories cannot be trained.** `ING-0.5 VENTA DE OTROS ANIMALES` has
   zero real examples anywhere in the data; `ADM-1.9 Asesoria Legal` has one.
   Both need client confirmation that they are genuinely unused.
5. **53 contradictions were skipped during promotion** and logged to
   `Data/gold/_contradicted_not_promoted_*.csv`. Each is a real disagreement
   between established gold and an audited silver verdict. They need human
   adjudication and are currently just excluded.
6. **ONNX export not done.** The recommended model still needs
   `training/export_onnx.py --version v1.2.0` plus the PyTorch/ONNX parity gate.
7. The 596 unaudited silver rows, the 77 conflicting item names, and the ~8,000
   line items never labeled by Ollama are all still untouched — deliberately.

## Training memory note (read before running training)

On this 16 GB Mac, PyTorch's MPS ceiling is 20.13 GiB (macOS allows the GPU
11.84 GiB × PyTorch's 1.7 safety ratio). Training needs ~6.1 GiB live but the
allocator reserves ~14 GiB, so it OOMs on a 732 MiB allocation — the token
embedding gradient (250,002 × 768 × 4 bytes).

**Measured, do not re-litigate:** it is NOT other applications, NOT system
uptime, NOT swap, and NOT fixable by closing apps or rebooting — those were all
tried and the numbers were byte-identical. Lowering `--batch-size` does not help
because the failing allocation is batch-independent. Cache clearing every step
helps but cannot keep up with AdamW allocating optimizer state. Gradient
checkpointing reduces the reserve 14.34 → 13.63 GiB, still not enough.

Two configurations that DO complete: `--freeze-embeddings` (ceiling intact,
~12 min) or `PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0` (ceiling removed, ~40 min).
Always wrap long runs in `caffeinate -ims` — closing the laptop lid suspends
training (it resumes on wake, but the run stalls).

## Non-negotiable guardrails

- **Nothing is pushed anywhere**: no Supabase writes, no Cloud Run deploy, no
  `git push`. Local only.
- Never overwrite `artifacts/v1.1.0/` or `models/setfit_base/` — the deployed
  model and the comparison baseline.
- Never modify raw XML under `Data/Raw_Data/`.
- `Data/gold/_master_gold.csv` is the training source of truth; the per-category
  files in `Data/gold/` are generated views — never edit them by hand.
- **Any dedup key applied to training rows must contain every field the model
  reads** (`item_text`, `description`, `provider`). This was the original bug and
  it was reintroduced twice in one session.
- A category with <2 examples cannot be trained. It must fail loudly, never
  silently.
- Never release on aggregate accuracy alone; income-slice accuracy is a
  mandatory gate.
- Do not reset the uncommitted work in git — see `docs/ROLLBACK.md`.

## How to verify anything

```bash
.venv-backend/bin/python -m pytest tests -q          # backend tests (6 passing)
.venv-train/bin/python scripts/56_promote_silver_to_gold.py   # dry run
.venv-train/bin/python scripts/57_harvest_sales_gold.py       # dry run
.venv-train/bin/python scripts/55_contradiction_audit.py
.venv-train/bin/python scripts/50_build_gold_views.py
```

Use `.venv-train` for anything touching torch/setfit, `.venv-backend` for the
API. Every data script is dry-run by default and backs up gold before writing —
keep it that way.

## Working style expected

The user is an Applied AI/ML engineer who wants to understand the reasoning, not
just the result. Be precise with numbers and correct yourself immediately and
plainly when wrong — several confident diagnoses in the previous session turned
out to be wrong and cost real time (a needless reboot among them). Verify claims
against the actual files and artifacts rather than trusting the documentation,
including this handover. Prefer measuring over asserting.
