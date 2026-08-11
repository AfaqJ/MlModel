# Start here — what happened, in plain English

One page. Read this and you know the whole story. Everything else in this folder
is detail you can look up when you need it.

| File | What it's for |
|---|---|
| **README.md** (this) | The story, plain English |
| `HANDOVER.md` | Where the work stands right now |
| `DECISIONS.md` | Every decision + why (11 entries) |
| `BUG-001-...md` | The milk incident, fully traced |
| `RESULTS-v1.2.0.md` | Before/after numbers |
| `ARCHITECTURE.md` | How the system is shaped |
| `FLOW.md` | Which code calls what |
| `CONSTRAINTS.md` | What must never happen |
| `TEST_CHECKLIST.md` | What to check before shipping |
| `ROLLBACK.md` | How to undo anything |

---

## 1. What went wrong

The client is a dairy company. Their milk-sale invoices were labeled as **road
maintenance expenses**.

The cause was not what it looked like. **The model had no "milk sales" category
at all.** It wasn't badly trained on milk — milk simply did not exist as an
option it could choose.

Here's how that happened, in order:

1. We had 47 milk-sale invoice lines. All 47 were reviewed and correctly labeled.
2. A script copied reviewed rows into the training file. To avoid duplicates it
   compared rows **by item name only**. All 47 rows were named "VENTA DE LECHE",
   so it kept 1 and threw away 46 — even though each had a different description
   (different month, volume, price, farm).
3. The training script skips any category with fewer than 2 examples. Milk had 1.
   **It was dropped silently** — logged, but training continued.
4. So the finished model knew 66 categories, and milk wasn't one of them.
5. When a milk invoice arrived, the model had to pick *something* from its 66
   options. It picked road maintenance, at 15% confidence.
6. 15% confidence means "I have no idea." The system correctly flagged all 125
   sales lines as **needs review**. The dashboard showed them as final answers
   anyway, without the confidence score.

**So there were two separate failures**: the model was missing a category, and
the dashboard presented uncertain guesses as facts. The second one is what
destroyed the client's trust — the model was honestly saying "I don't know" the
whole time.

## 2. The thing you asked about — why the name didn't save us

Reasonable question: the category is literally called "VENTA DE LECHE" and the
invoice says "VENTA DE LECHE". Why didn't they match?

**Because the model never sees category names.** It works in two steps:

- Step 1 turns the invoice text into a list of 768 numbers (an "embedding").
- Step 2 is a scorer with one row of numbers per category. Each row is **learned
  from that category's examples** — nothing else.

The name "VENTA DE LECHE" is just a display label we attach to the code
`ING-0.1` for humans to read. It's never fed into the model. A category with
zero examples has no row of numbers, so it can never win — no matter how
perfectly its name matches.

If you wanted name-matching to work, that's a different design (embed the
invoice, embed the category name, compare them). SetFit deliberately trades that
away for better accuracy once you have ~8+ examples per category.

**Bottom line: no amount of good naming rescues a category with no examples.**

## 3. What we fixed

**Fixed the duplicate rule.** It now compares rows by item name **+ description
+ supplier** — the same fields the model actually reads. That alone recovered
519 already-reviewed rows that were being thrown away.

**Took sales data straight from the raw invoices.** For milk, cows, calves and
heifers we didn't need any AI review — these are the client's own outgoing
invoices, the item name states the category. 59 more rows.

**Removed 6 poisoned rows.** Some *purchases* were labeled as *sales* — the
company buying cows was recorded under "cow sales". Training on that teaches the
model the exact opposite of the truth.

**Added 4 synthetic rows** for two tiny sales categories, only to get them over
the 2-example minimum. They're clearly marked and never used for scoring.

Result:

```
training rows          1,733 -> 2,309
usable categories         66 -> 69
milk examples              1 -> 48   (10 held back for honest testing)
```

## 4. Did it work

Yes, on the thing that broke.

```
                      before                    after
VENTA DE LECHE   road maintenance @ 0.15   milk sales @ 0.97
VENTAS TERNEROS  staff costs      @ 0.51   calf sales @ 0.98
VENTA DE VACAS   road maintenance @ 0.31   cow sales  @ 0.87

sales lines correctly identified as income:  0 of 125  ->  120 of 125
```

We also tested on 20 sales rows the model had **never seen during training**:
20 out of 20 correct. The old model couldn't be tested on income at all — its
test set contained zero income rows, which is why nobody caught this before
release.

## 5. What got worse — the honest part

**One wrong confident answer.** A row saying `VENTA DE ACTIVO FIJO` (sale of a
fixed asset — a truck, machinery) was labeled **milk sales at 84% confidence**
and auto-accepted. That's the only row that would reach the client wrong.

**Why it happened, and it's the same root problem as the original bug:** there
is **no category in the taxonomy for selling a truck**. All the `ING-*`
categories are operating revenue — milk, cows, calves, heifers, firewood. Asset
disposal isn't there. So the model has no correct option, must pick something,
and picks the closest-sounding one. Now that milk has 38 examples it dominates
the "VENTA DE …" neighbourhood, so it wins.

The same thing shows up in expenses: a row reading `TRANSITO_INFRACTOR` (a
traffic fine) got labeled as freight. There's no category for fines either — it
was deliberately excluded from this system as accounting-only.

