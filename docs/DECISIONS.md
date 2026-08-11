# DECISIONS

Why things are the way they are. Append-only — supersede an entry, don't delete it.

Format: `D-NNN` | date | decision | why | who decided.

---

## D-001 — A dedup key must contain every field the model consumes

**Date:** 2026-08-11 · **Decided by:** Afaq + Claude (Opus 5)

The historical promotion script deduped gold rows on
`(normalized_item_text, category_code)`. The model's input is
`item_text | description | provider`. The key was blind to two fields that are
*inside the model's input*, so 47 genuinely distinct milk-sale training texts
(47 distinct descriptions — different volumes, prices, tanks, farms) collapsed
to a single gold row.

**Rule going forward:** the dedup key is
`(item_text, description, provider, category_code)`, normalized. If the model's
input template ever changes, this key changes with it, in the same commit.

**Why not just drop dedup:** exact duplicate records still add nothing to
contrastive learning and skew the LR head's class prior. The problem was never
that dedup existed; it was that the key was narrower than the input.

---

## D-002 — Promote audited silver with the fixed key, skipping conflicting names

**Date:** 2026-08-11 · **Decided by:** Afaq

Recovers 680 already-audited rows currently blocked from gold. Item names whose
audited verdicts contradict each other (77 names, ~248 rows, e.g.
`VACAS PREÑADAS` → ING-0.2 vs ING-0.5) are held back rather than guessed at.

**Known quality caveat, accepted:** of the 680, 611 carry only a bulk batch tag
(`2step_review` / `wave2_review`) and 69 have an individually written reason. The
bulk path was "Ollama proposed → Ollama verified with a different prompt → human
confirmed the category batch." That is genuinely fine for unambiguous classes
and thinner for ambiguous ones. Accepted as an improvement over the status quo,
not as certainty.

---

## D-003 — Harvest sales categories directly from raw VENTAS, bypassing silver

**Date:** 2026-08-11 · **Decided by:** Afaq

