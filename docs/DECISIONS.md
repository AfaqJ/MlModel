# DECISIONS

Why things are the way they are.

**A dead entry is deleted, not left wearing a marker.** Fully dead means expired
or superseded AND cited nowhere in `CLAUDE.md`, `docs/` or code. An entry whose
principle is still cited stays and carries its marker instead. Git history is the
archive — check inbound references before deleting, and fix any that dangle.

Format: `D-NNN` | date | decision | why | who decided.
**Grep for existing `D-` IDs before adding one.** This file had a duplicate
`D-012` for two days; that is the failure mode to avoid.

Entries are not in strict numeric or date order. Use the ID, not the position.

---

## D-001 — A dedup key must contain every field the model consumes

> **Refined by D-013.** The principle stands and is the most important rule in
> the project. The specific tuple below is out of date: the input template now
> includes `transaction_type`, and dedup happens on the *built* string rather
> than a field tuple.

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

## D-015 — Full embeddings retained; fixed batch shapes solve the MPS growth

> Renumbered 2026-08-13: this entry was a second `D-012`, colliding with
> "Established gold wins". Content unchanged.

**Date:** 2026-08-11 · **Decided by:** Codex independent recovery

An earlier recommendation to freeze the token embeddings (deleted 2026-08-19 as
a dead entry; see git history) is superseded for release candidates.
Controlled local smoke runs showed that dynamic sequence padding grew MPS driver
memory from 5.05 to 14.41 GiB in 12 steps even with Adafactor. Padding every
batch to the fixed 64-token model length made memory plateau: 4.42 GiB with
Adafactor/batch 4 and 6.60 GiB with standard AdamW/batch 8, each through 20
steps. All 278,043,648 encoder parameters were trainable and tracked token
embeddings changed.

The recovery configuration therefore uses full encoder training, AdamW, batch
8, fixed 64-token padding, and the normal bounded MPS watermark. The trainer
refuses an unbounded `PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0`. Evidence is saved
under `reports/recovery_v1_2_0/`. (The original write-up,
`docs/RECOVERY_V1_2_0.md`, was deleted; the substance is in D-016 to D-024 and
`STATE.md`.)

---

## D-010 — Document type is out of scope

> **Narrowed by [D-072] on 2026-09-10.** The half about document type still
> holds. The half about the folder does not: direction is now read from the RUTs
> inside each document, and the folder is only a fallback.

**Date:** 2026-08-11 · **Decided by:** Afaq

Raw data contains credit notes, exempt invoices, settlement invoices and debit
notes. Classifying by document type is not this project's job — direction is
enough, and Supabase already stores it. Noted here only so a future session does
not re-derive it as a "gap".

---

## D-016 — Business rules are sales-only, narrowed 95 → 28

> **Still true of the runtime; the payload tag has drifted (checked 2026-08-19).**
> `app/data/business_rules.csv` holds exactly **28 rules, all `ING-*`, all
> `assign`** — this entry is accurate about what fires at inference. But
> `prediction_source = "business_rule"` in the Supabase payload was later reused
> by correction scripts as a generic "a deterministic rule decided this" tag:
> of its **928** rows only **124 are `ING-*`**, the rest being EXP- 479, ADM- 190,
> AF-1 113, AF-2 22. Do not read the payload tag as "one of the 28 sales rules".
> Folded into D-042's cleanup.

**Date:** 2026-08-12 · **Decided by:** Afaq · **Model:** Claude (Opus 5)

`scripts/64_build_taxonomy_rules.py` now emits `ING-*` leaves only and rejects
expense-side aliases. The two COMPRAS rows were dropped from
`app/data/taxonomy_aliases.csv` and `app/data/business_rules.csv` was
regenerated as version `2026.08.12-v3`.

**Why:** the client controls the wording on their own sales invoices; they do
not control their suppliers'. An exact-phrase rule is only safe where the phrase
is authored by the party we have an agreement with.

**What it prevented:** 15 of the expense keys were single common words —
`BOLOS`, `GAS`, `BENCINA` — which silently pre-empted questions still open with
the client. A deterministic rule that fires before the model is invisible in
accuracy metrics; it just quietly makes the answer.

---

## D-017 — Deploy INT8, not FP32

**Date:** 2026-08-12 · **Decided by:** Afaq · **Model:** Claude (Opus 5)

`artifacts/v1.3.3-int8` (284 MB) deploys. `artifacts/v1.3.3` (FP32, 1.1 GB) is
kept as the parity reference only.

**Why:** FP32 peaks at 1.92 GiB and is **OOM-killed** in the 2 GiB free-tier
box. This is not a preference; FP32 does not run.

**What it costs, measured:** cosine 0.99005, top-1 disagreement 6.41%, decision
disagreement 4.81% (15/312), accuracy 0.7532 → 0.7468. Of the 15 flips, **13 are
auto-accept → review (safe) and 2 are review → auto-accept, both correct. Zero
new false positives.**

**Guardrail, stated precisely.** Both ceilings are explicit flags on
`training/export_recovery_onnx.py`, defaulted tight —
`--allow-top1-disagreement` 0.03 and `--allow-threshold-decision-disagreement`
0.0. **The shipped v1.3.3-int8 build did not meet those defaults and was
released by raising them explicitly to 0.07 and 0.05.** The model card records
both the actual and the allowed value, so the override is on the record rather
than hidden:

| | actual | allowed for this build | flag default |
|---|---|---|---|
| top-1 disagreement | 0.0641 | 0.07 | 0.03 |
| threshold-decision disagreement | 0.04808 | 0.05 | 0.0 |

That is the intended mechanism — INT8 can never be substituted *silently*, but
it can be substituted *deliberately*, and this build was. Re-measure on every
retrain: the flip count is a property of the specific weights and worsened from
v1.3.1 (12/308) to v1.3.3 (15/312). If it keeps rising, the defaults are telling
you something.

---

## D-018 — Weak-class guard kept

**Date:** 2026-08-12 · **Decided by:** Afaq (reversing his own removal request)

**Why:** removing it would release 193 rows, of which 23 are wrong — fizzy
drinks and blowtorches → `EXP-11.5` (Gas), farm names → `EXP-6.3` (Cal). That is
exactly the "soda/fittings → natural gas: 23 → 0" family the v1.3.2 work fixed.

**Why the stated reason for removal did not hold:** the concern was drift, but
the weak-class list is recomputed from the split on every export, so it cannot
drift away from the data. Afaq reversed the request after seeing the numbers.

---

## D-019 — Familiarity gate kept at k=10 / agreement 0.4

> **Superseded by D-096** (2026-09-16): v1.4.0 ships k=5 / 0.40, re-measured
> on its own weights. The gate itself is unchanged.

**Date:** 2026-08-12 · **Decided by:** Afaq

**Why:** on the raw replay it caught 163 rows that had *all* cleared the
0.75/0.50 thresholds. Confidence measures how sharply the head separated the
classes it knows; it cannot measure whether the input resembles the training
data at all. The kNN gate answers the second question, and only ever downgrades.

---

## D-020 — Cloud Run concurrency 4 → 1, timeout 300 → 600 s

**Date:** 2026-08-12 · **Decided by:** Claude (Opus 5), confirmed by Afaq

**Why:** one vCPU cannot serve two CPU-bound requests. Concurrency 4 meant four
requests time-slicing one core, so every one of them got slower. Scale
horizontally via `maxScale 20` instead.

Everything else unchanged: 1 CPU / 2 GiB / `min-instances 0` / startup-cpu-boost
/ public IAM. `min-instances` stays unset — scale-to-zero is what holds the
service inside the free allowance.

---

## D-021 — Fix the data and the training, never the threshold

**Date:** 2026-08-12 · **Decided by:** Afaq

The v1.3.2 round began with ≥171 of 1,570 auto-accepts (10.9%) semantically
wrong while sitting *above* 0.75. Raising the threshold was rejected. **It was
never changed.**

**Why:** raising it would have hidden the confident errors rather than removing
them, and would have pushed correct rows into review at the same time. Coverage
was raised by correcting evidence instead.

---

## D-022 — Provider dropout in training, not provider removal

**Date:** 2026-08-12 · **Decided by:** Afaq

**Why:** the encoder had learned `RENDIC → ADM-1.6` from 21 gold rows, eight of
them supermarket cleaning products, and was applying it to every RENDIC food
line. But provider carries real signal (COPEC → fuel, veterinary suppliers →
animal health). Only the *reliance* needed breaking, so the fix is dropout
during training.

**Rejected:** removing the provider from the model input entirely (throws away
real signal), and a runtime ablation gate (adds a second inference pass and a
guard whose behaviour is hard to reason about).

---

## D-023 — Relabel quarantined rows instead of dropping them

**Date:** 2026-08-12 · **Decided by:** Afaq

> "instead of quarantining in the future we should assign correct label so we
> don't lose gold data"

Corrupted-folder rows are re-labelled wherever resolvable, and left quarantined
only where genuinely unresolvable. Rows the client had filed themselves are no
longer discarded on auditor judgment.

---

## D-024 — No hardcoded Spanish word gates in the runtime

**Date:** 2026-08-12 · **Decided by:** Afaq

Twelve hardcoded Spanish gates had been added to `app/inference/`. Afaq ordered
them removed. Recorded here as the most important correction of that round.

**Why:** a word list in the runtime is untestable, invisible to every accuracy
metric, and silently diverges from the data it was meant to patch. If a term is
being classified wrongly, the evidence is wrong — fix the gold data or the
training, where the fix is measurable. A regression test now fails if batch
vocabulary is reintroduced.

---

## D-025 — SetFit over frozen-encoder + LR, on `paraphrase-multilingual-mpnet-base-v2`

**Date:** 2026-07-05 · **Decided by:** Afaq + Claude
*Backfilled 2026-08-13 from the deleted `MLMODEL.md`, which was the only place
this reasoning lived.*

**Architecture:** SetFit — contrastive fine-tuning of the sentence transformer
itself, then a LogisticRegression head trained on the fine-tuned embeddings
(both happen inside `trainer.train()`; the head is not a separate manual step).

**Rejected — frozen encoder + LR.** With 20–50 examples per class across ~70
classes, a generic embedding space does not carry enough signal for logistic
regression to draw that many reliable boundaries, especially between
semantically adjacent categories (several `EXP` subcategories are all farm
supplies). SetFit's contrastive step reshapes the space around *these*
categories first, which makes the head's job tractable.

**This exact decision has drifted once before.** A handover prompt described
EmbeddingGemma-300m ONNX + frozen LogisticRegression, sized for a Vercel
serverless budget that no longer applied. It was traced to hallucination drift
across sessions and corrected back after re-reading the gold dataset. Any future
document proposing a frozen encoder is wrong; correct it back to this entry.

**Base model:** `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`,
278M params, 50+ languages — the model used for Spanish/multilingual experiments
in the original SetFit paper. It was pretrained on paraphrase detection, which is
a strong prior for "these mean the same thing" — exactly what SetFit builds on.

**Rejected alternatives:** `BAAI/bge-m3` (560M, ~1 GB, built for long documents
and hybrid retrieval — overkill for short invoice text) and
`paraphrase-multilingual-MiniLM-L12-v2` (~85 MB, lower quality ceiling).

---

## D-026 — Google Cloud Run, not Vercel/Lambda/Fargate/Render

**Date:** 2026-07-05 · **Decided by:** Afaq + Claude
*Backfilled 2026-08-13 from the deleted `MLMODEL.md` and `blueprint.md`.*

FastAPI + uvicorn on Cloud Run, 2 GiB / 1 vCPU, scale-to-zero. Frontend stays on
Vercel; only the backend was rejected from it.

**Rejected:**
- **Vercel for the backend** — 800 s function timeout against a batch job
  measured in thousands of seconds. A hard incompatibility, not a tuning issue.
- **AWS Lambda** — 15-minute hard timeout. Same class of problem.
- **Hosted model APIs (Roboflow etc.)** — real-time single-item inference. The
  backend calling them would still make ~10,000 calls and time out itself, plus
  per-call cost unsuited to a weekly batch.
- **AWS ECS Fargate** — comparable capability, ~12 setup steps vs ~5.
- **Render** — simplest setup but ~$25/month flat, no scale-to-zero.
- **Railway** — ~$60/month, no scale-to-zero.
- **Fly.io** — genuinely viable (~$2.32/month with scale-to-zero), no clear
  advantage over Cloud Run.

**Also decided:** batching is app-managed — the app splits line items into
chunks and calls `/predict-batch`, keeping the ML service stateless. Cloud Run
*Jobs* stay a V2 option if batches grow much larger or users need
fire-and-forget processing.

---

## D-027 — Project context lives in the repo, in four files, and stale docs are deleted

**Date:** 2026-08-13 · **Decided by:** Afaq · **Model:** Claude (Opus 5)

Context is `CLAUDE.md` at the repo root plus `docs/STATE.md`,
`docs/DECISIONS.md`, `docs/ARCHITECTURE.md`, with `AGENTS.md` as a one-line
pointer to `CLAUDE.md` so Codex loads the same context. Maintained by the
global `project-context` skill.

**Why:** 15 documents across 4 locations, several asserting they were the source
of truth, none loading automatically. `MLMODEL.md` said "do not drift" and
"deployment not yet executed" five weeks after the deploy.

**Rules that came out of it:**

- **One front door.** Only `CLAUDE.md` may say "start here." Any other doc
  claiming to be the source of truth is a bug.
- **One living `STATE.md`,** rewritten in place — never `HANDOVER_v1`, `_v2`,
  `_v3`. Versioned handovers are how history turns into sprawl.
- **Last 5 sessions only.** Anything older that still matters must already be a
  `D-NNN`. STATE is short-term memory; DECISIONS is long-term.
- **Delete superseded docs and dead decisions; do not archive them.** Git
  history is the archive. Fold load-bearing facts into the surviving doc first,
  then delete and fix every reference. This covers `D-NNN` entries: one that is
  expired or superseded **and** cited nowhere in `CLAUDE.md`, `docs/` or code is
  deleted. One whose principle is still cited stays and carries its marker.
  D-009 and D-011 were deleted on that test 2026-08-19; D-001 and D-034 stayed,
  because both are cited. (`DECISIONS.md` was append-only until then; Afaq
  removed that rule — a log nobody prunes is one nobody reads.)
- **Memory never duplicates the repo.** `~/.claude/.../memory/` is only for
  things the repo cannot hold. A fact stored twice rots in one copy.
- **Audit docs by content, not filename.** The files calling themselves context
  docs were the ones that got checked; `guides/` and `reports/*.md` were not,
  and both were wrong.

**Rejected:** an `archive/` folder (sprawl that has been moved rather than
removed), and keeping handovers in `~/.claude/handoffs/` (does not travel with
the repo, invisible in a diff, invisible to Codex).

## D-028 — Three new categories are assigned by rule, not predicted by the model

> **Narrowed by D-095** (2026-09-15): v1.4.0 trains every category that has
> gold rows, so `AF-1.1`, `AF-2.1`, `ING-0.7` and `ADM-2.3` are predictable now.
> Rule assignment stays in front of the model. `ADM-3.1`, `EXP-15.7` and
> `EXP-15.8` have no gold rows and remain rule-only.

**Date:** 2026-08-14 · **Decided by:** Afaq · **Model:** Claude Opus 5

The client created `AF-1.1 Compras de Animales`, `AF-2.1 Compras de Activo Fijo`
and `ING-0.7 Ventas de Activo Fijo`. All three exist in the live `categories`
table (74 rows) and carry data, but **the deployed model cannot emit them** — it
still has the original 71 output classes. Rows land in them by deterministic rule
only, `prediction_source = business_rule`.

> **Correction 2026-08-17 — two facts above are wrong; the decision stands.**
> (a) The deployed model has **67** output classes, not 71 — verified against
> `artifacts/v1.3.3-int8/labels.json` → `classifier_classes` and
> `model_card.json` → `trained_classes`. The "71" was arithmetic on the category
> table (74 − 3), never measured. (b) The client created `AF-1.1` and `ING-0.7`
> only. **`AF-2.1` was ours** — naming the sale side alone left trucks,
> generators and barn contracts with nowhere to go, so we added the purchase
> side and informed the client rather than asking. See
> `docs/CLIENT_CONVENTIONS.md` §4.

**Why:** the data had to be correct on the dashboard now; retraining is a
separate, later job. A category the model cannot predict is still a valid label
when a rule assigns it.

**The code prefix is load-bearing, despite the client saying codes are
meaningless to them.** `app/inference/business_rules.py::direction_mask` filters
on the literal string `"ING-"`: anything on a VENTAS invoice must start with
`ING-`, anything on a COMPRAS invoice must not. That is why asset *sales* are
`ING-0.7` and not an `AF-` code. Renaming these codes would silently break
direction masking.

**Rejected:** waiting for a retrain before creating the categories — it would
have left CLP 981M mislabelled on a live dashboard.

## D-029 — The petrol farm-vs-travel split is a rule at inference, never gold

**Date:** 2026-08-14 · **Decided by:** Afaq · **Model:** Claude Opus 5

Petrol is farm fuel or vehicle travel depending on the `<Transporte><Patente>`
field of the DTE: a plate means travel, the word "bidón" means farm. The model
input is `[direction] | item_text | description | provider` and **does not carry
the plate**. Two invoices from the same station, one jerrycan and one fill-up,
are byte-identical to the model but need opposite labels.

Correct labels were still written into gold at Afaq's explicit instruction — the
dashboard had to be right — but the contradictory pairs carry
`verify_flag=conflict` so a future retrain sees them.

**Why:** without the flag, D-013's dedup on the built input string would collide
those pairs and silently drop one. That is the exact mechanism that destroyed the
47 milk-sale rows.

**Rejected:** encoding the split by supplier. Two suppliers are genuinely mixed —
the co-op 47/48 and Paola 11/56 — so no supplier-level rule can express it.

## D-030 — Client authority outranks row volume when labels disagree

