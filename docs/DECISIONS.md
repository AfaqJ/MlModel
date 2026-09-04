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

## D-010 — Document type is out of scope; direction comes from the folder

**Date:** 2026-08-11 · **Decided by:** Afaq

Raw data contains credit notes, exempt invoices, settlement invoices and debit
notes. Classifying by document type is not this project's job — the
COMPRAS/VENTAS folder already gives direction, and Supabase already stores it.
Noted here only so a future session does not re-derive it as a "gap".

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