For `VENTA DE LECHE`, `VENTA DE VACAS`, `VENTAS TERNEROS`, `VENTA DE TERNERAS`,
`VENTA DE VAQUILLAS` the item name *states the category* and the document
direction is unambiguously a sale (the client's own outgoing invoices).

These rows do not need an Ollama pass or an audit queue — the label is certain
by inspection. This is the highest-confidence data in the project. It is also
the only way to fix `ING-0.3` and `ING-0.4`: the dedup fix alone does not help
them, because calves and heifers were never routed into the silver audit at all
(`TERNERO` has 1 ledger row with a blank verdict, `VAQUILLA` has zero).

---

## D-004 — Hold out ~20% of each harvested sales class for validation

**Date:** 2026-08-11 · **Decided by:** Afaq

If all 47 milk rows go into training, "the model classifies milk correctly"
proves only that it memorized them. A held-out slice makes the number mean
something. Applies to any class where we harvest a large block of near-identical
rows.

---

## D-005 — Synthetic examples only to clear the 2-example training floor

**Date:** 2026-08-11 · **Decided by:** Afaq

Where a category's name is literally the item name and real examples number
fewer than 2, generate synthetic rows up to 3 so the class can be trained at all.

Constraints on synthetic rows:
- `source` must start with `synthetic_` so they are always separable;
- no folio, no row_id, no source_file — they are training data, never invoices;
- they must never appear in a validation split (a synthetic row cannot validate
  anything);
- they are a floor-clearing device, not a substitute for real data.

---

## D-006 — Category codes as labels lose nothing

**Date:** 2026-08-11 · **Decided by:** Claude (Opus 5), confirmed by Afaq

Concern raised: does using `ING-0.1` instead of `VENTA DE LECHE` as the label
throw away semantic signal?

No. Verified against the artifact: the head is `LogisticRegression` with
`classes_` of dtype str and `coef_` of shape (66, 768). Neither SetFit stage
tokenizes or embeds label text — the contrastive stage uses labels only to decide
"same class / different class", and the head maps embeddings to column indices.
Labels could be `A`, `B`, `C` with identical results.

**Corollary:** a zero-example class cannot be rescued by naming it well. The
architecture that *would* match an item to a label by name (embed both, take
cosine similarity) is a zero-shot bi-encoder, which SetFit deliberately replaces.

---

## D-007 — `class_weight="balanced"` on the LR head

**Date:** 2026-08-11 · **Decided by:** Afaq + Claude

v1.1.0 used `sampling_strategy="oversampling"` for contrastive pairs but left the
head at `class_weight=None`. Rare classes were balanced during body fine-tuning
and then disadvantaged again at the head. To be measured against the current
head, not assumed better.

---

## D-008 — Export gate: refuse if any trained class has zero validation rows

**Date:** 2026-08-11 · **Decided by:** Afaq + Claude

v1.1.0 reported 0.7441 validation accuracy over 340 rows containing **zero**
income examples, and 5 of 66 trained classes had no validation support at all.
The metrics were real and meaningless for the client's core revenue lines.

A single gate would have caught the entire incident before release.

---

## D-009 — Local only this phase

**Date:** 2026-08-11 · **Decided by:** Afaq

No Supabase writes, no deploys, no git push. The v1.1.0 prediction run is
preserved locally at
`Temp_Inference/snapshots/normalized_before_company_item_split/invoice_items.json`
and is the before/after baseline. See CONSTRAINTS.md.

---

## D-012 — Established gold wins; a promotion may never contradict it

**Date:** 2026-08-11 · **Decided by:** Claude (Opus 5), flagged to Afaq

The dedup key `(item, description, provider, category_code)` prevents exact
duplicates but NOT contradictions: because the code is part of the key, a row
with the same text and a *different* code produces a different key, passes the
check, and is appended beside the row it contradicts. The model is then shown one
input with two correct answers — unlearnable, and it teaches uncertainty in that
region of embedding space.

Measured: gold had **0** contradictions before this session and **46** (96 rows)
after the first promotion run. All 46 were the same shape — a bulk-approved
Ollama row contradicting a client-supplied example or a file audit.

**Rule:** a second key, `(item, description, provider)` without the label, is
checked before promotion. If gold already labels that exact input differently,
the incoming row is rejected and logged to
`Data/gold/_contradicted_not_promoted_<stamp>.csv`. Established gold wins —
client rules and file audits outrank bulk-approved silver. The 53 rejected rows
are real disagreements and need human adjudication; they are excluded, not
resolved.

---

## D-013 — Deduplicate on the built model input, not on the raw fields

**Date:** 2026-08-11 · **Decided by:** Claude (Opus 5), flagged to Afaq

Gold legitimately records the same business fact many times — 36 rows carry the
identical text `"administracion del servicio | cooperativa rural elect r buen"`
for EXP-11.1. After `build_text()` these are the *same string*, so they are not
extra information. Keeping them caused two problems:

1. **Leakage.** Copies landed on both sides of the train/val split. Measured:
   **56 of 448 validation rows (12.5%)** had their exact text in training. This
   is pre-existing and affected v1.1.0 too — **its published 0.7441 accuracy was
   inflated by this.**
2. **Skewed priors.** The head saw ADM-1.7 as 117 examples when it has 57
   distinct ones; ADM-2.2 as 29 when it has 5; EXP-6.3 as 23 when it has 3.

**Rule:** `load_rows()` collapses rows producing an identical `(built_text,
label)`. Gold keeps every row for provenance; the model never sees a duplicate.

**This is NOT a repeat of BUG-001.** That bug deduped on `item_text` alone,
collapsing 47 genuinely different milk rows into 1 and deleting a category. This
dedups on the exact string the model consumes, so it can only remove rows
carrying zero additional signal. Verified: 253 rows collapsed, leakage 0, no
class starved below the 2-example floor, income categories untouched.

**Consequence for reporting:** the "20 of 20 income rows correct" result is real
but must not be described as generalisation. All 20 share their `item_text` and
label with training rows. It shows the model reliably recognises a repeated
phrase — which is what this labelling job needs — not that it handles unseen
wording.

---

## D-014 — Deterministic business rules with an explicit "no category exists" action

**Date:** 2026-08-11 · **Decided by:** Afaq (asked for pattern matching), designed by Claude

`app/data/business_rules.csv` + `app/inference/business_rules.py`, applied before
the model. Two actions:

- `assign` — a canonical sales phrase whose name states its own category
  (`VENTA DE LECHE` → ING-0.1). Score 1.0, model skipped. Asking a probabilistic
  classifier to rediscover a known fact spends uncertainty for nothing.
- `review` — the line has **no correct category in the taxonomy**. Asset
  disposals (`VENTA CAMIONETA`, `VENTA DE ACTIVO FIJO`, `maquinaria`) are not
  operating revenue, and every `ING-*` code is. The rule returns *no prediction*
  and forces review.

The `review` action is the important half: it encodes "we know we do not know",
which is the one thing the model cannot express about a missing category. Without
it the model returned the nearest neighbour — measured at
`VENTA DE ACTIVO FIJO → ING-0.1 milk sales @ 0.841, auto-accepted`. That is
BUG-001 inverted.

**Direction masking**, same module: a COMPRAS (purchase) line can never score an
`ING-*` (income) category; probabilities are zeroed and renormalised. This
removes by construction the 12 purchase-lines-predicted-as-income.

The reverse mask (VENTAS cannot be an expense) is deliberately NOT applied —
forcing asset disposals into an income category is precisely the failure above.

**Requires `transaction_type` on the request.** Verified: without it, the old
broken behaviour reproduces exactly. Every caller must pass it.

---

## D-011 — Token embeddings frozen for the constrained-memory run only

**Date:** 2026-08-11 · **Decided by:** Claude (Opus 5), flagged to Afaq

Training OOM'd on MPS three times. Diagnosis: the failing allocation was always
exactly **732.43 MiB**, which is `vocab_size × hidden × 4 bytes`
= 250,002 × 768 × 4 = 768,006,144 bytes — the gradient buffer for the token
embedding matrix. It is **batch-independent**, which is why dropping
`--batch-size` from 8 to 4 changed nothing.

**CORRECTED 2026-08-11.** My first two diagnoses were wrong and are recorded
here so nobody repeats them:

- ~~"other apps are holding 14.34 GiB, close them"~~ — closing Chrome changed
  nothing.
- ~~"36 days of uptime filled swap, reboot"~~ — the user rebooted; a fresh boot
  with **0 MB swap used** produced the byte-identical error.

The actual mechanism, measured rather than inferred:

```
macOS recommended_max_memory()      = 11.84 GiB   (75% of 16 GiB physical)
PyTorch default watermark ratio     x  1.7
max allowed                         = 20.13 GiB   <- matches the error exactly
```

And `other allocations` is **PyTorch's own caching allocator pool**, not other
processes. Demonstrated directly:

```
allocate a 200 MiB tensor  -> pytorch tensors 200 MiB, driver holds 1024 MiB
delete that tensor         -> pytorch tensors   0 MiB, driver holds 1024 MiB
torch.mps.empty_cache()    -> pytorch tensors   0 MiB, driver holds    0.5 MiB
```

PyTorch requests memory from Metal in large blocks and retains them for reuse.
Over a training run that pool reaches ~14.34 GiB of held-but-idle memory. The
OOM is therefore `5.35 (live) + 14.34 (cached) + 0.73 (next block) = 20.42 >
20.13` — the process starves inside its own budget while sitting on 14 GiB it is
not using.

This explains every observation: the number is byte-identical across system
states because it is a property of *this workload*, and freeing system RAM
cannot affect it because system RAM was never in it.

**Working fix:** `PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0` raises the ceiling. Safe
here because the job's true requirement is bounded (~6.1 GiB) and known. The
more principled fix, if this recurs, is periodic `torch.mps.empty_cache()`
during training to stop the pool growing unbounded.

`--freeze-embeddings` (default on) skips that gradient. Defensible on its own
terms: contrastive fine-tuning on ~1,850 short domain texts has no business
rewriting a 250k-token multilingual vocabulary, and the encoder blocks above it
still train normally.

**But it is not what v1.1.0 did.** The v1.1.0 comparison is only exactly
like-for-like with embeddings trainable. After a reboot reclaims swap, retrain
with `--no-freeze-embeddings` at `--batch-size 8` and compare the two.

Rejected alternatives:
- lower `--batch-size` — does not touch a batch-independent allocation;
- lower `max_seq_length` to 48 — truncates 6.1% of gold rows (p99 = 62 tokens),
  and the truncated tail is exactly the long milk descriptions we just recovered;
- `PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0` — removes the safety ceiling on a
  machine already 8 GB into swap; risks a hard system hang.

---

## D-012 — Full embeddings retained; fixed batch shapes solve the MPS growth

**Date:** 2026-08-11 · **Decided by:** Codex independent recovery

D-011's frozen-embedding recommendation is superseded for release candidates.
Controlled local smoke runs showed that dynamic sequence padding grew MPS driver
memory from 5.05 to 14.41 GiB in 12 steps even with Adafactor. Padding every
batch to the fixed 64-token model length made memory plateau: 4.42 GiB with
Adafactor/batch 4 and 6.60 GiB with standard AdamW/batch 8, each through 20
steps. All 278,043,648 encoder parameters were trainable and tracked token
embeddings changed.

The recovery configuration therefore uses full encoder training, AdamW, batch
8, fixed 64-token padding, and the normal bounded MPS watermark. The trainer
refuses an unbounded `PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0`. Evidence is saved
under `reports/recovery_v1_2_0/`; full reasoning is in
`docs/RECOVERY_V1_2_0.md`.

---

## D-010 — Document type is out of scope; direction comes from the folder

**Date:** 2026-08-11 · **Decided by:** Afaq

Raw data contains credit notes, exempt invoices, settlement invoices and debit
notes. Classifying by document type is not this project's job — the
COMPRAS/VENTAS folder already gives direction, and Supabase already stores it.
Noted here only so a future session does not re-derive it as a "gap".