**Date:** 2026-08-14 · **Decided by:** Claude Opus 5, confirmed by Afaq

When our data disagrees with a client-sourced label, the client wins regardless
of how many rows say otherwise. `docs/CLIENT_CONVENTIONS.md` records every
confirmed rule with its provenance tier.

**Why:** it happened twice in one session. Butane cartridges showed 15 rows as
`EXP-11.5` against 2 as `EXP-16.2`; the 15 were our keyword audit and the 2 were
`client_product_rule`. Groceries showed the client "filing biscuits under Office
Supplies" — he never did, our audit did, and his one real supermarket label was
toilet paper. Counting rows gave the wrong answer both times.

## D-032 — Source direction and client instruction beat structural audit theories

**Date:** 2026-08-17 · **Decided by:** Afaq · **Model:** Codex GPT-5.6

The 103 DTE-43 animal-auction rows from Tattersall Ganado and Feria Ganaderos
Osorno are `COMPRAS` in their source folder and every `input_id`. The client
created `AF-1.1 Compras de Animales` for purchases. They remain auto-accepted
as `AF-1.1`; an audit may not recast them as income merely from document type,
supplier business, or related freight lines.

**Why:** the recovered audit mixed a plausible story about an auction settlement
with an unsupported conclusion about the buyer/seller relationship. That would
have overridden both transaction direction and the client's own category.

## D-033 — A plate-field value outside the client's confirmed signals is review

**Date:** 2026-08-17 · **Decided by:** Afaq · **Model:** Codex GPT-5.6

For petrol, auto-accept only a recognised vehicle plate or a confirmed loose
`BIDON` spelling under the client rule. `ENVASE`-style entries and garbled
plate-like values are neither signal, so they remain predicted hints but must be
`review_required` with `final_code = NULL`.

**Why:** the client told us what the two meaningful signals are. Treating a
third spelling as farm fuel, or a malformed value as a vehicle plate, turns an
unproven interpretation into a final accounting answer.

## D-034 — Raw invoice text stays immutable (design withdrawn 2026-08-18)

**Date:** 2026-08-17 · **Decided by:** Afaq · **Model:** Codex GPT-5.6
**Amended:** 2026-08-18 — the specific schema below is **withdrawn**.

**Amended 2026-08-25 by Afaq:** the raw-evidence rule still holds; the old
restriction on repurposing `item_catalog` does not. `invoice_items.item_text`,
description, item code, supplier, invoice folio and line number remain the
evidence and the link back to the original XML. The approved canonical catalog
may repoint only `catalog_item_id` while leaving all of those fields unchanged
(D-044).

**What is withdrawn.** The two-table proposal (`product_catalog` plus
`product_catalog_mapping`) and the two-invoice-line dashboard threshold were our
assumptions, not the client's requirements. The prototype that implemented them
was deleted on 2026-08-18, before the client meeting that decides how far to
normalise. Do not resurrect that schema from memory — the answers may imply a
different shape entirely. Nothing was ever applied to Supabase, the staged
payload, raw XML or the frontend.

## D-035 — Catalog clustering is supervised candidate discovery, never mapping

**Date:** 2026-08-18 · **Decided by:** Afaq · **Model:** Codex GPT-5.6
**Status:** the *principle* holds and applies to any future attempt. The
implementation it describes was deleted on 2026-08-18 with D-034's schema.

Use a locally cached multilingual sentence embedding plus character-gram
similarity only to retrieve candidate source-wording pairs and overlapping
review neighbourhoods. An item may belong to several candidate neighbourhoods.
Neither a semantic score nor a connected component creates a canonical product
mapping. Inspect the actual members first; only then may a small deterministic
rule create a *suggested* mapping.

**Amended 2026-08-25 by Afaq:** similarity remains candidate discovery, never
the authority that maps a line. However, non-functional specifications such as
size, dimensions, gauge, capacity, pack quantity and month may merge when the
underlying product/service is the same; `Clavos` covers its sizes. Grade,
model/OEM identity, purpose and underlying contract remain separate when they
change the actual product/service. Volatile work-order numbers and months are
handled by narrow reviewed patterns, not stored one by one as aliases.

**Why:** flat semantic clusters put Gasolina 93 next to Gasolina 95, pipe
fittings of different sizes together, and different needle lengths together.
They are useful as a work queue but unsafe as a catalog. This preserves the
dashboard's purpose: a canonical header is a real comparable product or service,
while original invoice wording stays visible as evidence.

**Rejected:** Ollama/LLM batch normalisation, a separate matching classifier, and
automatic HDBSCAN or connected-component assignment. There is no approved
same/different-pair corpus. This authorises no Supabase, staged-payload, raw-XML
or frontend change.

## D-036 — Catalog cleanup is decided by the client, not inferred from the data

**Date:** 2026-08-18 · **Decided by:** Afaq · **Model:** Claude Opus 5

Item-catalog canonicalization stops until the client answers how far to
normalise. The prototype built on 2026-08-17/18 was deleted outright rather than
parked, because keeping it would invite a future session to resume from a schema
the client never approved. Nothing was ever applied to Supabase, the staged
payload, raw XML or the frontend, so there is nothing to roll back.

**Why:** how far to collapse is a business judgement with no data-derivable
answer. Whether `WD-40 226 GRS` and `WD-40 458ML` are one item depends on
whether the client compares per-unit or per-purchase; whether `ABRAZADERA SEBCOR
1/2"` and `2 1/2"` merge depends on whether they treat them as substitutes. Our
prototype answered these by assumption. Seven such questions went to the client
with measured examples; building before the answers means building twice.

One call is already settled and survives the deletion: **a licence plate stays
part of an item's identity.** Maintenance on truck A is a different catalog item
from truck B, so a single vehicle's cost history is visible. The deleted
prototype merged them, which was wrong.

