# Overnight comparison, 2026-09-21 — where everything is

Started 21:41 (Chile). One run at a time, in this order: A, B, C, D, E. Results land in
`results.md` / `results.json` as each model finishes. Progress: `queue.log`.

## Inputs (nothing here was changed)

| What | Where |
|---|---|
| July invoices (DTE XML, real) | `Data/Raw_Data/2026-07.zip` (also unzipped in `Data/Raw_Data/2026-07/`). The ZIP carries a `__MACOSX/` folder; ingest now skips it (`isArchiveJunk`, milk-company `c64b4e1`). |
| August invoices | **Not downloaded yet.** Only the August *ledger* sheet is here. Needed only for the morning test. |
| Accountants' labels (July + August ledger) | `Data/ledger_2026_07_08/` — `COMPRAS FORMATO 1.xlsx` (one row per document x account x cost centre; sheets JULIO, AGOSTO), `COMPRAS FORMATO 2.xlsx` (same, grouped), `Antillanca SpA - Hallazgos (…).xlsx` (a Chipax reconciliation, not labels). Original download: `~/Downloads/Fwd__LIBRO_DE_COMPRAS.zip`. |
| What the ML pipeline produced for July | the report `informe-facturas-1fb9c36e-2026-09-21.xlsx` (this folder) and, in Supabase, batch `1fb9c36e-39e4-4175-9fb0-1abede1dcca5` (337 invoices / 897 lines, written by the ML-only fallback because the AI Gateway had no credit). **Still in the live database. Do not delete until the analysis is finished.** |
| July line-level table with the accountants' category | `Data/candidates/overnight_2026_09_21/july_lines_truth.csv` (column `truth`; empty where the ledger could not be matched to a line). |
| Line-by-line comparison, ML vs ledger | `reports/july_ml_analysis/july_lines_vs_ledger.csv` |

How `truth` was made: an invoice's ledger rows give amount per account. 296 of 320 documents
have one account (every line gets it); 24 split across accounts, and for 20 of them the line
amounts add up exactly to the account amounts, which fixes the line. Four could not be solved
and have no truth. Account names match our category names except four (impuestos/comisiones,
two leasing debt accounts, arriendo otros predios), which were left out.

## The five variants (all keep the locked 843 test rows of `retrain_2026_09_16`)

| Variant | Training data | Question it answers |
|---|---|---|
| A_diet_old | old data, thinned diet | Does fixing the diet alone help? July is a fully unseen exam. |
| B_july70 | old data as-is + 70% of July suppliers | Does adding July help, without touching the diet? |
| C_july70_diet | thinned diet + same 70% of July | Diet and July together. |
| D_july70_diet_ctx | C, with 17 "mixed" suppliers capped at 40 rows | Does suppressing context-dependent suppliers help? |
| E_julyfull_diet | thinned diet + all July | The candidate for the demo. No fair July exam left. |

The diet (fixed before any July number was looked at): rows the client's own rules settle in
production are kept at 30% per class (never below 15 in a class); no supplier above 120 rows;
contrastive stage capped at 60 rows per class. The recipe otherwise equals v1.4.1
(CPU, batch 8, 2000 steps, provider-free augmentation on).

Exams: `locked843` (and its `model_facing` slice), `july_exam_fold` (130 lines from the
30% of July suppliers held out of B, C, D), `july_all` (499 lines, fair only for models that
did not train on July). Baseline v1.4.1 on the same exams is already in `results.md`.

## Code

`scripts/103_build_overnight_variants.py` (data), `scripts/104_eval_overnight.py` (scoring),
`scripts/overnight_queue.sh` (the queue). Models: `models/overnight_2026_09_21/<name>/`.