**This is not a model bug. It's a gap in the category list.** No amount of
retraining fixes it.

**471 fewer auto-accepts** (6,356 → 5,885), meaning more rows need human review.
But looking closer: of the 860 rows that moved to "needs review", **715 kept the
same label and just lost confidence.** That's a side effect of telling the model
to treat rare categories as equally important — it spreads its certainty
around. Only 145 actually changed their answer.

**Purchases labeled as income went 9 → 22.** All of them are flagged for review,
none auto-accepted, highest confidence 53%. Contained, but it's the mirror of
the original bug and worth closing.

**Where else confidence changed something:** 129 rows changed category *and* are
now auto-accepted. 112 of those are the sales fix. Of the other 17, I read every
one: roughly 8 clearly improved (gasoline now goes to "Bencina" instead of
"Movilizacion"; "ALMUERZOS" now goes to meals instead of building maintenance),
about 4 look wrong (a paintbrush filed as office supplies, blue spray paint as
mastitis medicine), the rest are genuinely ambiguous. **Importantly, none of the
129 had a confident answer before** — every one was previously "don't know". We
never overwrote a confident answer with a different confident answer.

## 6. Should we add pattern matching — yes

You asked this earlier and the answer held up. The system already does this: it
has a meter lookup (22 entries) and a product lookup (604 entries) that run
*before* the model and skip it entirely.

Add a third one for exact sales names. Reasons:

- For a name that repeats identically and states its own category, a lookup is
  simply correct. Asking a probabilistic model to rediscover a known fact is
  spending uncertainty for nothing.
- It fixes the asset-disposal problem: `VENTA DE ACTIVO FIJO`,
  `VENTA CAMIONETA`, `maquinaria`, `OTROS INGRESOS` (7 rows) get routed to
  "needs client decision" instead of being guessed at confidently.
- It must check direction. `VACAS` on a purchase invoice is a purchase, not a
  sale — that's exactly what poisoned the cow category.

The model stays for the long tail, which is real: 5,349 different item names,
4,115 of which appear exactly once.

## 7. The training crash — what a "GPU memory" error actually means

Training kept crashing with this, and it took three tries to diagnose correctly:

```
MPS backend out of memory
  MPS allocated: 5.35 GiB, other allocations: 14.34 GiB, max allowed: 20.13 GiB
```

**MPS** is Apple's system for running maths on your Mac's graphics chip.
Training uses the GPU because it's much faster than the CPU.

**Key fact about Apple Silicon:** there is no separate graphics memory. The CPU
and GPU share the same 16 GB. "GPU memory" *is* your RAM.

The three numbers:

- **`max allowed: 20.13 GiB`** — PyTorch's self-imposed spending limit.
  macOS says the GPU may use 11.84 GiB (75% of 16 GB); PyTorch multiplies by its
  default 1.7 safety ratio = 20.13 GiB. It exceeds physical RAM because PyTorch
  assumes it can spill to disk.
- **`MPS allocated: 5.35 GiB`** — the real model data in use.
- **`other allocations: 14.34 GiB`** — **PyTorch's own recycling bin**, not
  other apps.

That last one is the trap. Asking the OS for memory is slow, so PyTorch grabs it
in big blocks and keeps them after you're done. Measured directly:

```
allocate a 200 MiB tensor  ->  PyTorch takes 1024 MiB from the system
delete that tensor         ->  PyTorch still holds all 1024 MiB
call empty_cache()         ->  now it gives it back
```

So the crash was `5.35 in use + 14.34 hoarded + 0.73 needed = 20.42`, over the
20.13 limit. **The job ran out of its own budget while sitting on 14 GiB it
wasn't using.**

This is why closing Chrome did nothing and why rebooting did nothing — neither
was ever part of that number. Fixed by raising the ceiling with
`PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0`.

## 8. Mistakes made during this session

Recorded so you can judge the work honestly:

- **I quoted "+680 rows" repeatedly, then delivered 519.** The 680 was counted
  before we decided to skip contradictory item names; the two numbers were never
  compatible and I kept quoting them together.
- **I wrote the same bug we were fixing.** My harvest script compared rows using
  an empty supplier field while the training file had "ANTILLANCA SPA", so the
  duplicate check failed and it would have added 47 duplicate milk rows. Caught
  in the dry run, before anything was written.
- **I misdiagnosed the training crash twice.** First I said other apps were
  eating memory (closing Chrome changed nothing). Then I blamed 36 days of
  uptime and had you reboot — a fresh boot with zero swap gave the identical
  error. The real cause was PyTorch's own memory cache, explained in section 7.
  I should have measured it before sending you to reboot.
- **I said "10,014 silver rows" early on.** I'd added up four different file
  types. The real audit file has 1,672 rows.

Every gold file write took a timestamped backup first, and every script ran as a
dry run before committing, which is why the two data mistakes cost nothing.

## 8. What's left

1. Route the 7 asset/other-income rows by rule, not by model.
2. Block purchases from ever scoring an income category, and vice versa.
3. Decide whether 471 extra review rows is an acceptable price.
4. Export the ONNX package as v1.2.0.
5. Ask the client: how should selling a truck be categorised? Is
   `VENTA DE OTROS ANIMALES` actually used? (It has zero real examples.)
6. The dashboard must show confidence and must never present a "needs review"
   row as final. That's what caused the incident, and it's still unfixed.
