# RESULTS — v1.2.0, and whether we can report to the boss

**Date:** 2026-08-11 · **Verdict: the ML fix is done and proven. Do NOT show the
client anything yet — the thing that actually caused the humiliation is still
unfixed.** See section 6.

Nothing deployed. Nothing written to Supabase. Nothing pushed.

---

## 1. Recommended model

```
models/setfit_base_v1_2_0_clean      <- USE THIS ONE
```

Two candidates were trained. They score the same on paper, but on the real data
the fully-trained one is **safer**, so it wins:

```
run                  val_n     acc  macroF1    top3   mins   income slice
v1.1.0 deployed        340  0.7441   0.6768  0.8765      ?   0 rows (untestable)
v1.2.0 frozen-emb      457  0.7024   0.6919  0.8775   11.5   20/20 correct
v1.2.0 full-train      457  0.7002   0.6932  0.8687   40.1   20/20 correct
```

Aggregate accuracy fell, but **the two validation sets are different** (340 vs
457 rows) and only the new one contains income rows, so those numbers are not
comparable. Macro-F1 — which weights every category equally — improved.

The decider was behaviour on the 12,071 real rows, not the score table:

```
                                     frozen-emb    full-train
VENTA DE ACTIVO FIJO            wrong, auto-accept   -> review    <- decisive
                                    as milk @0.841       @0.388
purchases auto-accepted as income          0             0
sales auto-accepted as expenses            0             0
purchases predicted income (all review)   22            12
auto-accepts lost                       -471          -409
```

The frozen model confidently called a truck sale "milk revenue". The fully
trained one sends it to review. That is worth 40 minutes of training.

## 2. Training data fixed

```
gold rows                 1,733 -> 2,309
trainable categories         66 -> 69
categories with >=15 gold    43 -> 48
excluded (<2 examples)        5 -> 1

ING-0.1 milk        1 -> 48    train 38 / val 10
ING-0.2 cows        3 -> 15    train 13 / val  2
ING-0.3 heifers     1 ->  3    train  3 / val  0
ING-0.4 calves      2 -> 46    train 38 / val  8
ING-0.5 other       0 ->  0    NOT TRAINED — no real examples exist
ING-0.6 firewood    1 ->  3    train  3 / val  0
```

Composition: +519 re-promoted audited silver (dedup key fixed), +59 harvested
from raw VENTAS, +4 synthetic floor rows, −6 quarantined purchase-rows-as-sales.

## 3. The incident is fixed

```
item                    n   v1.1.0            v1.2.0        old t1   new t1   auto
VENTAS TERNEROS        50   staff costs    -> calf sales    0.5075   0.9777   50/50
VENTA DE LECHE         47   road maint.    -> milk sales    0.1545   0.9741   47/47
VENTA DE VACAS         18   road maint.    -> cow sales     0.3127   0.8554   12/18
VENTA DE VAQUILLAS      2   road maint.    -> heifer sales  0.2519   0.7830    0/2
VENTA DE TERNERAS       1   road maint.    -> calf sales     0.3284   0.5346    0/1

sales rows correctly identified as income:  0 of 125  ->  119 of 125
```

Independently verified on 20 sales rows the model never saw in training:
**20 of 20 correct.** v1.1.0 could not be tested on income at all — its
validation set had zero income rows, which is why nobody caught this pre-release.

Safety invariants on all 12,071 rows:

```
VENTAS rows auto-accepted as an expense   : 0
COMPRAS rows auto-accepted as income      : 0
```

## 4. Known issues — read before talking to anyone

**4.1 One new confident error.** Engine oil is now filed as office supplies:

```
"Item | 968042 JD Plus 50 II 15W40"   (John Deere 15W40 engine oil)
  was  EXP-13.1 Mantencion Maquinaria @ 0.896   <- correct
  now  ADM-1.6  Utiles y gastos oficina @ 0.814 <- wrong
```

2 rows. These are the **only** two rows in the entire dataset where a previously
confident answer was replaced by a different confident answer, and this one is
worse. Everything else that gained confidence was previously "don't know".