**Rejected:** keeping the prototype behind a flag (it would be resumed from
without re-reading the client's answers); committing it to an archive branch
(git history is the archive, and this was never committed, so there is no
history to preserve — the measured findings live in the client brief instead).

**Unparked 2026-08-25 by Afaq:** Afaq and his colleagues approved the business
rule and reviewed the proposed groups. Implementation now follows D-044. The
2026-08-18 stop was correct at the time but is no longer an active blocker.

## D-037 — A row reaches auto_accept only on a rule the client wrote

> **Narrowed by D-040 (2026-08-19).** Condition 2 below — "the model
> independently predicts the same code" — no longer applies where the client
> filed the same kind of item **consistently**. His filing wins and the model
> disagreeing is usually the undertraining, not a second opinion. Read D-040
> before applying this entry; on its own it would forbid promotions that are
> already live.
>
> **Also read literally, this entry describes a bar the existing data does not
> meet.** ~732 auto-accepted rows predate it and rest on `silver_audit_v2`
> keyword matching (365 tagged `silver_audit_backfill`, 367 hiding inside
> `client_evidence_backfill` — see D-042). They were audited against every
> product the client ruled on and scored **0 contradictions in 7,286**, so they
> are not being unwound; but this rule governs *new* promotions, it does not
> describe the whole table.

**Date:** 2026-08-18

**Amended 2026-08-18 (Afaq) — a client rule is no longer the only route.**
A row may also be promoted when **the model and an independent manual auditor
(Claude or Codex) both agree, and the object physically makes sense in that
account**. The two eyes must be independent: the auditor judges what the product
*is*, not what the model said. Where a client rule exists it still outranks both
— see D-030. Where none exists, unanimity between model and auditor plus a
physical-sense check is sufficient. Anything short of unanimous stays in
`review_required` with a corrected hint.

The original three conditions, which remain the strict path when a client rule
covers the product:

1. a rule **the client wrote** covers the product — `client_product_rule`,
   `direct_client_example`, `client_service_rule`, or a family resolution
   derived from one. Brand, size and supplier may differ; the product may not;
2. the model **independently** predicts the same code. Once the evidence stops
   being unanimous it is not a promotion, it is a guess with a citation;
3. the object physically makes sense in that account.

Our own reasoning is never sufficient, however obvious it feels. A brucellosis
test plainly is not building maintenance, but "plainly" is what put nails in
Agrochemicals in the first place. Such rows get a corrected **hint** and stay in
`review_required`.

`silver_audit_backfill` does **not** qualify. It was produced by an Ollama pass
with review, and four products are now known where it contradicts a client
label outright (`CLAVO TERRANO`, `LEVANTADOR DE VACAS`, `MOSKIMIC FORTE`,
`ORBENIN E.D.C`). It is a hint, not authority — in either direction.

**Why:** `HORA TECNICA` was promoted onto the client's example `HORA TECNICA AM`
and reverted the same session. The client ruled on one technician's initials;
gold labels a second set of initials from the same supplier to a different
account. A client example covers the row he labelled, not every variant of it.

**Consequence:** promotions are small and slow. 153 rows on 2026-08-18, against
a review queue of thousands. That is the intended trade — see D-001.

## D-038 — Read the description and the client's rules before calling a row wrong

**Date:** 2026-08-18

Four auto-accepted rows were flagged as silver-audit errors on 2026-08-18. Three
were correct, and "fixing" any of them would have overwritten a client
convention:

- `SMART BLUE …FERTILIZANTES(B)-UREA`, CLP 67.3M — `SMARTBLUE FUNDO` is a
  client product rule mapping to `EXP-6.2`, and the item name ends in UREA.
- `BIDON CERT. AMARILLO DIESEL 20 L` — read as diesel fuel because a neighbouring
  line's description mentioned `Impuesto base combustible`. The row itself has
  `additional_tax_code = None`, `quantity = 1`, `unit = UN`, flat unit price.
  Real diesel in this payload carries tax code **28**, `unit = Lt`, and a
  per-litre price. It is the jerrycan. The client's rule was right.
- `VENTA MATERIAL`, CLP 13.03M — called meaningless from `item_text`. Its
  **description** is `MAICILLO`, road surfacing gravel, from an excavation
  contractor. `EXP-14.1` is right.

A fourth scare came from our own tooling: 56 fuel rows looked like plated
vehicle fuel filed as farm petrol, contradicting five client examples for that
station. The `<Patente>` values are `BIDO93`, `BIDO45`, `IBDO96`, `VIDO93` —
"bidón" typed into the plate field with the fuel grade appended, including
typos. The production rule already handles them; the ad-hoc check written to
audit it did not.

**Amended 2026-08-18 (Afaq) — what to do with a finding that has no client rule.**
If a client rule covers the product, the rule decides and the finding is checked
against it. If **no** rule exists, the finding may be applied only when the
correction is beyond doubt — the object is unmistakable and the model agrees.
Otherwise the row is not left where it is and not promoted either: it moves to
the **best available account as a corrected hint** and stays `review_required`.
A wrong-but-closer hint is worth more to the reviewer than a wrong-and-far one.

**The order is:** read `description`, check `additional_tax_code`/`unit`/
`quantity`, grep the client's rules, and only then call an auto-accept wrong.
Verify the audit tool against the production rule before trusting a discrepancy.

## D-039 — Hardware with no named job needs a default, not a new category

**Date:** 2026-08-18 · **Decided by:** Afaq, on measured evidence · **Model:** Claude Opus 5

Do **not** create a category for "tools and materials bought to support a fixed
asset". The idea was raised because 1,562 hardware- and building-store lines sit
in review with nothing on the invoice naming a job. It was rejected on the data.

Two categories already cover it, and one is the client's own:

- `EXP-16.1 Ropa y Herramientas de Trabajo` holds 422 lines, 371 auto-accepted,
  **305 of them placed by rules the client wrote.** Tools are not homeless.
- `EXP-14.2 Mantencion Cercos` holds 206 auto-accepted rows of *physical fence
  hardware* — nails, staples, pigtail posts, insulators. All ten fastener rules
  in `product_lookup` are `client_product_rule` pointing there.

**The client's pattern, read off his own placements:** a maintenance category
holds the work done on that system **plus the parts specific to that system**.
`EXP-14.4 Mantencion Instalaciones` is almost pure labour (16 auto rows: `MANO DE
OBRA`, `INSTALACION`) precisely because a generic bolt is not specific to
anything.

**Why:** the measurement is unambiguous. Of the 189 hardware-store lines that
*were* auto-accepted, **121 (64%) name their own system in the product text**
(HDPE, `ASPERSOR`, chainsaw, fencing). Of the 1,428 still in review, **38 (3%)**
do. The stuck lines are objects genuinely at home in four categories at once — a
1/2" nipple fits water, slurry, irrigation and the milking parlour, and all four
are correct. A catch-all category would give every one of them a home and destroy
the only thing the categories exist for.

**Consequence:** the open item is a client question — is there a default, or does
his team place each one? If the answer is "our team places them", that is a
complete answer and those lines stay in `review_required` by design, exactly as
untagged petrol does under D-029.

**Rejected:** a "supporting tools / fixed-asset consumables" category; inferring
the job from sibling lines on the same invoice (a ferretería receipt mixes jobs);
widening `product_lookup` with generic hardware (no client rule exists to anchor
it, and D-037 requires one or an unambiguous physical read).


## D-040 — A consistent client folder placement outranks the model

**Date:** 2026-08-19 · **Decided by:** Afaq · **Model:** Claude Opus 5

`file_audit` — a label inferred from the folder the client filed the invoice in —
was rated **Medium** trust because we feared noise: an invoice dropped in the
wrong place by accident. Measured across all 392 `file_audit` gold rows,
**363 of 369 distinct item-kinds went into exactly one category (98%)**. The only
6 that split are electricity lines from the Paillaco co-op, where the account
genuinely depends on which meter it is — already handled by `meter_lookup`, not
client error.

**So where the client filed the same kind of item the same way every time, his
filing wins, and the model's disagreement is not a veto.**

**Why:** consistent placement is intentional placement. Afaq's argument, and it
held under measurement. The worked example is `Revision Tecnica`: he files
`Automovil particular camioneta` under `EXP-13.3` (4 of 4) and `Maquinaria
automotriz` under `EXP-13.1` (1 of 1) — the inspection follows what the asset is.
The model predicts `EXP-13.3` for both, because exactly **one** machinery example
exists in all of gold. That disagreement *is* the undertraining; treating it as a
second opinion inverts the evidence.

The bar is the one `product_lookup` already clears to auto-accept 2,639 rows: an
exact item + supplier match to something the client decided. A plate or a size
differing does not make it a different product.

**Three limits, all of which fired in practice on 2026-08-19:**
- **A spec sibling is only safe when the siblings agree.** The client filed
  `FILTRO LECHE JUMBO 100 UND` under `EXP-10.1` and `FILTRO LECHE 75 MM * 800 SE`
  under `EXP-10.4` — same product, same supplier, different size, different
  account. Held in review.
- **The placement must also make physical sense.** `PIOLA PERLON RETIRADOR`, a
  nylon cluster-remover cord, is filed under `EXP-10.3 Detergentes e
  higenizantes`, an account holding ZINICIN, ORACID and chlorine. That is the
  misfile we feared. Held in review, model hint left in place.
- **A placeholder item name is never a match key.** `Item`, `DETALLE`,
  `MATERIALES` identify no product and collide with every other placeholder from
  the same supplier — the same empty-key bug that produced 138 false
  contradictions on 2026-08-18. Read the description instead; it carries the real
  product on **141 of 155** vague-named review rows, CLP 106.8M.

**Rejected:** requiring model agreement in all cases (D-037's bar) — it lets an
undertrained model overrule the client, which is backwards; and blanket-trusting
`file_audit` without the three limits above.

**Superseded scope:** narrows D-037's promotion bar. A client-sourced label plus
consistency now qualifies; model agreement strengthens it but is not required.

## D-041 — Never resolve in the payload a question currently open with the client

**Date:** 2026-08-19 · **Decided by:** Claude, endorsed by Afaq · **Model:** Claude Opus 5

If a question has gone to the client and is unanswered, the affected rows stay in
`review_required` even when we could argue a defensible answer.

**Why:** it happened twice on 2026-08-19 and was caught both times. Three
`TRASLADO BOLOS` rows matched a client convention saying Hay while the model said
Silage — silage-vs-hay is question 4 of the email sent that day. And four SONDAJES
PERFOMAQ lines were promoted to `EXP-14.3` on their descriptions before rereading
showed they describe **buying and improving equipment** (`REEMPLAZO EQUIPO
SUMERGIBLE POR UNO NUEVO`, `MEJORAS EN INSTALACION`, `PUESTA EN MARCHA … SONDAJE
N° 2824`), and the supplier's giro is `Perforacion de Pozos Profundos, Const. e
Instalaciones`. Expense-vs-fixed-asset is **question 1** of that same email.
Reverted by `scripts/92_revert_sondajes_capital_rows.py`.

Answering it ourselves would make the client's reply arrive to a database that
had already decided, and we would not know which rows to revisit.

**Consequence:** before any promotion, check the open-questions list in
`CLIENT_CONVENTIONS.md`. Pure-service lines from the same supplier are still fine
— `LIMPIEZA DE POZO 6"` and `REVISION … FALLA EN CONTACTOR` stayed auto-accepted,
because neither creates an asset.

## D-042 — `prediction_source` will be consolidated, but not in the same upload

**Completed by D-047 on 2026-09-03.** The consolidation described here has
been applied to production; the six surviving values are listed there.

**Date:** 2026-08-19 · **Decided by:** Afaq · **Model:** Claude Opus 5

Two problems are recorded and deliberately **not** fixed yet:

- `manual_recategorisation` (327) and `manually_audited_near_identical_backfill`
  (216) are the same principle at different confidence, and are **perfectly
  determined by the `decision` column** — 100% review and 100% auto respectively.
  One of the two tags carries no information.
- **`client_evidence_backfill` is a misleading name.** Of its 612 rows, **none**
  trace to a highest-trust client label: 243 rest on `file_audit` and 367 on
  `silver_audit_v2`, which is our own keyword matching. The tag asserts an
  authority nothing behind it has — precisely what the rule at the top of
  `CLIENT_CONVENTIONS.md` exists to prevent.

A third tag has the same defect: **`business_rule` (928 rows) means two
different things** — the 28 `ING-*` sales rules that fire at inference (D-016),
and "a correction script applied a deterministic rule", which is 804 of the 928.

**Why not now:** renaming a source value needs another migration plus rewriting
provenance on 543 rows, on the same day two label uploads went out. Two changes in
one upload means a failure tells you nothing about which one broke.

**Consequence:** read the backing gold `source`, never the `prediction_source`
tag, until this is done.

## D-043 — Say which decision you are relying on, before you act on it

**Date:** 2026-08-19 · **Decided by:** Afaq · **Model:** Claude Opus 5

Whenever a `D-NNN` is about to shape what gets built, labelled, promoted or
written, **name it to Afaq in plain language with its reasoning, and wait** —
before acting, not in the summary afterwards.

This is wider than the existing rule about contradictions. That one only fires
when Afaq asks for something a decision forbids. This one fires whenever a
decision is *load-bearing for the next step*, including when it agrees with what
he asked for. The point is that the rationale passes through him every time it is
used, not only when it collides with him.

**Why:** the decision log is now 40 entries deep and much of it was written in
sessions Afaq does not remember. A past decision applied silently is
indistinguishable, from his side, from the agent inventing a rule — and he cannot
withdraw consent from reasoning he never sees. On 2026-08-19 he overruled D-037's
model-agreement requirement within minutes of it being explained, because it was
letting an undertrained model veto the client. Had it been applied silently, the
`Revision Tecnica` rows would have stayed wrong and nobody would have known which
rule made them so.

Two more from the same day: a proposed date-window rule for capitalising
contractor invoices was killed on sight once stated out loud, and the claim that
`client_evidence_backfill` meant "the client labelled this" collapsed the moment
he asked for the trace instead of accepting the tag.

**How to apply:**
- State the entry, what it says, and what it makes you do next. One or two
  sentences, no jargon, no "see D-0NN".
- Say it *before* the edit, script or promotion — not in the report.
- If he disagrees, the decision is amended or superseded in the same session.
  A decision he no longer agrees with is stale by definition (see D-027).
- Batch sensibly. Several rows governed by one decision is one disclosure, not
  one per row.

**Rejected:** relying on him to read `DECISIONS.md` — he does not read the docs,
that is the agent's job (global `CLAUDE.md`); and surfacing only on conflict,
which is the rule that already existed and is what let D-037 sit unchallenged for
a day.

## D-044 — One real product or recurring service gets one canonical catalog ID

**Narrowed by D-105:** the canonical name is display-only; purchasing search matches invoice wording.

**Date:** 2026-08-25 · **Decided by:** Afaq and colleagues · **Model:** Codex GPT-5.6

Reuse `item_catalog` as the user-facing canonical catalog. Different spelling,
case, pack/size specification, month or installment number does not create a new
catalog item when the underlying product or recurring service is the same.
Different grades, actual products, purposes, assets and underlying contracts
remain separate. Original invoice `item_text` and `description` never change;
history displays both beneath the canonical name.

Add one `item_aliases` table for true alternate wording such as `G93` →
`Gasolina 93`. Do not store case-only duplicates, `SEGUN OT 81/82/...`, months,
dimensions, quantities or generic placeholders as aliases. Future ingestion
checks exact normalized canonical names, supplier/global aliases, then narrow
approved patterns; fuzzy similarity only suggests review candidates. Matching
belongs in the backend ingestion path, not the frontend. No such online writer
exists in this repository yet, so runtime matching is deferred and documented.

The approved local payload is 11,746 invoice lines, 4,029 canonical rows and 8
initial aliases. It is not production until Afaq separately approves a fresh
backup and the guarded transaction. Frontend push/merge is another approval.

## D-045 — The catalog migration ships as three idempotent steps, not one transaction

**Date:** 2026-08-26 · **Decided by:** Afaq · **Model:** Claude Opus 5

`002_apply_canonical_catalog.sql` — the generated single guarded transaction —
was **not** used. It is 2.6 MB, which the Supabase SQL editor will not accept,
and this project holds no Postgres connection string: `Temp_Inference/.env.loader`
carries REST keys only, and every write ever made here has gone through
PostgREST. The one prior SQL migration was pasted into the SQL editor by hand
because it was a few lines long.

The migration was therefore split:

- **step A** `003_step_a_schema.sql` — SQL editor. Creates `catalog_normalize_label`
  and `item_aliases`; drops the old `(item_name, description)` unique constraint.
- **step B** `scripts/94_apply_canonical_catalog_rest.py` — PostgREST. Insert 16,
  repoint 2,122, delete 1,398, rename 3,366, insert 8 aliases.
- **step C** `004_step_c_unique_index.sql` — SQL editor. Unique index on the
  normalized `item_name`, plus the referential `left join`.

**Why:** atomicity was unavailable, so it was replaced with two weaker
properties that together cover the same risk. Every phase is **idempotent**
(upsert merges on the primary key, PATCH sets an already-known value, DELETE of
an absent row is a no-op), so a failure part-way is resumed by re-running — which
is exactly what happened when the alias insert failed and phases 1–4 re-applied
harmlessly. And the phase **order** keeps every intermediate state valid: lines
are repointed only onto rows that already exist, and rows are deleted only once
nothing references them. A crash leaves a partly-grouped catalog, never a
dangling reference.

**The cost, stated plainly:** between step A and step C, `item_catalog` has no
uniqueness constraint at all. That window must be closed in the same working
session. It was not — it stayed open for one day. Step C ran on 2026-08-26 and
returned `4029 | 11746 | 8`, closing the migration.

**Rejected:** pasting the 2.6 MB file (the editor cannot take it); splitting the
transaction into chunks pasted in sequence (loses atomicity *and* idempotency —
strictly worse than this); asking Afaq for the database password (avoidable, and
a credential we do not otherwise need).

**Also decided:** the numbered uploaders were spent one-shot scripts, not a
standing re-load path. **They were deleted on 2026-08-26 (D-046)** along with
every prescriptive reference to them.

## D-046 — The numbered one-shot scripts are deleted, not kept as reference

**Date:** 2026-08-26 · **Decided by:** Afaq · **Model:** Claude Opus 5

Nineteen numbered scripts — the Supabase bundle builder, the payload preparer,
the pre-flight, both uploaders, and every one-shot correction script from 82 to
94 — were deleted. Each was written against a database state that no longer
exists. Keeping them "as reference" cost real attention every session: they were
cited 21 times across `CLAUDE.md` and `docs/`, and every citation pulled a dead
path back into a live conversation. `scripts/82` was the worst of them — it still
carried the pre-canonical 5,411-row catalog and would have fought D-044 if run.

**Kept:** `scripts/supabase_rest.py` (the live PostgREST client),
`scripts/81_backup_supabase.py` (the backup path), and the whole offline ML
pipeline (`10`, `50`–`77` minus the deleted correction scripts), which is
re-runnable and still needed for the next retrain.

**The cost, stated plainly:** `scripts/` is gitignored, so five of the deleted
files (`74`, `76`, `78`, `79`, `94`) were untracked and are **gone permanently** —
git is not the archive here. `94` is the script that applied the canonical
catalog migration. The migration itself is recorded in
`reports/canonical_catalog_2026_08_25/` and was verified against live, so what
was lost is the mechanism, not the result. Afaq was told before deleting and
chose to proceed.

**Rule that replaces them:** there is no re-load path. Every change to live data
is a scoped PostgREST write touching only the rows it names, dry run first,
backed up first, behind an explicit flag.

**Load-bearing facts folded out of the deleted D-031** and into
`docs/ARCHITECTURE.md`: a PostgREST upsert is `INSERT ... ON CONFLICT`, so a
partial-column payload fails the insert arm on every NOT NULL column it omits —
send whole rows or `PATCH`; and `categories_id` is database-generated, so
locally-invented UUIDs are meaningless.

**Also deleted:** D-031 ("Script 80 is first-load only; script 82 is the
re-load"), which described only the two deleted scripts and was cited nowhere.

## D-047 — `prediction_source` is six values, and four cleanup tags became one

**Date:** 2026-09-03 · **Decided by:** Afaq · **Model:** Claude Opus 5

The column now allows exactly `model`, `product_lookup`, `meter_lookup`,
`business_rule`, `cleanup`, `user_selected`. Four historical tags collapsed into
`cleanup` across **2,066 rows**: `manual_recategorisation` (823),
`client_evidence_backfill` (611), `silver_audit_backfill` (366),
`manually_audited_near_identical_backfill` (266). Applied via
`milk-company/supabase/004_consolidate_prediction_source.sql`.

**Why:** the four named one-shot passes whose scripts were deleted under D-046,
so they described code that no longer exists. `client_evidence_backfill` had to
go regardless of tidiness — D-042 measured that **0 of its 611 rows** trace to a
client-sourced label, so the name asserted an authority it never had.

**What it costs, stated plainly:** 592 of the `manual_recategorisation` rows were
the 2026-09-02 labels applied from the client's own written answers — the
strongest provenance in the table — and they now read as `cleanup` like
everything else. That is acceptable only because **the tag was never the
evidence**, which is the whole point of D-042. The trace for those rows is
`reports/client_reply_2026_09_02/*.jsonl`, which records the client's own
sentence per row, and `docs/CLIENT_CONVENTIONS.md` §9. Do not reconstruct
provenance from this column.

**Verified:** only `prediction_source` changed, on exactly 2,066 rows; 0 rows had
any other column move; raw-evidence SHA `1d2718423f2bb6db` and label SHA
`e823044ce9df6013` both identical before and after.

**Rejected:** keeping the four names for historical fidelity. Git history and
`reports/` already hold that, and a tag a reader will misinterpret is worse than
one that admits it means "a pass we ran once".

## D-048 — The dashboard writes to Supabase through a Server Action, never the browser

**Date:** 2026-09-03 · **Decided by:** Claude, approved by Afaq · **Model:** Claude Opus 5

The category-assignment dialog is the **first write path this product has ever
had** — every other change to live data is an offline script. It writes through a
Next.js Server Action (`src/app/[locale]/productos/actions.ts`), never a
browser-side Supabase call.

**Why:** the page reads with the publishable key, which is visible to anyone who
opens the browser's network tab. A browser-side write would let anyone holding
that key rewrite the client's accounting. The Server Action runs on the server
carrying the user's session, so the database sees an `authenticated` user.

Three things the write must keep doing, each learned the hard way this session:

- **Never write `needs_review`.** It is a GENERATED column; PostgREST returns
  `400` and takes the whole batch down. Setting `decision` and
  `final_categories_id` is what moves it. Same class as the `normalized_alias`
  gotcha of 2026-08-26.
- **Re-read the category server-side.** The client sends an id; the action reads
  the code from the database so a tampered request cannot store a `final_code`
  disagreeing with its own `final_categories_id`.
- **Report a partial write as a failure.** A silent partial save on accounting
  data is worse than a visible error.

**RLS is the gate, and it is easy to miss.** Row-level security is enabled and
the anon role sees **0 rows in every table**. Reading worked because a
`SELECT` policy exists for `authenticated`; writing needed its own `UPDATE`
policy, which did not exist and was added on 2026-09-03. A read policy grants
nothing about writes.

**Rejected:** writing with the service key from a route handler. It would work
and it would bypass RLS entirely, which throws away the only thing standing
between a leaked publishable key and the client's books.


---

## D-049 — A statistic is scored against its own population, never a pooled one

**Date:** 2026-09-03 · **Decided by:** Claude, approved by Afaq · **Model:** Claude Opus 5

Any detector that asks "is this value unusual?" computes its mean and standard
deviation **within the group the value belongs to**. In this project that means
COMPRAS and VENTAS are separate populations everywhere — outlier detection,
averages, thresholds, and anything derived from a spread.

**Why:** the dashboard's `detectAnomalies` pooled every invoice into one
z-score. Measured on `backups/supabase_20260903T054820Z`, COMPRAS averages
1,132,672 across 5,107 invoices and VENTAS averages 71,345,335 across 88. The
pooled standard deviation came out at 25,514,580 and broke the detector in both
directions at once:

- the critical cut landed at **91,623,060 CLP**, so 9 of the 14 "critical"
  flags on the default window were ordinary milk sales with nothing wrong with
  them;
- and that same inflated spread hid the real ones. Only **5** purchase invoices
  cleared the pooled bar; scored against COMPRAS alone, **24** do.

A wrong number that reassures is worse than no number. Both failures came from
one line, and neither was visible without recomputing against real data —
`tsc`, lint and the build were all green throughout.

The two directions are already known to be incomparable: `DECISIONS_LEDGER.md`
in the frontend records VENTAS as 1.7% of documents and 52% of the money. That
asymmetry is exactly why they cannot share a distribution.

**Rejected:** raising the z threshold. It would have removed the false flags
and buried the real ones deeper — the thresholds were never the problem, the
denominator was.

**Proof:** `scripts/check-anomaly-direction.ts` in the frontend repo asserts
both halves and fails against the previous code. Fixed in `59c4cb1`.

## D-050 — A settled line never displays the model's suggestion

**Date:** 2026-09-03 · **Decided by:** Afaq · **Model:** Claude Opus 5

Once a line's category is confirmed — a human reviewed it, or the pipeline
auto-accepted it — no surface shows what the model would have guessed. The
suggestion exists only for rows still in review.

**Why:** the Analítica → Ítems tab carried a "Model suggestion" column that ran
on every line rather than only pending ones. Of 4,002 products, **1,574 had no
pending line at all and still showed a guess, and 148 of those guesses named a
different category than the confirmed one.** That is the model publicly
second-guessing a closed decision, which is the same failure family as
**D-001** — a prediction presented where a classification belongs.

Afaq's instruction was to remove the column, not to gate it: a suggestion on a
row with nothing left to decide has no reader and no use.

**This reverses decision B2** in the frontend's `docs/DECISIONS_LEDGER.md`,
which had specified the separate suggestion column on 2026-08-27. That entry is
marked superseded in the same change.

**Rejected:** gating the column on `resolved.state === "pending"`. Correct, one
conditional, and still leaves a column that is empty on 39% of rows and
meaningless on the rest.

Removed in `1dad390`, merged as `2b6c45d`.

## D-051 — Ingestion is deterministic code; the agent is only where judgement is

**Date:** 2026-09-08 · **Decided by:** Afaq · **Model:** Claude Opus 5

Reading the inbound file, unpacking it, parsing the DTE XML, checking the
sender, detecting duplicates, calling `/predict-batch`, storing the result and
sending the acknowledgement and reception report are **plain code**. No agent
sits anywhere in that path.

The agent's scope is exactly three things, all of them judgement calls:
proposing a category for a review line with its evidence, reading a free-text
question and choosing which query answers it, and drafting a purchase order
request from a plain-language sentence.

**Why:** Afaq's own objection, and it was correct. "Why do we need a unit to
take an email and send it to an endpoint when we can hook the email, run it
through deterministic code and hit the endpoint ourselves?" There is no
judgement in the pipeline, so an agent there adds cost, latency and a failure
mode for nothing. It also means ingestion ships standalone, without the agent
existing.

**Rejected:** the earlier framing that had the Yunt owning ingestion end to
end. That plan was deleted on 2026-09-08; the surviving recipe is
`docs/YUNT_IMPLEMENTATION_PLAN.md`.

## D-052 — Purchase orders v1: two forms, no roles, no approval step

**Date:** 2026-09-08 · **Decided by:** Afaq · **Model:** Claude Opus 5

Form one opens an internal request: what is needed, how much, by when, for
which farm or cost centre. The request stays open and is how open needs are
tracked.

**Obtaining quotations is outside the system.** There is no way to contact a
supplier from the dashboard. Whoever is responsible negotiates by their own
means and agrees a price.

Form two places the order: supplier, final agreed price, quantity, delivery
date. Above CLP 500,000 at least two quotations must be uploaded, which is the
rule already displayed on Antillanca's own home screen. Below that no formal
quotation is required and the buyer records the price the supplier gave them.
The output is a PDF that Antillanca sends to the supplier themselves.
Generating the order closes the request.

**Roles and approval routing are explicitly deferred to v2.** The dashboard
lists six roles but today they only filter sidebar links: the role is React
state initialised to `ADMIN` in `app-sidebar.tsx:40`, switchable by a header
dropdown, and `middleware.ts` checks only whether a user is logged in. Any page
is reachable by URL regardless of role. Promising approval routing means making
roles real first, and Antillanca has not said who approves at what amount.

**Why:** Afaq's call, to keep v1 one-way and shippable. Separation of requester
from approver is an internal control; where one person does all of it, it is
ceremony.

**Rejected:** enforcing the approval phase in v1. It would have made user roles
a prerequisite for the whole purchase-order feature.

## D-053 — Open-ended questions are answered by parameterised query tools

**Date:** 2026-09-08 · **Decided by:** Afaq · **Model:** Claude Opus 5

Reports are not written in advance and the model does not write queries freely.
The query space is enumerated once as about five parameterised tools. The main
one takes filters (date range, direction, document type, category, supplier,
item, state, amount range), a grouping (month, category, supplier, document
type, item, city) and a measure (sum, count of lines, count of documents,
average unit price, min, max) plus sort and limit. Four more cover period
comparison, single-item price history, row-level listings for the spreadsheet
attachment, and precedent lookup. Charts come from a fixed set: bar, line,
stacked bar, pie, table.

**The model picks the tool, fills the parameters, chooses the chart and writes
the prose around the result. Code runs the query, computes every number, renders
every output, and prints the exact filter used at the top of every answer.**
No number in any answer is written by the model.

A question that fits no tool is refused, saying so. The refusal list is the
backlog for what to add next.

**Why:** it makes "he can ask anything" a promise that can actually be kept.
The openness lives in the parameter space, not in the code, so the surface is
large and the implementation is small and testable.

**Rejected:** letting the model author SQL against a read-only role. Larger
blast radius, unbounded output shapes, and every number then originates from
the model rather than from code.

## D-054 — The Audisoft API is the intended ingestion source; email is the fallback

**Date:** 2026-09-08 · **Decided by:** Rodrigo, relayed by Afaq · **Model:** Claude Opus 5

Antillanca's accounting vendor, Audisoft, exposes `xmlrecibidos` (purchases) and
`xmlemitidos` (sales) on their system. `crutempresa 96685810-9` matches the
`dte_96685810_*` folders, so it serves the same document stream already parsed.
Two endpoints also remove the need for the `COMPRAS/` and `VENTAS/` folder
convention, since direction becomes native.

**Email ingestion is still built, as the fallback.** Only the first step
differs; parse, deduplicate, classify, store and report are shared, so the
source is a thin swap at the front. Email also stays useful afterwards for
backfills and anything not in Audisoft's system.

**The spreadsheet template is deferred.** It existed only for data with no XML
behind it, and that need mostly disappears if the API works.

**Why:** it removes the manual export step entirely, and clause 5.1 of
Audisoft's terms gives no uptime guarantee while 6.2 lets them revoke access
without notice, so a second path must exist regardless.

## D-055 — The Yunt is an eve agent in Next.js on Vercel; GCloud keeps only the classifier

**Date:** 2026-09-09 · **Decided by:** Afaq · **Model:** Claude Opus 5

The Yunt is built with [eve](https://vercel.com/eve), Vercel's agent framework,
inside the existing `milk-company` Next.js app — same repo, same deploy, same
database. Google Cloud hosts the classifier endpoint and nothing else.

Everything after the classifier returns a category is ours and lives in
Next.js: reading the XML, matching to the catalog, writing to Supabase. **The
entire ingestion pipeline was ported from Python to TypeScript** into
`../milk-company/src/lib/ingest/`.

**What eve changes, for the better.** Tools are TypeScript files in
`agent/tools/`, auto-discovered — the five parameterised query tools of D-053
become five files with no registration layer. `needsApproval` is a single field
and the agent pauses indefinitely without consuming compute, so the
approve-then-apply flow of the plan is a framework primitive rather than
machinery. Execution is durable and checkpointed, which answers both the
114-second classification and the "the webhook must reply immediately" problem.

**Email is not one of eve's channels** (Slack, Discord, Teams, Telegram, Twilio,
GitHub, Linear), so Resend inbound stays a plain route handler feeding the
deterministic pipeline — which is what D-051 requires anyway.

**Why:** Afaq's call. It puts the agent where the rest of the logic already is,
and lets it reach the ingestion code as a tool later.

**The objection that was withdrawn:** moving off Cloud Run looked like it forced
a TypeScript rewrite of the DTE parser, which Node makes risky (no `DOMParser`,
and `src/lib/extractor/xml-parser.ts` is verifiably wrong on DTE). Vercel runs
Python natively, so that was never forced — but the port happened anyway, for
the reason above rather than under duress.

**The port is verified by equality, not inspection.** Replaying the same 4,451
files gives numbers identical to the Python: 4,451 documents, 10,620 lines, 0
unparseable, 158 rescaled, 50 non-reconciling, and the same document-type
breakdown. Asserted as exact equalities in `scripts/check-dte-corpus.ts`,
because a port that is close is a port that lost a rule.

**Rejected:** separate Vercel projects for the dashboard and the agent. eve
installs into an existing project and its tools need the database logic.

## D-056 — Four measured rules govern reading a DTE, and none came from the spec

**Date:** 2026-09-09 · **Decided by:** Claude, approved by Afaq · **Model:** Claude Opus 5

Each was decided by arithmetic over the 4,451-file corpus. **None was read from
the SII specification** — they describe habit, not law, which is why they are
allowed to raise a flag and not to correct anyone's books (see `CONSTRAINTS.md`).

- **`.` is the decimal point.** `qty * price == monto` holds for 89.4% reading
  it that way and 35.3% reading it as a thousands separator.
- **`MontoItem = qty * price - DescuentoMonto`.** `DescuentoPct` is
  informational; applying both reconciles 15% of discounted lines, subtracting
  the amount alone reconciles 99.5%.
- **`RecargoMonto` is excluded.** It appears on 30 lines, all one supplier, and
  is a verbatim copy of `MontoItem` every time. Stored, never added.
- **Supplier scaling is decided per LINE, not per supplier.** One fuel supplier
  writes quantity and price scaled by 10^4 on some lines and plainly on others
  of the same invoice. Scaling per supplier broke 2,196 lines that were already
  correct. Arithmetic decides whether to rescale; the supplier table only
  supplies the split, which arithmetic cannot recover.

Also: type 43 names its body `<Liquidacion>`, not `<Documento>` — all 29,
CLP 292,085,987, were being skipped as "no DTE found". And Supabase stores a RUT
with the hyphen stripped and the check digit uppercased; matching the DTE's own
format made every document look new.

**This corrects `AUTOMATION_PLAN` A-3.** The `GASOLINA 93` quantity bug was
never the Chilean decimal separator. Together these took non-reconciling lines
from 10.9% to **0.47%**.

## D-057 — An alias is a memorised observation; a pattern is a derived rule

**Date:** 2026-09-09 · **Decided by:** Afaq · **Model:** Claude Opus 5

The distinction the catalog resolver rests on, and the answer to *"how would we
know to strip 5 kg from `cloro organico 5 kg`?"* — **we never have to.**

An **alias** records that a wording has been observed to mean a catalog item.
Bounded, safe, asserts nothing beyond the observation. 222 were harvested from
assignments the verified migration already made: automatic resolution 78.8% →
86.2%, 870 lines gained, **zero new disagreements**. 781 unbounded wordings
(`SEGUN OT 107`) were excluded — one row each, forever, is what D-044 forbids.
585 seen-once wordings were excluded as memorising noise.

A **pattern** generalises to wordings never seen, so it is written only where
the data proves it safe. Exactly one exists beyond P-01: strip a parenthesised
number followed by a unit or a percentage — `( 21 kWh)`, `( 16.5% )`. Never a
bare number, never a number beside a word.

**Verisure set that boundary.** `MONITOREO MES DE 11/2025 CONTRATO 1731275` —
stripping the numbers merges four different contracts, because there the
contract number *is* identity. Yet BICE's `COMISION DE USO MENSUAL (Nro.
Documento: …)` is one item across 23 documents, so a document number is *not*.
**Nothing in the string distinguishes them.** So the rule is as narrow as the
evidence: it touches 519 lines and every one collapses to exactly one item.

**Also rejected, with its evidence, so it is not reinvented:** matching on
supplier plus unit price. 867 pairs, strongest being `Clavos` ↔ `Tornillos` and
`Gasolina 93` ↔ `Petroleo Diesel Ultra`. Price is not evidence of identity.

**And the guard that makes fuzzy matching safe:** every digit-carrying token
must match exactly. Without it, fuzzy proposed `UNION HDPE 50 X 1,1/2HE` onto
`…1,1/2HI` and `VIAJE 32 VACAS` onto `Viaje De 38 Vacas` — different fittings, a
different lorryload of cows, each plausible enough to be ticked through.

**Afaq's framing, which settles the priority:** the catalog is open-ended and
the category list is fixed, so categories are what the product depends on.
Clean up the obvious recurring items — fuel, utility bills — and let everything
else become a new catalog row rather than paying a model per line to decide.

---

## D-058 — The Yunt acts on data problems, but only through one apply path

**Date:** 2026-09-09 · **Decided by:** Afaq · **Model:** Claude Opus 5

The sent scope says of data-quality flags: *"A flag never changes anything; it
is information for a person"* — and then, in the same paragraph, *"The YUNT
proposes fixes to any abnormality and act upon Cristian's approval."* Those two
sentences contradict each other. Afaq settled it in favour of the second, and
stated the principle behind it: **a Yunt is a digital collaborator, not an
advisor — it works on tasks, after Cristian approves them.**

So the split is not flag-versus-fix, it is **detection versus action**:

- **Detection is deterministic, read-only, and never blocks an ingest.** That
  half of the scope sentence stands, and `docs/CLIENT_DATA_ISSUES.md`'s
  constraint with it: a check may flag, never silently change a value.
- **The fix is a proposal**, and every proposal — a category, a data
  correction, a catalog merge — travels the **same** propose → approve → apply →
  undo path (scope item 8, plan Phase 6). One mechanism, one undo, one audit
  trail.

**Why one path and not two.** A second apply mechanism means a second place
where "approved" is defined, a second undo to get right, and a second set of
rows nobody can explain later. The sealed-proposal design already exists and
already carries its target rows and their expected revisions inside itself; a
data fix is the same shape with a different payload.

**What this does not authorise.** Nothing applies without Cristian's approval on
that specific group, and the historical 11,746 rows are untouched by it — those
are a separate backfill with its own approval.

---

## D-059 — The scope document is a client-facing menu, not the build's source of truth

**Date:** 2026-09-09 · **Decided by:** Afaq · **Model:** Claude Opus 5

`docs/Yunt_scope_v1.docx` was sent to the team on 2026-09-07. **Several things
were settled by discussion afterwards, and the document was not re-issued.**
Afaq, when the drift was surfaced: *"things were discussed after the scope
document that is not authoritative."*

Two copies of it exist and they differ — the sent one is authoritative *as a
record of what the client was promised*, and the repo now holds that copy.

**The rule:** where the scope document and `DECISIONS.md` disagree, the decision
log wins and `YUNT_IMPLEMENTATION_PLAN.md` follows the decision log. The scope
document is never edited to match the build; it is what Antillanca agreed to
receive, and rewriting it after the fact would destroy the only record of that.
When a change is big enough that Antillanca needs to know, it goes out as a new
version with a new date, not as a silent edit.

This also retires the claim, made in `YUNT_IMPLEMENTATION_PLAN.md` until today,
that the plan is "the recipe behind the docx". It is the recipe behind the
decisions.

---

## D-060 — The ZIP upload page is a permanent fallback, not a stopgap

**Date:** 2026-09-09 · **Decided by:** Afaq · **Model:** Claude Opus 5

`/carga` in the dashboard takes a ZIP of SII XML (since D-107 also loose XML files) and runs the identical ingest
pipeline the mailbox runs. It was built because scope item 1 (the mailbox) is
blocked on a domain and API keys, but Afaq settled that **it stays**:

- as the path for when Cristian would rather not use email;
- as the fallback for when the mail path — or the Audisoft API, still returning
  401 on every credential form (D-054) — stops working;
- as the only sane route for a full-year backfill, which was never going to
  arrive as an email attachment.

**One pipeline, two doors.** Both call `runIngest` in
`../milk-company/src/lib/ingest/live.ts`. There is no second copy of the reading,
deduplication, resolution or classification logic, so the two cannot drift — which
is the whole reason this is safe to keep rather than a second thing to maintain.

---

## D-061 — The Resend account is shared, so the Yunt filters inbound mail by recipient

**Date:** 2026-09-09 · **Decided by:** Claude, confirmed by Afaq · **Model:** Claude Opus 5

The Yunt receives at **`antillanca.yunt@mountaincreative.cl`**, on a Resend
account (`MC`, Pro, `afaq@mctechstudio.com`) that already serves other projects —
`ppd-agent` has been receiving at `testing@` and `siniestros@` on the same domain
for 23 days.

**The fact that forces this:** a Resend webhook cannot be scoped. Creating one
takes an `endpoint` and an `events` array **and nothing else** — checked against
the API reference, not assumed. So every endpoint registered on the account
receives every `email.received`, whoever it was addressed to. Filtering is the
receiver's job, which is how Stripe and GitHub work too.

**So the route checks the `To:` address before the sender allowlist**, and
ignores anything that is not the Yunt's mailbox — silently, because replying
would put the Yunt in the middle of another project's conversation.
`YUNT_INBOUND_ADDRESS` unset means ignore everything, which is the safe
direction for a filter nobody has configured.

**Rejected — a subdomain of its own.** `yunt.mountaincreative.cl` with its own
MX record is the intuitive fix and it does not work: still the same account,
still no scoping, same fan-out, plus DNS work. Real isolation would need a
separate Resend account, which means separate billing.

**What is NOT solved:** `ppd-agent` still receives a notification for every
invoice email Cristian sends. That is their side to filter and their code is not
in this repo.

**Not on Antillanca's own domain.** `facturas@antillanca.cl` would need their IT
to add an MX record on a subdomain — never the root, which would divert all
their mail to Resend. Worth doing later; it blocks nothing now.

---

## D-062 — Preview deployments reach the webhook through a Vercel bypass secret

**Date:** 2026-09-09 · **Decided by:** Afaq · **Model:** Claude Opus 5

Afaq's instruction: *"keep it on preview as a branch, it doesn't become prod
until I see it working."*

Vercel Authentication is on for this project, so a preview URL answers an
unauthenticated POST with **302 → `vercel.com/sso-api`**. Resend would follow
that to a login page and the route would never run. Measured, not assumed.

The fix is Vercel's **Protection Bypass for Automation**, whose documented
purpose is third-party webhooks that cannot set custom headers — Resend cannot.
The secret is appended to the webhook URL as `?x-vercel-protection-bypass=…`.
The bypass is labelled `Resend inbound webhook (Yunt)` in the project settings.

**This is temporary and must be removed at merge.** Production
(`milk-company.vercel.app`) is not behind the auth wall, so once this reaches
production the webhook URL loses the query string. A bypass secret left in a
production webhook URL is a credential sitting in a third party's config for no
reason.

**Rejected:** turning deployment protection off, which would expose every
preview of the client's dashboard to anyone with the URL.

---

## D-063 — One invoice and all of its lines are one database transaction

**Date:** 2026-09-09 · **Decided by:** Codex · **Model:** GPT-5.6

The ingest writer may create or update reference rows first, but an invoice and
every `invoice_items` row belonging to it cross the database through one
transactional RPC. If any line is invalid, the invoice and all lines in that
RPC call roll back together.

This closes a retry hole in the original Phase 3 wording. Separate PostgREST
upserts could insert an invoice, fail on a later line, then see the invoice as a
duplicate on webhook redelivery and skip the data that never arrived. Batch-id
deduplication does not repair a half-written business document; atomic document
writes prevent that state from existing.

The writer still preflights every row before its first write, defaults to dry
run, and never includes the generated `needs_review` column. Nothing here
authorises a live write: backup, dry-run evidence, and Afaq's explicit approval
remain mandatory.

---

## D-064 — Storage never waits for Yunt; every saved line gets a compact post-write review

**Date:** 2026-09-09 · **Decided by:** Afaq · **Model:** GPT-5.6

The deterministic path stores the invoice and classifier result first. Claude
being slow or unavailable may never cause an invoice to be lost. A successful
write is followed immediately by a Yunt review, and an unavailable review stays
eligible for a later attempt.

The Yunt reviews **all** saved lines, including auto-accepted ones, to catch a
plausible false positive. It does so token-efficiently: code groups repeated
normalised wording and sends counts, classification variants, confidence
ranges, counterparties, amounts and deterministic flags once per group. Exact
line identities remain outside the prompt and later seal any proposed action.

Email delivery is split by responsibility. The first email is the deterministic
reception report and does not wait for the agent. A second email is sent only
when Yunt has a finding or proposal: what it noticed, the evidence, and the
action it offers to take. No second email is sent when Claude is down, and no
suggestion changes a category without the existing approval/apply/undo path.

The second email is sent **without asking** — see D-065 for why that is not
a hole in the approval rule, and what makes it safe.

---

## D-065 — The findings reply is part of reception, not a new outbound action

**Date:** 2026-09-09 · **Decided by:** Codex, ratified by Afaq · **Model:** GPT-5.6

`agent/instructions.md` requires human approval before any tool that changes
company data, contacts another person, or creates an external effect. The
second email of D-064 would deadlock against that rule: the agent would finish
its review and then stop, waiting for a confirmation no one is watching for.

So the rule is narrowed, not waived. Approval is required to contact **another
person** or create a **new** external effect. Replying to the same allowed
sender who just sent the invoices is neither — it is the second half of an
exchange that person started, and D-064 already settled that it happens. After
the final packet reports `reviewCompleted: true`, the agent calls
`send_review_findings` once without asking.

The safety is in the outbox, not in the model's judgement. A trigger sets the
queued row `ready` only when flags or proposals exist and `suppressed`
otherwise, so a clean review sends nothing however the agent behaves. One
worker can claim the row; a second claim gets zero rows. The recipient is the
original sender read from the batch, never a value the model supplies. The
send carries a stable Resend `Idempotency-Key`.

**This does not extend to acting on a proposal.** Changing a category still
requires the approval/apply/undo path. That path now exists locally but is not
live until migration `014` runs; D-066 records its provenance value.

**Rejected:** letting the agent return findings to the webhook request and mail
from there. That request may not outlive the review, and a Resend or EVE retry
would then send the same findings twice.

---

## D-066 — A Yunt-applied category has its own provenance value

**Date:** 2026-09-09 · **Decided by:** Afaq · **Model:** GPT-5.6

When a person approves a Yunt category proposal and the apply tool performs the
change, `invoice_items.prediction_source` is `yunt_applied`. `user_selected`
remains only for a category the person selected directly in the dashboard.

Both values mean the settled category was not automatically accepted by the
classifier or deterministic pipeline, so neither belongs in the automatic-
accept KPI. Migration `014` adds the seventh allowed value before its apply RPC
can write it. Exact proposal, actor and prior-row provenance still live in
`yunt_applications` and `yunt_application_rows`; the source tag is the short
answer to “how did this row become settled?”, not the full audit trail.

**Rejected:** reusing `user_selected`. Approval is human, but execution is by
the Yunt, and Afaq wants those two operational paths distinguishable.

---

## D-067 — Email actions require an exact, structurally bound confirmation

**Date:** 2026-09-09 · **Decided by:** Codex · **Model:** GPT-5.6

Yunt V1 has no chat UI; its action channel is email. Before applying a category
proposal or undoing an application, a dedicated tool sends a code-generated
restatement for exactly one action and target. The action executes only when a
later inbound request matches that outgoing Message-ID, the same sender, the
same action and target, and has `CONFIRMO <one-use token>` as its entire first
line. Quoted email text below the first line cannot approve anything. The
database consumes the confirmation in the same transaction as the action, and
a retry of the same request is idempotent.

EVE's built-in approval pause is deliberately not used: it expects a channel
that can render an approval control, while V1 is email-only and would park with
nobody able to click. A generic reply is also insufficient; the previous code
accepted any `in_reply_to`, and the webhook even filled missing reply headers
with the opening message's own id. Both paths made “confirm first” a prompt
instruction rather than an enforced boundary.

---

## D-068 — An exact meter match outranks same-wording evidence

**Date:** 2026-09-10 · **Decided by:** Codex, from Afaq's correction · **Model:** GPT-5.6

`yunt_category_precedent` ranked historical lines by wording similarity alone.
Migration `025` adds a `same_meter` tier that sorts above it: when the line
being judged carries a `meter_code`, lines with the same normalised meter are
cited first, whatever their wording. The DTE's `<Transporte><Patente>` is
preserved as `invoices.transport_plate` in the same migration, so the petrol
plate/jerrycan rule in `CLIENT_CONVENTIONS.md` has a column to read.

**Why:** 29 item wordings looked like the client filing one thing under several
categories. Every one turned out deterministic — 23 wordings / 882 lines decided
by `meter_code` (different meters are different cost centres), 6 wordings /
625 lines by the plate. Wording similarity was searching the one field that does
*not* decide the answer. Measured on the fixed 400-line held-out run, confidently
wrong proposals fell 5.75% → 2.76%. See D-038 and D-040 — this is the same rule,
now enforced in SQL instead of trusted to a reader.

**Rejected:** filtering to same-meter rows only. A meter with no history would
then return no evidence at all; ranking degrades gracefully where a filter
returns nothing.

---

## D-069 — Recurring reports move to V2

**Date:** 2026-09-10 · **Decided by:** Afaq · **Model:** Claude Opus 5

Scope item 13 — the month-end summary, post-batch digest and weekly review list
— is parked for V2. `MCT-154` is in the backlog. A working first pass sits on
`milk-company` branch `yunt-recurring-reports-v2`: the cron config, both reports,
migration `026` for an on/off switch, a dashboard toggle and two agent tools.
None of it is on `yunt`, so a V1 deploy registers no cron and `026` stays unrun.

**Why:** the reports were built before anyone settled what they say, when they
run, or who receives them. Those are product decisions and every one of them was
guessed. Antillanca has not asked for the feature, the deterministic reception
email already tells Cristian a batch landed, and V1 still has unbuilt work that
was actually requested. Parking it costs nothing — the figures come from the
existing aggregate query and the PDF from `MCT-152`, so resuming is a matter of
answering the questions, not rebuilding.

**Rejected:** shipping it switched off. An unshipped feature cannot be turned on
by accident, and a `vercel.json` on the release branch registers its cron the
moment it deploys, whatever the toggle says.

---

## D-070 — The Yunt may change a category, never a value from the document

**Date:** 2026-09-10 · **Decided by:** Afaq · **Model:** Claude Opus 5

The only correction the Yunt can offer is the category of a line (and, if it is
ever wanted, which catalog item a line belongs to — Afaq called that "not that
important", so it is not built). An amount, quantity, date, item name or any
other figure that came off the DTE is never rewritten. When one of those is
wrong the Yunt reports it and offers nothing: Cristian decides whether it gets
fixed, and it gets fixed at the source.

This is already enforced structurally rather than by instruction, which is why
it is worth writing down: `yunt_proposals` allows a `data_fix` type, but
`apply_yunt_proposal` in `014` refuses it outright, and `review-persistence.ts`
hardcodes every stored proposal to `category_change`. **That refusal is the
decision, not an unfinished feature.** Do not "complete" it.

**Why:** the stored figures are what Antillanca filed with the SII. A copy that
silently disagrees with the filed document is worse than a copy with a known
error in it, because the error is at least visible to whoever compares them.
The review path already has the right shape for this — a `data_quality` finding
carries a severity and a reason and no action at all.

**Rejected:** rewriting the value with the original kept for undo. Undo makes it
recoverable, not correct; it still means our number and the SII's number differ
for as long as nobody looks. Also rejected: dropping the `data_fix` enum value,
which would need a migration against an applied one to delete a door that is
already locked.

---

## D-071 — Locale changes interface chrome, not Antillanca's business content

**Date:** 2026-09-10 · **Decided by:** Afaq · **Model:** Codex GPT-5

Switching the dashboard to English translates its interface labels, help text,
buttons, validation messages and navigation. It does not translate stored or
client-facing content. Invoice wording, supplier and item names, category names,
generated reception reports, purchase-order documents and downloaded filenames
stay in Spanish exactly as Antillanca owns or receives them.

**Why:** the language switch is for the person operating the interface. The
documents and business records still belong to the Spanish-speaking client, and
translating them would silently change their content rather than merely changing
the UI around it.

---

## D-072 — Direction comes from the RUTs; the folder is only a fallback

**Date:** 2026-09-10 · **Decided by:** Afaq · **Model:** Claude (Opus 5)

`COMPRAS` or `VENTAS` is decided by who is named in the document: Antillanca as
`RUTEmisor` is a sale, Antillanca as `RUTRecep` is a purchase. The
`COMPRAS/`/`VENTAS/` folder is consulted only when the document names Antillanca
on neither side. A document that names neither party and sits under no direction
folder is refused, and the reception report says exactly that.

This narrows [D-010], which made the folder the source of direction, and departs
from the signed V1 scope, which says the same. Afaq overruled both: *"the file
named based detection is not a good approach and can fail… i cant guarantee
they'll upload with this exact folder format."*

**Why:** the RUTs are inside the document and survive however the sender chose
to package it. A folder name is a human convention that a client can rename,
flatten or mix at any time, and doing so silently mislabelled every line in the
archive — direction is part of the model input template (D-013), so a wrong
folder is a wrong classification, not a cosmetic error.

**Measured before changing anything**, across the whole raw corpus:

| | |
|---|---|
| DTEs with both RUTs readable | 5,584 |
| Antillanca on **neither** side | **0** |
| Antillanca on **both** sides | **0** |
| Under a `COMPRAS`/`VENTAS` folder | 5,195 — the live invoice count |
| Folder rule and RUT rule **disagree** | **0** |

So this relabels nothing that is already stored. What it changes is what gets
*accepted*: an archive with a flat or differently-named folder used to be
rejected file by file as `no_direction_folder`. That rejection reason is gone.
Proved on the real screen: six documents in one flat `todo/` folder — four
purchases, two sales — were read and split correctly by `/carga`, with nothing
written.

**Rejected:** keeping the folder as the first choice and the RUTs as the
fallback. It needs a definition of a "garbage" folder name before it can decide
anything, and the folder is the less trustworthy of the two signals in the first
place.

## D-073 — `companies` holds counterparties, never Antillanca itself

**Date:** 2026-09-11 · **Decided by:** Afaq · **Model:** Claude (Opus 5)

The TypeScript ingest wrote a `companies` row for **both** parties on every
document, so it would have added Antillanca to a table that has never contained
it. It no longer does: our own RUT is skipped when the write is planned.

**Why:** an invoice links the *other* party — `companyRut` is the seller on a
COMPRAS document and the buyer on a VENTAS one — so a row for Antillanca is one
no invoice would ever reference, and it would appear as one of our own suppliers
in every list built from this table. Live carries **461 company rows and none of
them is Antillanca**, which is the meaning the old Python load established and
the dashboard's "Contrapartes" count still assumes.

This closes the question `STATE.md` had been carrying as waiting on Afaq. It is
one condition to reverse if a later feature genuinely needs both parties stored.

**Found by** uploading a one-document test batch through `/carga` and reading
the confirmation screen, which offered to create *two* suppliers for an invoice
with one.

---

## D-074 — "Proveedores nuevos" counts what does not exist yet

**Date:** 2026-09-11 · **Decided by:** Claude (Opus 5)

The upload confirmation screen showed the length of the whole upsert list, which
carries every counterparty in the batch whether or not it is already on file. A
month of invoices from entirely familiar suppliers would have announced dozens of
"new" ones on the screen you press Save from.

The upsert list itself is unchanged and still carries everyone, because the
upsert also refreshes names and seller/buyer roles on existing rows. Only the
number shown is now filtered against the companies already stored.

**Why:** a confirmation screen that overstates what it is about to create is the
same class of defect as D-001 — a display asserting something the data does not
say. `scripts/check-ingest-writer.ts` now pins both directions: the same batch
reports one new counterparty when it is unknown and zero once it is on file.

## D-075 — A flag's sentence is interface, not stored content

**Date:** 2026-09-11 · **Decided by:** Afaq · **Model:** Claude (Opus 5)

[D-072] and [D-071] split text by where it ends up: interface chrome follows the
language switch, stored and client-facing content stays Spanish. A quality flag's
`reason` and `suggested_action` fell on the stored side and so stayed Spanish in
the English dashboard, which made the English page unreadable in exactly the
place it mattered.

They are now re-stated by the interface in the reader's language. The stored
Spanish is untouched, because it is what goes to Cristian by email — that half of
D-071 still holds. The carve-out is narrow: **text we generate about our own
findings, addressed to whoever is reviewing, is interface** even when it happens
to be persisted.

**Why re-derive rather than store a translation:** `yunt_flags` keeps one row per
group per type, and four different amount checks collapse into `amount_anomaly`.
When several lines share one flag the stored reason describes only one of them
("N lineas. Por ejemplo: …"). The line itself carries every number the sentence
needs, so the interface names the condition on the row actually being displayed —
**more accurate than the text it replaces**, not merely translated.

The conditions are tested in the same order the ingest checks run, so the two can
never disagree about a row. A flag written by the model (`source = 'yunt'`) is
never re-stated: its wording is shown exactly as given.
`scripts/check-yunt-dashboard-flags.ts` pins each branch, the ordering, the
no-declared-total case, and the model-wording fallback.

**Rejected:** a `detail jsonb` column plus a backfill. It is the cleaner long-term
shape, but nothing needed it — the numbers were already on the line.

## D-076 — The Yunt reviews on Sonnet 5, high reasoning

> **Amended 2026-09-21 (D-115): reasoning is now `medium`.** The model choice (Sonnet 5) stands.

**Date:** 2026-09-11 · **Decided by:** Afaq

`agent/agent.ts` was `anthropic/claude-opus-5`. It is now
`anthropic/claude-sonnet-5`, reasoning unchanged at `high`.

Afaq's reason: *"there isn't deep math or reasoning to do here, just checking at
data or drafting mail or reports."* That agrees with what the file already
argued for its reasoning setting — **the agent computes nothing.** Every number
comes from a tool, and `submit_review_chunk` rejects any finding citing a
category or an evidence row it was not given. The work is reading, matching and
refusing.

`reasoning: "high"` stays, because the failure that costs something is a
confident wrong category or an invented purchasing fact, and that is what the
reasoning budget guards. Cost was never the argument for lowering it.

**Two places, and they must agree.** `agent/agent.ts` chooses the model;
`YUNT_REVIEW_MODEL` in `src/lib/yunt/after-write.ts` is stamped on each review
attempt as provenance. If they drift, a stored review names a model that did not
write it.

**What would reverse this:** review quality, not cost. Watch the first live runs
for a category proposal that cites evidence it was not given, a refusal it should
not have made, or a finding whose reasoning does not follow from the rows
attached. Any of those is a reason to go back to Opus — it is one line in each
file.


## D-077 — The Yunt runs on an Anthropic key, direct, not through the gateway

**Date:** 2026-09-11 · **Decided by:** Afaq

`agent/agent.ts` asks for `anthropic/claude-sonnet-5`, which is a **Vercel AI
Gateway** model id. Afaq has an Anthropic key (`sk-ant-…`) and nothing else. The
gateway will not accept it, so the agent moves to the direct path:
`npm i @ai-sdk/anthropic`, and `model: anthropic("claude-sonnet-5")`.

This is not only a plumbing choice. Billing and per-request usage then show up
in the **Anthropic console**, which is the one Afaq can actually read; through
the gateway they show up in Vercel. The whole concern behind
`docs/YUNT_TEST_PLAN.md` is not spending blind, so the readable console wins.

The model and the reasoning setting are unchanged — D-076 still holds, and
`YUNT_REVIEW_MODEL` in `src/lib/yunt/after-write.ts` must move with
`agent/agent.ts` exactly as it says. The stamped value becomes
`claude-sonnet-5`, without the `anthropic/` prefix, because that is what the
direct path actually calls.

The key lives on **Vercel**, not only in `.env.local`: the agent runs in the
deployment. It is added unflagged rather than sensitive, so a later session can
confirm it is there instead of reading `[SENSITIVE]` and guessing — the same
unreadability that made earlier docs claim `YUNT_ALLOWED_ADDRESSES` was unset.

## D-078 — eve's default tools are off

**Date:** 2026-09-11 · **Decided by:** Afaq

`defineAgent` in `agent/agent.ts` gets `defaultTools: false`. eve was giving the
Yunt eleven tools nobody here wrote — `bash`, `read_file`, `write_file`,
`web_fetch`, `web_search`, `agent`, `ask_question`, `todo`, `task_update`,
`task_cancel`, `load_skill` — on top of our 22.

Two reasons, and the second is the one that would have cost a paid run.

**`ask_question` deadlocks this agent.** It pauses the session so a channel can
render a prompt and a person can click. The Yunt's only channel is email, so
there is nothing to render and nobody to click: the session parks forever. This
is the same deadlock D-065 avoided for the findings reply and the reason
`apply.ts` uses a database-enforced confirmation instead of eve's `approval`
helper. Leaving `ask_question` reachable puts the deadlock back in by the side
door, and it looks exactly like a model outage from outside.

**`bash`, `write_file`, `web_fetch` and `agent` are an injection surface.** The
Yunt's input is email written by someone else. `agent/instructions.md` tells the
model that text is information and not instructions, which is mitigation by
prompt; removing the capability is mitigation by construction, and the second
kind does not depend on the model reading carefully. Nothing the Yunt is
supposed to do needs a shell, the filesystem or the open web — every fact comes
from a query tool (D-053).

Reversible in one line. If some later feature genuinely needs one of these, add
that single tool back as a file under `agent/tools/`, which is how eve's own
documentation says to do it.

## D-079 — The superseded Python `yunt/` is deleted

**Date:** 2026-09-11 · **Decided by:** Afaq

Ingestion lives in `../milk-company/src/lib/ingest/`. The Python `yunt/` in this
repo was the reference it was ported from, and the two have already diverged —
D-072 (direction from the RUTs) landed only in the TypeScript. Its 49 tests
still ran, which is precisely the problem: a green suite over code nothing calls
reads as reassurance.

Git history is the archive. Deleting it means `CLAUDE.md`'s standing warning
("`yunt/` here is the superseded Python reference and still exists … never port
logic out of it") goes with it, and the venv/test-command conventions that
mention `.venv-yunt` need the same pass — a doc that still routes people to a
directory that is gone is worse than the directory was.

## D-080 — Natural email requests are restated before any write

**Date:** 2026-09-11 · **Decided by:** Afaq · **Recorded by:** Codex (GPT-5)

D-067's structural safety remains: sender, email thread, action, target and
single use must all match. Its visible UUID-style confirmation code is replaced
by the natural exact first line `SÍ, ADELANTE` (or `YES, GO AHEAD` in English).
The binding stays hidden from the client in stored context.

Natural-language instructions — including selective changes, a category named
by the user and `Undo that.` — never write directly. The Yunt first sends a
short interpretation naming the affected records and the exact business
before/after state. Only the exact confirmation phrase on the resulting thread
may perform that stated action.

Client-facing reasoning uses accounting evidence: for example, how the same
concept was previously filed, or what the supplied document supports. It does
not mention model confidence, UUIDs, internal logs or database implementation.

## D-081 — The review batch is resolved from the conversation, not from one message id

**Date:** 2026-09-11 · **Decided by:** Claude · **Recorded by:** Claude (Opus 5)

The proposal lookup matched a reply's `In-Reply-To` against
`yunt_review_outbox.resend_message_id`. That column can hold Resend's **API
uuid**, while a reply quotes the **RFC Message-ID** — two different identifier
spaces that can never be equal. Measured on live on 2026-09-11: the lookup had
never once succeeded, and the one apparent success on 2026-09-11 was a manual
recovery script, not the agent. Resend can also answer a send before the
Message-ID exists, leaving a null hop mid-thread.

So resolution now walks the thread where the ids allow it, and otherwise falls
back to the newest **sent** findings mail addressed to this sender under the
same subject, with `Re:`/`Fwd:` prefixes stripped.

**The tradeoff, stated plainly.** The fallback is a heuristic. Two batches
mailed to the same person under the same subject would resolve to the newer
one. That is accepted for v1 because the confirmation step restates the exact
line and destination before anything is written, so a wrong batch is visible to
the client before it can do damage — and because the alternative, a lookup that
never works, is worse. Revisit if a client ever runs two open review threads
under one subject.

`resolveThreadReviewBatch` is the single place both the proposal listing and a
user's category correction resolve through; they had duplicated the broken
lookup. Guarded by `scripts/check-thread-batch-resolution.ts`, which fails
against the pre-fix code.

## D-082 — Safe refusal and one faithful log entry complete the refusal feature

**Date:** 2026-09-13 · **Decided by:** Afaq · **Recorded by:** Codex (GPT-5)

`MCT-153` is complete when the Yunt refuses an out-of-scope question safely and
records the user's original wording once. Reviewing later real refusals and
choosing a feature to build from them remains ordinary product discovery; it is
not a condition for closing this implementation ticket.

`MCT-165`, which checks whether an uploaded file looks like a genuine quotation,
remains in Backlog. V1 accepts a quotation recorded as a stated price in email,
and file inspection cannot prove that a supplier's claimed price is true.

## D-083 — Reports are deliverables, not data dumps

**Date:** 2026-09-13 · **Decided by:** Afaq · **Recorded by:** Codex (GPT-5)

`MCT-152` is not complete merely because its CSV, PDF and chart open with
correct data. A report sent by the Yunt must be a readable, presentable business
document: a real styled spreadsheet, a designed PDF, and a chart with an
intentional layout. The model chooses a supported query and output type only;
code owns all figures and the fixed document templates.

Implemented by D-093 (one document theme, charts inside the PDF) and D-094
(share charts are shares of the whole total).

## D-084 — A confirmation remains direct-reply-bound after Q&A

**Date:** 2026-09-13 · **Decided by:** Afaq · **Recorded by:** Codex (GPT-5)

An approval phrase is valid only as a direct reply to the code-generated
confirmation message. A same-thread reply after intervening Q&A must not reach
back silently to a two-message-old proposal. When the person asks a question
instead of approving, Yunt answers briefly and sends a fresh restatement of the
same change. The person can then reply directly to that fresh confirmation.

This is deliberate: it preserves a visible, exact before/after state at the
moment of approval and stops an ordinary “yes” from authorising an old change.

## D-085 — The quotation preflight must answer before confirmation

**Date:** 2026-09-13 · **Decided by:** Afaq · **Recorded by:** Codex (GPT-5)

For an order above CLP 500,000, fewer than two recorded quotations must be
reported before an order confirmation is requested. The same database constraint
remains the final authority at issuance. If that expected constraint is reached
while staging, the agent returns a structured `quotation_required` result and
asks for the missing quotation; it does not leave the email unanswered, split
the purchase, or offer a confirmation it cannot honor.

## D-086 — Recent prices suggest; the buyer chooses

**Date:** 2026-09-13 · **Decided by:** Afaq · **Recorded by:** Codex (GPT-5)

When a buyer selects an existing catalog item while creating a purchase request,
show its three newest recorded invoice prices beside Estimated budget. With a
valid quantity, show a one-click latest-price × quantity estimate. It is always
an explicit choice: typing a quantity, changing it, or selecting an item must
never replace a budget the buyer entered. Historic invoice price is planning
context, not a committed supplier price.

## D-087 — A reversible real sample for the team, with additive email access

**Sample part expired 2026-09-15:** Afaq had live restored to the full baseline,
so the five invoices are back and the ZIP is no longer unseen. A new unseen
test needs a fresh detach. The email-access part still stands.

**Date:** 2026-09-13 · **Decided by:** Afaq · **Recorded by:** Codex (GPT-6)

Afaq authorized backing up and removing a small set of existing invoices so
the team can email the original XML as unseen input. Remove complete documents
and their lines, not just lines (the invoice header would still deduplicate).
Keep the catalog and other precedent rows. The handover deliberately leaves
5 invoices / 12 lines absent, with a full 23-table snapshot and a proved exact
restore. This tests ingestion, not held-out model generalization. One volunteer
sends the ZIP; subsequent sends are duplicates. After team testing begins,
cleanup must name that run's exact records instead of assuming all Yunt-created
purchases are disposable.

Email access includes `cristian.anguita@gmail.com` and the exact
`@mctechstudio.com` domain. The original sensitive Preview allowlist cannot be
read back, so an additive variable preserves it and the shared inbound/outbound
gate combines both lists. Domain matching excludes subdomains and lookalikes.
Dashboard accounts remain a separate access mechanism.

## D-088 — A recent, explicitly selected historical purchase may be repeated

**Date:** 2026-09-14 · **Decided by:** Afaq · **Recorded by:** Codex (GPT-5)

The normal purchase-request confirmation remains the first email step. If the
buyer subsequently explicitly selects an exact historical catalog item,
supplier, unit and unit price from the last six months, the Yunt may offer a
repeat instead of requiring two new quotations above CLP 500,000. The repeat
confirmation states the supplier, RUT, rate, quantity, delivery date, cost
centre and historical category. Its exact confirmation atomically creates the
request and the linked order, then closes the request; it never contacts the
supplier.

This is a narrow exception to D-052, not a change to the normal two-quotation
rule. A similar item spelling is only a suggestion until the buyer expressly
chooses the named historic catalog item. The database independently checks the
six-month source, supplier RUT, unit and rate. A changed repeat creates a fresh
pending draft, invalidating the old confirmation rather than allowing it to
approve different details.

## D-089 — Requests are the open-work queue; orders own their history

**Date:** 2026-09-15 · **Decided by:** Afaq · **Recorded by:** Codex (GPT-5)

Purchase Requests shows open work only. It keeps an explicit Purchase Orders
navigation control, but does not duplicate generated orders. Purchase Orders
owns the generated-order list and its issued-month, supplier, and category
filters. Removing redundant content must not remove the route that users rely
on to reach its dedicated screen.

For a new request, every visible field is required except detailed description;
an uncatalogued free-text item remains allowed. On a known item, historic
category chips come only from prior purchase invoices and selecting one fills
the PO category without altering historic data. The form and server action
require a category, while the database-level non-null category constraint is
parked for now rather than introduced as a migration.

## D-090 — Numbers read the Chilean way in both UI languages

**Date:** 2026-09-15 · **Decided by:** Afaq · **Recorded by:** Claude (Opus 5)

Amounts and counts are the client's data, so they are formatted `es-CL` whether
the UI is Spanish or English: `4.192`, `$9.259.812.345`, `9,8%`, and `$9.260 MM`
for millions in tight spaces. Only labels translate. One formatter
(`NUMBER_LOCALE` in `src/lib/dashboard/format.ts`); bare `toLocaleString()`
followed the browser's language and is not used for figures.

**Why:** plain `es` prints `4192` and `9.259.812.345 CLP`; English `$9.26B`
reads as *billón* (a trillion) to a Chilean. The purchasing pages already
hard-coded `es-CL`, so one rule removed a split.
**Rejected:** following the UI language — two formats for the same figure.

## D-091 — Pastizal theme with a framed layout

**Date:** 2026-09-15 · **Decided by:** Afaq · **Recorded by:** Claude (Opus 5)

Moss sidebar `#1F2A22`, oat page ground `#F5F3EC`, white cards and controls,
sage `#3E7B4F` only for primary actions / current page / focus, wheat `#C8963E`
only for the headline KPI. Table header rows are moss with centred titles; the
frozen first column stays oat; scrollable cells stay white. Tokens live in
`src/app/globals.css`. Generated documents copy these colours as hex in
`src/lib/documents/theme.ts` (D-093); change both together.

**Why:** the stock greyscale read as bland, and colour alone on white was not
enough — structure (dark frame, tinted headers, cards on a tinted ground) is
what made it read designed. Earthy fits a dairy/farming client.
**Rejected:** navy + trust blue (generic), Arcilla, Petróleo, Tinta palettes.

## D-092 — Layout responds to the space beside the sidebar

**Date:** 2026-09-15 · **Decided by:** Afaq · **Recorded by:** Claude (Opus 5)

Filter rows, the KPI grid, KPI figures and the header title size themselves with
container queries on their own area, not viewport breakpoints. Narrow areas
collapse filters behind one "Filtros" toggle that opens an even 2-column grid;
the header uses icon-only language/role pickers below tablet width and shows
the title only when it fits (the open sidebar already shows the name).

**Why:** viewport breakpoints treated a 900px window with the sidebar open as
desktop, which stacked filters and cut KPI figures.
**Rejected:** more viewport breakpoints — they cannot see the sidebar.

## D-093 — Every Yunt document shares one theme, and charts live inside the PDF

**Date:** 2026-09-15 · **Decided by:** Afaq · **Recorded by:** Claude (Opus 5)

Report PDFs, chart reports, spreadsheets and the purchase-order PDF read one
file, `src/lib/documents/theme.ts`, whose colours are the Pastizal tokens
(D-091) as hex, drawn with a small dependency-free PDF canvas
(`src/lib/documents/pdf.ts`). A chart request returns a report PDF — header,
criteria, summary tiles, the chart, the detail table — never a loose image
file. The purchase order stays mostly black and white so it prints cleanly for
suppliers, with the theme's sage-deep only on its rule and labels, and matches
the print page. Criteria print in Spanish words, never parameter names or query
mechanics. The model still chooses only the query and output type (D-053, D-083).

**Why:** Afaq's review of the delivered files: plain text on a page, an
unformatted sheet, and "a graph thrown in an SVG" read as data dumps, and the
emailed order did not look like the order on screen. Outlook does not preview
SVG at all.
**Rejected:** a headless browser or PDF library (weight inside the Vercel
function for what a few hundred lines draw); PNG charts (needs a rasterizer and
still arrives as a loose image); a Pastizal-coloured purchase order (prints and
photocopies badly for suppliers).

## D-094 — A pie or stacked chart shows shares of the whole query

**Date:** 2026-09-15 · **Decided by:** Claude (Opus 5), after a live test Afaq ran

Shares and the donut centre use the query's own total. When more groups exist
than fit (10), the top 9 are drawn and everything else is one "Otros (N grupos)"
slice, with a line saying so; the detail table still lists every group. Share
charts are refused for measures that do not add up (average, min, max, distinct
documents), so the model picks another chart type.

**Why:** the first live pie of 2025 purchases by category drew 10 of 69 groups
and computed each share of those ten: "Sin categoría confirmada 24,3%" was
really 17,1%, and the centre showed $2.841 MM against a real $4.029 MM. A share
of a subset read as a share of the whole is a wrong number on a client document.
**Rejected:** keeping the "Se muestran 10 de 69" note alone — the percentages
beside it still read as shares of everything.

---

## D-095 — Every category is trained; a deterministic rule is an add-on, never a replacement

**Date:** 2026-09-15 · **Decided by:** Afaq · **Model:** Claude Opus 5

The model gets every live category it has gold rows for, including the six added
on 2026-08-14/17 and the ones a lookup already settles. Afaq's words: *"the ML
model always have all the categories, we don't exclude any category just because
it can be sorted by some deterministic pattern, that pattern is just an add on,
it's not a replacement."*

v1.4.0 trains **73** classes against v1.3.3's 67. `AF-1.1` (108 distinct inputs),
`AF-2.1` (13), `ADM-2.3` (16), `ING-0.7` (6) and `ING-0.6` (3, synthetic floor)
are now predictable; `ADM-1.9` trains on 1 real row plus 2 D-005 synthetic rows.
`ADM-3.1`, `EXP-15.7` and `EXP-15.8` have **0 gold rows** and are still
rule-only — live has 43, 14 and 158 lines under them, so they are the obvious
next harvest into gold.

**Why:** a rule covers the wordings it was written for. The model is what
generalises to the next wording, and a category it cannot emit is a category
the model can only ever get wrong. Measured on the locked test set, the 29 rows
in unemittable categories went from all-wrong to `AF-1.1` recall 1.00.

**Narrows D-028**, which deferred these categories to "a later retrain". This is
that retrain. The order of the cascade is unchanged: fuel, meter, exact phrase
and product lookups still answer before the model.

---

## D-096 — The familiarity gate ships at k=5 for v1.4.0

**Date:** 2026-09-16 · **Decided by:** Afaq · **Model:** Claude Opus 5

`scripts/75_calibrate_familiarity_gate.py` swept k and agreement on the v1.4.0
weights and selected **k=5, agreement 0.40** over 1,903 indexed training rows.

Of 177 model-only auto-accepts on the locked test set (171 right, 6 wrong):

| Setting | Correct auto-accepts lost | Wrong ones caught |
|---|---|---|
| **k=5 / 0.40 (shipped)** | **0** | 1 of 6 |
| k=10 / 0.40 (D-019) | 4 | 2 of 6 |

**Why:** k=10 buys one extra catch for four correct auto-accepts, on a model
whose remaining mistakes are near-misses inside a family (`MANGA DE LECHE`
EXP-10.3 → EXP-10.1; `Revision Tecnica Maquinaria` EXP-13.1 → EXP-13.3) that no
neighbourhood vote can separate, because genuine neighbours sit in both classes.

**Supersedes D-019.** The gate itself is unchanged and still only downgrades;
what changed is the neighbourhood size, re-measured on new weights. Recalibrate
on every retrain rather than carrying a number forward.

---

## D-097 — INT8 ships for v1.4.0 with the top-1 ceiling raised to 9%

**Date:** 2026-09-16 · **Decided by:** Afaq · **Model:** Claude Opus 5

The export gate refused at its 7% default. Measured INT8 against the FP32
reference on the 466 locked test rows: top-1 disagreement **8.80%** (41 rows),
threshold-decision disagreement **1.72%** (8 rows), cosine mean 0.9929,
accuracy **0.6931 → 0.6974**. Afaq raised the top-1 ceiling to 9%; the
decision ceiling stayed at 5%.

**Why:** Cloud Run is 2 GiB / 1 CPU on the free tier and FP32 peaks at 1.92 GiB,
so INT8 is the only thing that fits. The trade is better than the one v1.3.3
shipped with (6.41% top-1, **4.81%** decision flips, accuracy 0.7532 → 0.7468):
more first picks move, far fewer auto-accept/review decisions flip, and accuracy
does not drop. Both ceilings are stamped into `model_card.json`.

**Rejected:** shipping FP32 (does not fit), and lowering the accepted
disagreement by re-quantising per-channel (untried, and the decision-level
number — the one that reaches the dashboard — was already inside its ceiling).

---

## D-098 — One locked split, reused by every model compared on it

**Date:** 2026-09-15 · **Decided by:** Claude Opus 5, confirmed by Afaq

`scripts/100_build_retrain_candidate.py` writes `split.csv` once and every
candidate reads it with `--split-from`. Rules baked into it:

- v1.3.3's 312 validation inputs stay **test**; its training inputs stay
  **train**. So the old model and every new one are scored on rows none of them
  trained on, and the comparison is like-for-like.
- 20% of each class's new inputs join the test set; classes under 5 distinct
  inputs are train-only and are listed as untested (6 of them).
- Synthetic rows (D-005) and plate-conflict rows (D-029) are never test rows.
- The build fails if any test input also appears in train.

Direction, absent from 2,508 of 2,577 gold rows, is recovered from the raw XML
line where one matches (1,606 rows, **0** disagreements with the category family)
and from the `ING-`/expense family otherwise. The build stops if the two ever
disagree.

**Why:** without a locked split, every retrain is scored on a different exam and
the comparison means nothing. Verified: replaying v1.3.3 on its own original
rows through `scripts/101_evaluate_retrain.py` reproduces its recorded 0.7532
accuracy and 0.8654 top-3 exactly.

---

## D-099 — Training data is gold **plus** every settled Supabase label, by trust order

**Date:** 2026-09-16 · **Decided by:** Afaq · **Model:** Claude Opus 5

v1.4.0 was trained from `Data/gold/_master_gold.csv` alone. That was wrong:
gold is one lineage of the labelled set, and live carried 6,842 more settled
lines, including the only examples that exist for `ADM-3.1`, `EXP-15.7` and
`EXP-15.8` (215 lines, 0 gold rows). Afaq: *"the whole point of retraining was
that I have more labels now and you still kept some categories undertrained
which clearly had lines in the db."*

`scripts/102_merge_live_labels.py` merges both. Trust order, highest first:

| Source | Why it ranks there |
|---|---|
| `user_selected` | a person at Antillanca chose it in the dashboard |
| gold | audited into `Data/gold/` per `docs/LABELING_RULES.md` |
| `cleanup` | our audited passes applying client conventions |
| `business_rule` / `product_lookup` | exact client phrase and product rules |
| `meter_lookup` | decided by the meter, not by the text (D-068) |

**Refused:** 982 `model` auto-accepts — the model's own guesses, measured at
0.698 auto-accept precision, so feeding them back teaches roughly a third of its
own mistakes — and 103 DTE-43 liquidación lines, which have no client category
(D-016 lineage). Where one model input carried two labels: 167 resolved by trust
order, 15 dropped as ties the text genuinely cannot settle, and the D-029 plate
pairs kept one per label.

Result: **4,251 distinct model inputs across 76 classes**, against v1.4.0's
2,369 / 73.

**The local mirror of live is `backups/yunt_team_handover_20260913/`** — verified
identical to live, row for row, on 2026-09-16. The obvious-looking local file,
`reports/recovery_v1_3_3/supabase_upload/invoice_items.jsonl`, is **stale**:
7,335 settled rows against live's 7,927, still using the pre-D-047 source names.
Use the backup, or read live; never that payload.

**Why not write these rows into gold:** `docs/LABELING_RULES.md` forbids
promoting an unaudited row, and a rule-assigned line is not an audited one. The
merge therefore happens in the training candidate, where provenance stays
visible in `source` (`live_cleanup`, `live_business_rule`, …), and gold keeps
its meaning.

---

## D-100 — The category name list is rebuilt from the live `categories` table, and a test holds it there

**Date:** 2026-09-16 · **Decided by:** Afaq · **Model:** Claude Opus 5

`Data/current_context_2026_06_30/taxonomy_from_plan.csv` is what
`training/export_recovery_onnx.py` turns into the artifact's `taxonomy.json`,
which is the only place a category's human-readable name lives. It still held
the **71** categories of June while live held **78**, so every artifact since
August shipped a name list missing `ADM-3.1`, `AF-1.1`, `AF-2.1`, `EXP-15.6`,
`EXP-15.7`, `EXP-15.8` and `ING-0.7`. `/predict` returned the right code with
`name: ""`, and the dashboard would have rendered a blank category to Antillanca.

All seven were added with the names copied from live and verified: 78 codes,
0 missing, 0 name mismatches. Re-exported with the same weights — the image tag
became `v1.4.1-names` while the model version stayed **v1.4.1**, the same way
`v1.3.3-plate` worked.

**The second gap this exposed is the more interesting one.**
`tests/test_transaction_rules.py::test_every_sales_taxonomy_name_is_a_rule`
asserts that every `ING-` leaf name resolves through
`app/data/business_rules.csv`. It had been passing only because the taxonomy it
read was stale: `ING-0.7` had no rule, so a sale line literally named
`VENTA DE ACTIVO FIJO` fell through to the model, where 6 examples put it on the
weak list and into review. Four rules were added (canonical, singular, and both
without "de"); live now answers `ING-0.7` by `business_rule`.

**Why the exact-name rule is sales-only:** on a sale the client writes the
invoice, so an item naming a category is the client naming their own category.
On a purchase the supplier writes it and a match is a coincidence in someone
else's document.

**Rule:** when a category is created, it lands in the live table, in this CSV,
and — if it is a sales category — in `business_rules.csv`, in the same change.
The test asserts 78 categories and 7 sales leaves, so the next drift fails
before it ships.

---

## D-101 — The Yunt uses Vercel AI Gateway; this supersedes D-077

**Date:** 2026-09-17 · **Decided by:** Afaq · **Model:** Codex

Rodrigo confirmed that the expected provider path is the Mountain Creative
Vercel AI Gateway, whose Anthropic provider and billing are already configured.
The deployment therefore uses `AI_GATEWAY_API_KEY`; it does not use a direct
Anthropic key for ordinary Yunt calls. D-077 was the best decision under the
information available then, but is no longer current.

With eve, the model identifier is the provider/model string
`anthropic/claude-sonnet-5`. Do not add a `gateway/` prefix and do not wrap it
with `gateway(...)`: that produced an eve build failure because the compaction
compiler saw `gateway/anthropic/claude-sonnet-5` as an unknown Gateway model.
`agent/agent.ts` and the stored `YUNT_REVIEW_MODEL` provenance must still agree.

**Credential rule:** create a scoped AI Gateway API key in Vercel, put it in
the deployment as `AI_GATEWAY_API_KEY`, and use the same variable locally when
needed. Never pull sensitive Vercel variables over a working `.env.local`; the
CLI cannot reveal their values and writes `[SENSITIVE]` placeholders.

---

## D-102 — Canonicalise units and validate numeric corrections at ingestion

**Extended by D-104** (all units, code map) and **D-103** (credit notes, extra taxes, document discounts, flag-not-fix).

**Date:** 2026-09-17 · **Decided by:** Afaq · **Model:** Codex

Reports aggregate the structured rows already stored in `invoice_items`; they
must not rediscover data cleanup rules independently. During DTE parsing, every
known litre spelling (`L`, `LT`, `LTR`, `LITR`, `LTS`, `LITRO`, `LITROS`, case
insensitive) becomes `L` before classification or storage. This keeps future
reports in one physical-unit bucket.

D-056 still governs scale correction. Correct source arithmetic is accepted
unchanged before the supplier-specific candidate is considered. A line is
rescaled only when the original calculation fails and the known corrected
calculation reconciles to `MontoItem`; otherwise it remains unchanged and is
flagged. Supplier history proposes the otherwise-underdetermined split between
quantity and price, while arithmetic proves whether that proposal applies to
this line.

Migration `031_repair_scaled_invoice_lines.sql` applied the same rule to stored
history: 212 proven lines repaired, 383 historical litre aliases canonicalised,
and originals retained in `yunt_invoice_item_scale_repairs`. Raw uploaded
ZIP/XML files are currently not archived by the app; only cleaned relational
rows and batch metadata are durable.

## D-103 — Supplier numbers are stored as received; arithmetic flags, never rewrites

**Date:** 2026-09-17 · **Decided by:** Afaq · **Model:** Claude Opus 5

Every total is computed from the fields exactly as the DTE defines them:
- a credit note (DTE 61) counts as negative in every spend figure, as SII's purchase register does;
- additional taxes (`ImptoReten`: fuel excise 35/28 and others) and document-level discounts or surcharges (`DscRcgGlobal`) are stored, and are part of the reconciliation.

Where a supplier's own numbers still disagree with themselves, the invoice is kept exactly as sent and flagged "no cuadra según proveedor", with the expected and received values. The D-056/D-102 scale correction stays the only automatic numeric fix. The only allowed cleanup of supplier wording is replacing placeholder names ("Item", "Detalle") with the description.

**Why:** The 2026-09-17 audit found that most apparent errors were terms we never stored, not supplier mistakes: 1,246 header gaps from unstored extra taxes, 473 line-sum gaps from unstored document discounts, and BIOLACT "outliers" that were really credit notes. Correcting supplier data to force a match would take responsibility for, and risk damaging, invoices that are actually fine.
**Rejected:** Auto-correcting non-reconciling invoices — it cannot tell a supplier mistake from a term we don't store. Tickets: MCT-171 (175, 176, 177, 187), MCT-179, MCT-188.

## D-104 — Every unit spelling maps to one standard unit through a fixed map in code

**Date:** 2026-09-17 · **Decided by:** Afaq · **Model:** Claude Opus 5

Extends D-102 from litres to every unit (UN, KG, M, KWH, …). The map lives in code, not in a database alias table. It is applied at ingest and wherever units are read, so older rows group correctly without a rewrite. Spellings not in the map are kept as sent and listed so they can be added. Price outliers per item and standard unit are flagged, never corrected, and credit notes are excluded (D-103).

**Why:** Units are a closed, deterministic vocabulary; a table adds a fetch and a place to drift. 32% of lines carry no unit and "each" arrives in ~15 spellings.
**Rejected:** An alias table in Supabase. Tickets: MCT-178, MCT-188.

## D-105 — Purchasing item search matches invoice wording, not the canonical catalog name

**Date:** 2026-09-17 · **Decided by:** Afaq · **Model:** Claude Opus 5

The canonical `item_catalog.item_name` (D-044) is for display only. Purchase-request search runs over the distinct invoice `item_text` wordings, returns the exact wording, and carries the catalog item it belongs to.

**Why:** Repeat orders must use the wording the supplier invoices under, or they cannot be matched back to that supplier's history. "G93" (78 lines) returned nothing because it only exists under the catalog name "Gasolina 93".
**Rejected:** Adding more aliases to the catalog search. Ticket: MCT-184.

## D-106 — Analítica figures are computed on the server by the existing TypeScript, cached on a database change stamp

**Date:** 2026-09-17 · **Decided by:** Afaq (via MCT-182 scope) · **Model:** Claude Opus 5

The dashboard's aggregation functions run on the server over the same filtered rows the browser used to hold; only each tab's result is sent. Results are cached in Next's data cache keyed on `analytics_version.changed_at`, a one-row stamp that statement-level triggers (migration `036`) move on any write to `invoices`, `invoice_items`, `categories`, `companies` or `item_catalog`. Productos reuses the same stamp for its memoised summaries. No code path has to remember to invalidate.

**Why:** Re-implementing ~1,500 lines of figures in SQL would let them drift from what the screen showed; reusing the code made every tab text-identical before and after. A tag-invalidation call in each writer missed writes made outside the app (SQL editor, Yunt agent steps) and a self-generated version stamp flipped under stale-while-revalidate.
**Rejected:** SQL grouped-totals per chart; `revalidateTag` from every writer; a version generated inside `unstable_cache`. Tickets: MCT-182, MCT-183.

---

## D-107 — Both doors accept loose DTE XML files, one or many, as well as ZIPs

**Date:** 2026-09-17 · **Decided by:** Afaq · **Model:** Claude Opus 5

A classification job can start from any mix of ZIPs and loose `.xml` files, by
email or on `/carga`. One reader (`readFiles` in `src/lib/ingest/batch.ts`) opens
both; a loose XML has no folder, so its direction comes from the RUTs, which is
the rule anyway.

- **Email:** every ZIP and XML attachment of one message is **one batch** — one
  reception report, one review — claimed by the Message-ID, falling back to the
  Resend email id when a message has none (a shared blank claim would have made
  every later such message look already processed). An XML sent with a bare
  filename and an XML content type is still read as XML.
- **`/carga`:** the picker takes several files; when more than one is chosen the
  **browser packs them into one ZIP** before upload. A month of loose XML is
  2.5–4 MB, at Vercel's 4.5 MB request cap; zipped it is ~10x smaller. Entry
  dates come from the files, so re-picking the same files builds the same bytes
  and claims the same batch.

**Why:** Afaq, top priority: the endpoints must take XML "as is", not only ZIP.
**Proof:** a real month (388 documents, 902 lines) read as loose XMLs matches the
ZIP read document for document and direction for direction
(`scripts/check-ingest-batch.ts`); signed-in `/carga` dry run with three real
XMLs showed 1 new, 2 already registered, classified, nothing saved.
**Rejected:** one batch per attachment (several reports and reviews for one
email); sending raw files from the browser (hits the request cap for a month);
PDF intake — deferred by Afaq, likely agent-prepared, not deterministic parsing.

---

## D-108 — Yunt gates writes when available; ML-only may write with a complete audit trail

**Date:** 2026-09-17 · **Decided by:** Afaq · **Model:** Codex

One Next.js orchestrator owns invoice intake from email and `/carga`. After XML
parsing and data-quality checks, it runs the exact product, meter, fuel and sales
accounting rules locally. Lines settled by those rules stay settled; only the
unresolved lines go to the Cloud Run classifier. Results are merged one-to-one
by stable input id, and a missing or duplicated result aborts the whole batch.

The availability contract is:

| Available | What happens |
| --- | --- |
| ML + Yunt | Yunt reviews the complete proposal before write. Show the full report, require client confirmation, then commit once. |
| ML only | ~~Commit the deterministic + ML result immediately~~ **Replaced by D-114 (2026-09-21): nothing is saved.** The job ends failed and the sender is asked to retry. The old behaviour survives only behind `YUNT_ALLOW_ML_ONLY=1`. |
| Yunt only, at most 10 unresolved lines | Yunt may suggest the unresolved categories with full client, taxonomy and precedent context. Show the full report, require confirmation, then commit once. |
| Yunt only, more than 10 unresolved lines | Save nothing and ask the user to retry later. |
| Neither | Save nothing and ask the user to retry later. |

The ten-line limit is counted **after** deterministic resolution. If a rejected
batch contains cheaply resolved lines, those results are discarded too; rerun
the cheap rules later instead of maintaining partial recovery state.

Whenever Yunt participates, confirmation is required even when it agrees with
ML. No invoice, invoice-item or final classification rows become business truth
before that confirmation. Because an email reply can arrive hours later, the
exact prepared write plan, report hash, authorized sender/source identity and
one-use confirmation token live in one durable staged-approval record. This is
not an outage queue: it has no cron, automatic retry or delayed dashboard result,
and it closes on approval, rejection or expiry. Approval commits atomically and
idempotently; duplicate uploads or replies cannot import twice.

The client sees every line: document, supplier, wording/description, quantity,
unit, unit price, amount, proposed category, decision source, review status and
Yunt reason/flag. Email prefers an inline table through 25 lines and uses XLSX
above that with a concise inline summary. The dashboard shows the same report.

Yunt fallback is not an ungrounded second classifier. It gets the category guide,
client conventions, precedents and read-only lookup/evidence tools needed for an
informed suggestion; it must surface ambiguity rather than claim certainty. The
extra tools are visible only in a server-issued `ml_fallback` session and every
executor independently rejects other modes. A process-global boolean is unsafe
under Vercel concurrency and is forbidden. Ordinary ML-review sessions do not
receive these fallback tools.

The deterministic rule source moves to Next.js, but the Cloud Run cascade is not
deleted until its direct callers have migrated and parity tests prove identical
answers. This decision supersedes D-064's unconditional post-write review: when
Yunt is available it reviews before write and gates confirmation. D-064's
availability principle survives only in the explicit ML-only row above.

**Why:** Yunt can catch an ML mistake before it is logged, but an ML outage need
not stop a small, well-grounded batch. Simultaneous outages are rare and do not
justify a hidden pending queue, cron, partial imports or a dashboard result that
appears after the user has left.

**Rejected:** always writing before Yunt reviews; using Yunt for more than ten
unresolved lines; retaining partial deterministic successes; retrying outage
batches later; exposing fallback tools during ordinary review. Ticket: MCT-189.

**Amended 2026-09-18 by Afaq, while implementing it.** Five points, each
replacing what this entry said above:

1. **A staged approval never expires.** It closes on approval or rejection only.
   Re-sending the same files returns the pending proposal rather than opening a
   second one, so nothing is left unreachable by the expiry rule this entry
   originally carried.
2. **One email per job, not two.** The reception acknowledgement is gone with
   the post-write path: what goes out is the proposal, the audit report of a
   saved ML-only job, or "the system is down, send it again later".
3. **The client's copy never names the engine or its confidence.** D-108's
   column list included decision source and review status; both are stored and
   shown in the dashboard, and neither is mailed. Telling the client which
   engine settled a line, or how sure it was, is a map of where the model is
   weak. The email reads as three groups instead: confirmed, the Yunt's
   suggestions, and what needs a person.
4. **A waiting job is approved by replying to its email or from the dashboard
   (D-111).** It was first "one job, one channel": an emailed job could only be
   answered by email and an uploaded one only on `/carga`. D-111 (2026-09-21)
   lifted that. Both channels answer the same stored proposal, bound by its hash,
   so a per-line change asked by email is what the dashboard shows next.
5. **Every line of an approved batch is written `yunt_applied`.** No new
   provenance value: `014` already allows it and `aggregate.ts` already excludes
   it, so the automatic-accept figure reads 0% for new batches and keeps its
   meaning for the stored history. What the model proposed stays in
   `predicted_code`.

6. **Amended 2026-09-21 (D-114): "ML only" no longer saves.** A Yunt that is down, out of
   credit or not finished in time never causes a write.

**Also settled here:** Yunt liveness is read, never poked. A job waits ~4
minutes, then READS the review session's event stream; re-sending the job would
start a second review once the first is terminal, and a follow-up message would
cancel a turn that is still working. A mid-run death (credits, provider) is
caught by a hook on `turn.failed` / `session.failed`, which is the only thing
that can see it. The person who sent the invoices is told; nobody else is.


## D-109 — The glassbox shows the client the current state of every case, read-only, from what is already stored

**Date:** 2026-09-21 · **Decided by:** Afaq · **Model:** Claude

MCT-190. Three read-only views over data the Yunt already keeps, so the process
is visible instead of only its result.

1. **Client-facing, so D-108 applies to the page.** A line carries no decision
   source, no engine and no confidence; the page type cannot hold them, and the
   model's reason passes through `colleagueText` again at the page boundary
   because rows stored before 2026-09-19 still carry confidence talk.
2. **Current state only.** A line shows its category now — confirmed, suggested or
   needs review — never the history of corrections. A saved job shows accepted
   suggestions as confirmed.
3. **Live without a timer that never sleeps.** The page refreshes every 5 seconds
   only while a job is `processing`, `reviewing` or `awaiting_approval`, and once
   when the tab becomes visible. A settled list makes no requests.
4. **Email stays the only conversation.** Threads are shown read-only. Any waiting
   job can also be approved or discarded from its page (D-111).
5. **Where each lives.** Jobs: history under the upload form, `/carga/[id]`.
   Purchase: one page per request, the order is a stage of it; its emails are
   found through the request and order drafts' `source_request_id`, with no new
   column. Reports: `/informes`, backed by `yunt_reports`.
6. **Reports store the question and the data, not the PDF.** The PDF is a pure
   function of title, chart type and data and is drawn again on open. The write
   is best-effort, before the mail goes: a failed audit copy must not fail a
   delivered answer. The writer lives in `report-store.ts`, which imports nothing
   from Next, because the agent loads it.
7. **All reads are as the signed-in user through RLS.** `039` and `040` grant
   `select` only; the service key is never used by a page.


## D-110 — A confirmation is tied to the conversation, not to one email

**Date:** 2026-09-21 · **Decided by:** Afaq · **Model:** Claude

Amends D-108 point 4 ("an emailed job is approved only by replying to that email").
The confirmation gate, `consume_yunt_action_confirmation`, checked only the message
a reply answered. A person who did not type the phrase got a plain answer from the
Yunt, replied to *that*, and was refused as "a different action or target" — the
only way out was to find the first email. Afaq: the client must never have to go back;
the context of the proposal being discussed must be kept.

1. **The gate follows the thread upward** to the *nearest* message carrying a
   confirmation and checks that one (migration `041`). Sender, action, target, the
   exact phrase and single use are unchanged. Nearest wins, so a revised proposal
   supersedes an older approval.
2. **The database, not the model, judges the phrase.** It ignores capitals and
   accents. The Yunt must not refuse a reply for its wording, and must not ask the
   person to find an earlier email.
3. **Two channels per waiting job** (D-111): the email thread, or the job's page on
   the dashboard. The thread stays the only conversation.

## D-111 — Any waiting job can be approved from the dashboard, after seeing the proposal

**Date:** 2026-09-21 · **Decided by:** Afaq · **Model:** Claude

Replaces the "one job, one channel" rule of D-108 point 4 (Afaq, 2026-09-18), which
let only the sender approve an emailed job.

1. **Every job in *awaiting approval* shows Approve and Discard on its page**, and on
   `/carga` right after an upload, whichever door it came through.
2. **Approve opens a dialog first.** It lists the proposal grouped by category, with
   each line and amount and the lines still marked *Need review*, and only "Yes, save"
   commits. The proposal shown is the latest stored for the job — the one the email
   thread is currently about, since a change asked by email rewrites it in place.
3. **You approve exactly what you saw.** The request carries the proposal's hash; if it
   changed while the dialog was open the server answers 409 and the page reloads. The
   endpoint refuses an approval that names no hash.
4. **The database still guards the write** (migration `042`): the hash binding, the
   single commit and the one-use email confirmation are unchanged; only its two refusals of a
   signed-in user on an emailed job are gone. Any signed-in user may answer (D-052).
5. **Whichever channel comes first settles it.** A later `SÍ` finds the job already
   saved and changes nothing.

Not decided: telling the email's sender when someone else approved on the dashboard.
Nothing is sent today.

## D-112 — The Yunt may suggest a category from context when there is no precedent

**Date:** 2026-09-21 · **Decided by:** Afaq · **Model:** Claude

Relaxes the batch-review rule that a suggestion had to cite a precedent it retrieved.

1. **With precedent, cite it. Without, reason from everything the line carries** —
   wording, description, supplier and what they sell, unit, amounts — read against
   `agent/category-guide.md`, and say in the reason that there is no earlier filing and
   what points to the category. Reasoning is never presented as precedent.
2. **Only when an accountant would land on the same category** without knowing the
   business. Anything that depends on what the client did with it — generic hardware
   or tools with no known job or project — stays `unsure` and goes to review.
3. **Nothing else changes:** a suggestion is still only a proposal a person approves
   (D-108), the classifier's first pick still does not become a suggestion by itself,
   and meter and plate evidence still outranks wording. It is an instruction change,
   not code: nothing in the report gates a suggestion on precedent.

**Not measured.** How often the Yunt now suggests, and how often it is right, is
unknown until a real batch has gone through; read the *Yunt suggestions* group of the
first jobs before trusting it.

## D-113 — History is a hint, never a rule; July and August may train the model, after the flaws are fixed

**Date:** 2026-09-21 · **Decided by:** Afaq · **Model:** Claude

1. **Only client-confirmed deterministic rules are treated as certain** — the product list,
   the meter map, the plate/bidón convention and the exact-wording business rules. What a
   supplier or wording was filed under before is **evidence to show a reviewer or the Yunt,
   never a rule that files a line by itself.** Reason, measured on July 2026 against the
   accountants' ledger: Doris Castillo was 96% one category in history and both history and
   the model said so with confidence; the accountants booked 37 of her 38 lines elsewhere.
   "Precedent and model agree, so auto-file" would have filed 138 July lines with 49 wrong.
2. **The model's own auto-accept is not a rule either.** In July it auto-accepted 76 lines
   with 22 wrong (0.98+ confidence was 50% right). The remedy Afaq chose is better training,
   not switching it off: see the overnight comparison in
   `reports/overnight_2026_09_21/README.md`. Nothing about the live threshold changed.
3. **Training on the July and August ledger labels is allowed** ("the purpose of this data is
   to improve the model"), but only after the training flaws are fixed, so the fixes are
   measured on unseen data first. Order: fix on old data, test on July, then train on July,
   test on August, then train on August. August invoices are not on this machine yet.
4. **Not decided:** suppressing "context-dependent" suppliers. Measured on July against a list
   built from old data alone, flagging the 18 mixed suppliers would have caught 3 of 22 wrong
   auto-accepts and cost 11 of 54 correct ones, so the hypothesis is not supported as a
   filter; variant D of the overnight run tests it as a training change instead.

## D-114 — A Yunt that does not finish never causes a write; the review wait follows liveness

**Date:** 2026-09-21 · **Decided by:** Afaq · **Model:** Claude

Amends D-108's "ML only" row. Found the hard way: with the AI Gateway out of credit, one email
saved a whole month (337 invoices / 897 lines) with nobody's approval.

1. **No Yunt answer, no save.** When the classifier answered but the Yunt did not — down, out
   of credit, or not done in time — the job ends `failed`, nothing is written, and the sender
   is told "No alcancé a terminar la revisión … no guardé nada" and can send again. The
   previous ML-only save is kept only behind `YUNT_ALLOW_ML_ONLY=1` (default off).
2. **How long to wait is liveness, not a fixed deadline.** The job asks the review sessions
   every 30 s whether they are still working; alive sessions keep it waiting, dead ones end
   the wait at once (the failure hook still ends it in seconds). The ceiling is what is left of
   the function's 300 s (`deadlineAt`, request start + 290 s, minus 20 s to stage the plan),
   because waiting past that only means being killed. The old fixed 240 s / 270 s are gone.
3. **Packets of 40 groups** (`YUNT_GROUPS_PER_PACKET`, default 40, was 80) so more run in
   parallel and each finishes sooner. Cost is about the same; the fixed per-packet context
   is paid more often.
4. **Not solved:** a month that genuinely needs more than ~5 minutes cannot finish inside one
   function. The measure is the 100-invoice test (6 packets); if a month does not fit, the
   next step is a finisher that stages the plan when the last packet arrives, instead of a
   function that polls.

## D-115 — The Yunt reviews only what the classifier proposed or a rule held; reasoning is medium

**Date:** 2026-09-21 · **Decided by:** Afaq · **Model:** Claude

Reason: cost. The first measured review (100 July invoices, AI Gateway log in
`reports/overnight_2026_09_21/gateway-inference-requests.csv`) cost $2.85 for a run that was
cut off at one packet of six done, about $0.04 to $0.06 an invoice or roughly $14 to $20 for
a month; thinking tokens were about a third of it.

1. **Lines the client's own rules settled are not shown to the Yunt.** A line is skipped when
   its decision is `auto_accept` and its source is `product_lookup`, `meter_lookup` or
   `business_rule`. They are confirmed as they are and keep their source (they are not
   rewritten to `yunt_applied`). Everything else is still reviewed: every classifier line, and
   every line a rule deliberately held (petrol without a known plate, DTE 43). A group is
   skipped only if all of its lines are settled. On the 100-invoice sample: 220 groups
   become 155, 6 packets become 4.
2. **Trade-off accepted.** The Yunt can no longer catch a rule-settled line the accountants
   disagree with. July showed three (sulfato de cobre, AdBlue, Spartan Check); those belong
   to the client's list, not to a per-line review (D-041).
3. **A batch with nothing left to review skips the Yunt** and goes straight to a person's
   approval; nothing is written first.
4. **`reasoning: "medium"`** in `agent/agent.ts` (was `high`, D-076). It applies to every turn
   the agent takes, not only reviews. **Unmeasured:** whether review quality moved. Watch the
   *Yunt suggestions* group and the purchasing and report replies, and go back to `high` if a
   confident wrong "keep" or a bad suggestion appears.

## D-116 — Keep the packets that delivered; a silent packet must not cost the whole review

**Date:** 2026-09-21 · **Decided by:** Afaq (after the second 100-invoice run) · **Model:** Claude

The second run (100 invoices, D-115 settings): 4 packets of about 40 groups. Three delivered, at
2 min 13 s, 2 min 13 s and 3 min 21 s after the review started; the fourth never did, and the job
discarded all four at its ceiling. The paid-for work of the three was thrown away, twice
(the first run lost five packets to the gateway budget).

1. **`awaitVerdicts` returns what arrived** when the ceiling, a dead packet, a stopped review or
   120 s of silence after the last delivery ends the wait. It returns null only when nothing
   arrived, which is still a failed review (D-114).
2. **Groups that never came are marked for a person** (`unsure`), so the classifier's word alone
   does not confirm them, and the plan is staged for approval as usual. Nothing is written before
   approval.
3. **`maxDuration` 300 -> 800 s** on the email and upload routes (Fluid compute), deadline 790 s.
4. **Not known:** why the fourth packet was silent (slow, or a session that ended without
   submitting). The session stream could not be read from outside the deployment. The gateway
   export for that run is the next place to look. Not fixed: re-dispatching a silent packet.

## D-117 — Audit of the review path: no paid-for work is thrown away, and every session is capped

**Date:** 2026-09-21 · **Decided by:** Afaq ("make sure money is not going to waste") · **Model:** Claude

Found by reading the wait and dispatch code against the two failed 100-invoice runs:

1. **One failed packet ended the whole wait.** The failure hook marks the batch `unavailable` when
   *any* session dies; the wait treated that as the end. With 13 packets a single provider blip
   would have abandoned twelve working ones. Now the wait gives up on that signal only if nothing at
   all has delivered within 45 s (a real outage: credit, budget, provider).
2. **A silent packet was never retried.** A session that finishes its turn without submitting parks
   at `session.waiting` and looks alive to the probe. A packet still owed after its peers delivered
   (1.5x their median time, at least 90 s), or one that never started, is now started once more
   under its own operation id. Once per packet, and never when nothing has delivered.
3. **One failed dispatch orphaned the rest.** `Promise.all` rejected while sessions that had already
   started kept spending. Dispatch now retries each POST once, keeps what succeeded, and the wait
   re-dispatches the rest.
4. **Nothing bounded a looping session.** `agent.ts` now has `limits.maxTokenCostUsdPerSession: 1.5`
   (a packet costs about $0.3 to $0.7). The instructions also say never to end the turn without
   `submit_batch_proposal`.

Worst case, stated plainly: every packet loops to the cap and is retried, so at most 2 x $1.5 per
packet, about $12 for 100 invoices and $40 for a month. The gateway key budget is the outer bound.
Typical, from the gateway log with D-115: about $2 to $3 and $7 to $11.

**Still not known:** why the fourth packet of the second run was silent. The retry makes it cost a
retry instead of the whole review; the cause is for the next run's logs (`[yunt] packet N delivered
after S s`, `... is silent; starting it once more`).

## D-118 — B_july70 picked over F_targeted_fix; exported int8 under D-097's ceilings, deployed at 0% traffic

**Date:** 2026-09-22 · **Decided by:** Afaq · **Model:** Claude

1. **F_targeted_fix's headline August win was training contamination, not evidence.** `scripts/107`
   trained F directly on 41 of the 94 lines `august_score.py` scores against. On every exam neither
   model trained on — locked843 (843 rows), the August lines actually held out of F
   (`F_holdout_exam[august_holdout]`, 56 rows), and the July holdout (117 rows) — B_july70 ties or
   beats F, and clearly wins the income-slice gate (22/22 vs F's 21/22) and the July holdout (47.9%/0
   wrong vs 38.5%/3 wrong). **B_july70 ships, not F.** F's targeted rows didn't generalize, consistent
   with A/C/D/E's diet variants all scoring worse than B too (D-113).
2. **Neither model fixes the Verisure ADM-1.2/1.7 bug.** Checked directly: both still predict ADM-1.7
   top-1 on the untouched locked843 Verisure rows (v1.4.1 99.3%, B 97.3%, F 89.2% — F nudged toward
   ADM-1.2 at 7.6% but didn't flip). **locked843's own gold label for Verisure is ADM-1.7** — the old
   test set encodes the same wrong answer the accountants reject every month. This is a rule gap, not
   a training gap. **Fixed same day as a deterministic rule, see D-119** — not by retraining either
   model, and locked843's own label is still stale (do not read a locked843 Verisure "miss" as a
   regression going forward; it is the exam that is wrong there, not the system).
3. **INT8 export needed D-097's ceilings, not new ones.** Default gate (0.03 top-1 / 0.0 decision)
   failed: cosine 0.99425, top-1 disagreement 6.05%, decision disagreement 3.44%, accuracy 0.7663 fp32
   → 0.7556 int8. Both measured numbers fall under the ceilings D-097 already established for
   v1.4.0/v1.4.1 (0.09 / 0.05) — reused, not loosened further. Traced the 29 decision flips by hand
   before accepting: 24 auto-accept→review (safe), 5 review→auto-accept, and of those 5 exactly **one
   is a new false positive** — "TOALLA PAPEL INTERFOLIADA" (Cooperativa Agrícola y Lechera), true
   EXP-5.3, both fp32 and int8 already agreed on the wrong EXP-2.6, int8's confidence alone crossed the
   auto-accept bar. 1/843 = 0.12%, accepted as the same class of cost D-097 already priced in.
4. **Auto-accept thresholds (0.75/0.50) are v1.4.1's, reused as-is, not recalibrated for B.** Real
   recalibration on locked843 is still open — do not read this deploy as a re-tuned release.
5. **Deployed as `mlmodel-b-july70-rc1`**, tagged `b-july70`
   (`https://b-july70---mlmodel-ufmuwiq6ta-ew.a.run.app`). All of `scripts/88_prove_deploy.sh` passed.
   Shipped at 0% traffic first, deliberately, with production still on v1.4.1 — **superseded same day,
   see D-119: traffic moved to 100% after Afaq's explicit go-ahead.**
6. **Pipeline gap found and fixed along the way, not specific to B:** `scripts/75_calibrate_familiarity_gate.py`
   called `SetFitModel.from_pretrained`, which crashes on any locally-saved model (no HF repo id) —
   same bug already documented and worked around in `training/export_onnx.py`. Now loads body+head
   directly. Also bridged the overnight comparison pipeline's stripped split.csv schema
   (`split,gold_id,category_code`) to what the release pipeline expects (`+text,text_sha256`) — the two
   pipelines were never wired together before this.

## D-119 — B_july70 traffic moved to 100%; Verisure shipped as a rule; Jev experiment concluded (for now)

**Date:** 2026-09-22 · **Decided by:** Afaq · **Model:** Claude

1. **Traffic moved from 0% to 100% on `mlmodel-b-july70-rc1`, Afaq's explicit go-ahead.** Verified with
   `scripts/88_prove_deploy.sh` against the base URL. `CLASSIFIER_URL` already pointed at the base
   Cloud Run URL rather than a revision tag, so no Vercel change was needed — the Yunt started calling
   B_july70 on its next classifier call, no redeploy of `milk-company` required. Supersedes D-118 §5.
2. **Verisure → `ADM-1.2` shipped as a deterministic rule, superseding D-118 §2's "needs the 5th
   business rule" note.** Checked against real ledger data before writing anything: 18/18 real
   Verisure lines ever seen (2025 locked843, July 2026, August 2026) are `ADM-1.2`, no exceptions,
   exactly matching the client's own email answer.
   **First attempt was wrong and was caught and corrected in the same session, not left as shipped:**
   16 exact `item_text|provider` rows in `app/data/product_lookup.csv`, one per real month/contract
   string seen so far. Afaq caught it immediately — Verisure's monitoring charge is a recurring
   monthly invoice, so the item text embeds the month and one of 4 contract numbers, and an
   exact-text row breaks on every new month. **Replaced with a new, month-agnostic `providerRules`
   mechanism**: a new `app/data/provider_rules.csv` (provider, transaction_type, category_code) for
   suppliers whose entire business with this client is one thing, checked in `applyRules()`
   independent of item_text. New `RulesData.providerRules` field, generator support in
   `scripts/generate-rules-data.ts`, one CSV row: `VERISURE CHILE SPA,COMPRAS,ADM-1.2`. Verified live
   against 2025, 2030, a never-seen contract number, and a hypothetical different Verisure line — all
   correctly resolve, because the rule doesn't read wording at all, only the supplier. Regenerated
   `rules-data.json` on both `milk-company` branches (`yunt` and `experiment/jev-typesafe`) via
   `scripts/generate-rules-data.ts`. **Deliberately not mirrored into `app/inference/business_rules.py`
   / Cloud Run this pass** — the TS `applyRules()` layer already intercepts these lines before either
   classifier is called, so the fix is complete without a second Cloud Run redeploy.
   `scripts/check-rules-parity.ts` will report a real, known, temporary disagreement between the
   Python and TS sides until the Python data is brought current — expected, not a bug to chase before
   the demo. **Neither `milk-company` branch's changes are committed** — left for Afaq to review.
   **The general lesson, worth applying to any future exact-match rule for a recurring invoice:**
   check whether the invoice text contains something that changes every time (a date, a sequence
   number, a contract reference) before choosing item-text matching over supplier-level matching —
   the first attempt here didn't ask that question and shipped something that would have silently
   reverted to the model's wrong guess every month starting in September.
3. **The Yunt's own precedent search would not have caught the Verisure bug**, checked by reading
   `yunt_category_precedent` (`supabase/025_invoice_context_precedent.sql`) directly rather than
   assuming. It ranks `human_confirmed` evidence first but falls back to the model's own past
   `pipeline_auto_accepted` guesses when nothing human-confirmed exists — and no Verisure line had
   ever been human-corrected in Supabase, so the only "precedent" available was the model agreeing
   with its own past mistakes. **The precedent safety net has a blind spot exactly where a bug is
   systematic and unanimous** — worth remembering the next time a "the Yunt will catch it" argument
   comes up for a different recurring, confidently-wrong pattern.
4. **Jev (Typesafe AI) is not ready to replace the classifier — concluded after six rounds of real
   prompt iteration, not a first impression.** Branch `experiment/jev-typesafe` in `milk-company`,
   left as-is, not merged, not deleted. On `locked843`, iteration (category-description hints, an
   explicit `NEEDS_REVIEW` abstain option, positive rules checked against real label distributions)
   closed the accuracy gap to B_july70 (~73–76% on commits vs B's 71.0%). **Cross-validated on July
   and August and the tuning did not generalize**: beat B_july70 on July accuracy (51.5% vs 46.2%) but
   was ~5x less safe (14 vs 3 wrong auto-accepts); on August it flipped (46.8% vs 60.6% accuracy, but
   safer: 2 vs 6 wrong auto-accepts). **B_july70's wrong-auto-accept count stayed in a tight band (6,
   3, 6) across all three months of real evidence; Jev's swung from 2 to 24.** That instability across
   months, not either single accuracy number, is the actual reason to hold off — a hint written from
   `locked843` evidence was directly contradicted by a real July line (an embroidery-service rule).
   Two real analytical mistakes were made and caught mid-session by checking full label distributions
   instead of single examples before writing a rule (`CONTROL DE ROEDORES` is 17:1 `EXP-7.0`, not the
   reverse as first written; GEA splits 6:2:2 across three categories, not one) — worth citing as the
   concrete case for "check the distribution, not the example" going forward, on any project. Untried,
   real next steps if this resumes: Typesafe's `examples` field (distinct from the `what`/`not_for`
   hints used so far), real precedent retrieval (few-shot real historical lines per call), hierarchical
   two-stage classification, and calibrating Jev's own auto-accept threshold instead of reusing
   B_july70's 0.75/0.50.