**4.2 Seven rows have no correct category.** `VENTA DE ACTIVO FIJO` (2),
`VENTA CAMIONETA` (3), `maquinaria` (1), `OTROS INGRESOS` (1). The taxonomy has
no category for selling a truck — all `ING-*` categories are operating revenue.
The model correctly sends them all to review now, but **the client must decide
how asset disposals are booked.** This is a taxonomy gap, not a model bug, and
retraining will never fix it.

**4.3 409 fewer auto-accepts** (6,356 → 5,947), i.e. more manual review. But of
the 834 rows that moved to review, **710 kept the same label and only lost
confidence** — a side effect of weighting rare categories equally. Only 124
actually changed answer.

**4.4 Purchases predicted as income: 9 → 12.** All review-required, none
auto-accepted. Contained, but it is the original bug mirrored. A direction rule
(a purchase can never be income) would take it to zero.

**4.5 Two categories still untrained.** `ING-0.5 VENTA DE OTROS ANIMALES` has
zero real examples anywhere in the data. `ADM-1.9 Asesoria Legal` has one. Both
need client confirmation that they are genuinely unused.

## 5. Training environment — resolved

Training kept failing with an MPS out-of-memory error. Three wrong diagnoses were
made before the right one (all recorded in DECISIONS.md D-011 so they are not
repeated). Final answer:

- The job genuinely needs more memory than PyTorch's default ceiling allows on a
  16 GB Mac. It is not a leak, not other apps, and not system uptime.
- Clearing PyTorch's cache every step **does** release memory but cannot keep up
  with AdamW allocating optimizer state — measured: 4.98 → 6.44 → 7.13 → 8.59 →
  10.00 → 10.72 GiB over six steps, then OOM.
- Two configurations that do complete: freeze the token embeddings (11.5 min,
  ceiling intact), or raise the ceiling with
  `PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0` (40 min, ceiling removed).
- The recommended model used the raised ceiling. **It did not destabilise the
  machine** — an earlier run appeared to be killed, but that was the laptop lid
  closing and sleeping; the process resumed on wake and finished normally.
- All memory is released the moment training exits. Nothing persists on the Mac,
  and no environment variable was written to any shell profile.

## 6. Are we ready to report to the boss?

**The ML work: yes.** The milk misclassification is fixed, proven on held-out
data, with a validation gate that would have caught it before release.

**Showing the client: no, not yet.** The model was never the whole story. Every
one of the 125 sales rows was correctly flagged "needs review" with 15%
confidence — the system was honestly saying "I don't know". The dashboard
displayed those guesses as final answers and hid the confidence score. **That
part is still unfixed**, and it is what actually caused the incident.

If the dashboard ships unchanged, the same humiliation happens again on the next
uncertain category — and there are still 5,947 auto-accepted and ~6,100
review-required rows behind it.

Safe to tell the boss:

1. Root cause found and fixed: a de-duplication bug deleted 46 of 47 milk
   training examples, and the trainer then silently dropped the category.
2. Milk is now identified correctly at 97% confidence, verified on data the
   model never trained on.
3. A release gate now blocks any model where a category is untested.
4. Two things must happen before the client sees anything: the dashboard must
   show confidence and must never present a "needs review" row as final; and the
   client must tell us how to book asset sales.

## 7. Still to do

1. **Dashboard: never show a review-required row as final; always show
   confidence.** Highest priority, not started, outside this repo.
2. Direction rule: purchases cannot be income, sales cannot be expenses.
3. Exact-name lookup for canonical sales phrases + the 7 homeless rows.
4. Investigate the engine-oil regression (4.1).
5. Export the ONNX package as v1.2.0 with a parity check.
6. Client decisions: asset disposals, livestock purchases, `ING-0.5`.

## 8. Files

```
models/setfit_base_v1_2_0_clean/        RECOMMENDED model + metrics
models/setfit_base_v1_2_0/              frozen-embedding variant
Data/stale/inference_v1.1.0_baseline_*/ preserved v1.1.0 predictions
Data/stale/inference_compare_20260811_122609/   full 12,071-row before/after
Data/gold/_master_gold.backup_*.csv     two timestamped backups
Data/gold/_quarantined_purchase_as_sale_*.csv
```

`artifacts/v1.1.0/` and `models/setfit_base/` are untouched. Backend tests pass.
