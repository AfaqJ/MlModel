# EVIDENCE_RULES — how a claim is allowed to become a number

Every rule here was paid for by a mistake that nearly reached the client. They
are not style guidance. Each one is a step that must actually run before a
figure, a group, or a "we can't do this" leaves the session.

These are cheap to follow and expensive to skip: in every case below the
correct check was available the whole time and took under two minutes.

---

## 1. A schema tells you intent. The data tells you behaviour.

Reasoning about what a field is *designed* to hold is a hypothesis, not
evidence. When both the schema and the values are available, **the values win.**

The failure: a fuel supplier's invoices carried a vehicle plate. The claim was
that for a bulk supplier the plate must be their delivery truck, reasoned from
the field's purpose in the national e-invoice schema. It survived several turns
and reached a draft client question. One query falsified it — 41 of 47 plated
lines carried plates seen at other suppliers, so they were the client's own
vehicles.

**The test for "does this field mean different things in different contexts" is
value overlap across those contexts.** Shared values mean one shared meaning.

Any claim that would change what a third party is asked must trace to a query
that was actually run. State explicitly whether an interpretation is measured or
inferred, and never let the two carry the same confidence.

---

## 2. An exclusion justified by a fact about the data is a hypothesis, not a decision.

Separate exclusions by **policy** ("out of scope") from exclusions by
**asserted fact** ("these never produce documents"). Policy is stable.
Fact-based exclusions are testable, expire, and must be re-tested against the
real data before the list is trusted — and again whenever the source data grows.

The failure: two categories the client described as "missing" had existed in the
taxonomy all along, sitting on an exclusion list. The recorded reason was a
factual claim, and it was false for one entry — which was named explicitly in
the exclusion row's own notes. Nobody re-checked, because an item on an
exclusion list reads as settled.

**Treat any identifier appearing in an exclusion row's notes as a search term to
run, not as documentation.** Grep for the things the list claims do not exist.

---

## 3. A measured number in prose is a snapshot with no expiry stamp.

Any figure written into a doc must carry **the state it was measured at** on the
same line — script number, commit, or payload hash.

And: **never quote a doc's measured figure in an outward-facing artefact without
re-deriving it from the source of truth first.** The doc is the pointer to the
measurement, not the measurement.

The failure: a question list stated counts measured "after script 86". Scripts
87, 88 and 89 then moved hundreds of rows and the counts were never revised.
Re-measuring before drafting found a family listed as 240 lines was 460, and
another listed as 217/191 was 173. Every one of those numbers was about to go to
a client in writing. The doc was not wrong when written; it was wrong by the
time it was read, and nothing in it signalled that.

---

## 4. A hypothesis about the data is a query, not a discussion.

When anyone — Afaq, a colleague, the client — raises a hypothesis about what the
data means, identify the **cheapest query that discriminates between true and
false**, and run it *before* writing any answer.

Then report the strength of the signal honestly. And check separately whether a
**structural fact about how the data was produced** settles it more cleanly than
the statistics do — it usually does.

The failure that shows both halves: asked whether consumables in the review
queue were inputs to a capital project. The spend histogram against the build
window returned a weak signal (39% of lines in 27% of the calendar, flat money,
largest month *preceding* the project). The structural fact settled it properly:
the project was billed as a turnkey contract including its own fittings, so the
builder bought the materials. Neither answer was reachable by reasoning alone.

Where the question is ultimately a policy choice rather than a fact, say so and
route it to the decision owner instead of answering it.

---

## 5. Only ask a question whose answer you can execute.

For each question drafted for the client, write the sentence:
**"if they answer X, the system does Y."**

If Y cannot be written because the data lacks the field the answer keys on, the
question is unusable. Either rewrite it to request that missing field directly,
or drop it.

The failure: *"Is work on an existing structure an expense, and only new
construction an asset?"* — answerable, correct, and completely useless, because
no record says which of the two it is. Afaq caught it: *"do we even know how to
distinguish them even if he tells us?"* The fix was to invert the question, from
asking for the rule to asking for the missing key itself — name the projects and
their date ranges, and we route by supplier plus window.

Also state both branches in the question, including what happens if the answer
is "it cannot be automated." That is a real and useful answer; invite it
explicitly.

---

## 6. A substring match names candidates, not members.

**List and read the matched rows, row by row, before quoting the count outward.**
Check near-miss vocabulary explicitly.

The failure: a substring match on the bale product root returned 28 lines.
Reading them showed only 18 were bale-making. The rest were wrapping film,
netting, transport, a machine repair — and one line of **crushed stone**, whose
name differs from the product's by a single letter (`bolón` vs `bolo`). The
inflated count and its money total had already reached two drafts.

**Expect the reading to change the answer rather than confirm it.** In that case
the read also produced the finding that mattered: the *supplier* column separated
silage from hay where wording, property and date all failed.

Related: a normaliser regex that misses a spacing variant undercounts silently.
`SULFATO DE? ?COBRE` matched 3 of 6 rows; `SULFATO\s+(DE\s+)?COBRE` matched all 6.
**A count that disagrees with the docs is a regex bug until proven otherwise.**

---

## 7. A correlate is not a key. Validate a rule on what it catches *wrongly*.

Before proposing any rule that assigns records by a proxy attribute, **list the
records the rule would capture and inspect them for ones that clearly do not
belong.** Report that false-capture set alongside the rule.

The failure: having established that a date window correlated with a capital
project, a draft proposed routing every contractor invoice inside that window to
the project's asset account. Afaq rejected it on sight. The window contained a
house repair at Maitén and a fence at Raíces. The error survived several drafts
because the window had only ever been validated on the rows it caught correctly.

Where the false-capture rate is unacceptable and no true key exists, **drop the
rule rather than weakening it.** The honest fallback is to check whether the
money concentrates, and hand the client the few records carrying the weight to
adjudicate — in that case, the 10 contractors holding 73% of the money in 93
lines.

---

## 8. "We cannot read this" is a claim about every field, not the one you looked at.

Before any record goes in an "unresolvable" bucket, **confirm every populated
field on it has been examined.** Report the bucket split into genuinely-empty
versus resolvable-from-another-field, with counts and values for each.

The failure: a large group was reported unreadable because `item_text` held a
placeholder. Afaq pointed out that `description` carried the real content.
Measured: of 155 such rows, **155 had a description and 141 were fully
identifiable from it.** Only **14 rows, CLP 1,450,281** were genuinely blind. The
draft was about to tell the client that ~254 rows worth CLP 106,758,176 were
unresolvable, and to ask a question about a subgroup that was entirely
self-describing.

This is the most expensive rule to break, because it **hands away work you can
actually do.**

---

## 9. An assertion firing is information, not an obstacle.

When a guard fires at a number you did not expect, the answer is to read the
extra rows — not to widen the guard.

`assert len(changed) == 20` fired at 31 in `scripts/91`. The 11 extra were DIFOR
service intervals the client had never filed, and inspection showed they were
*justified* (client 3/3, model 18/18 unanimous). Without the assertion they would
have gone in silently. A second assertion was added to keep that extension
honest.

Corollary: **a report that suddenly finds a surprising number of hits deserves a
debug pass before it is believed.** A contradiction check once reported 138 hits;
every one was a normaliser bug — item names too short to identify a product
normalised to an empty key, which then collided with everything. **A normaliser
that can return an empty key must refuse to match on it.**

---

## 10. Assign each row to exactly one bucket, and assert the buckets sum.

When measuring a queue by category, a supplier-shaped bucket silently swallows
product-shaped ones.

The failure: counting "hardware store" and "fasteners" as separate questions
triple-counted hundreds of rows — the hardware-store question *contained* the
fasteners, the fittings, the welding and half the paint. The re-partition into
exclusive buckets changed the story: the eight questions covered 47% of the lines
but only **12% of the money.**

**Partition in priority order, and assert the buckets sum to the total.**

---

*Rules 1–8 were promoted from session gotchas on 2026-08-27 so they stop living
only in `STATE.md`, which keeps five sessions and then drops them. 9 and 10 came
from the same audit. See `docs/LABELING_RULES.md` for what may enter gold, and
`docs/CLIENT_CONVENTIONS.md` for how the client wants things filed.*

## 11. A comment asserting a property is a claim, not evidence — and a confident one hides the defect.

The dashboard's purchases-vs-sales chart carried this above it:

> *"Two series, one axis — never a dual axis, so the visual comparison stays
> honest."*

Both series were rendered with the same `stackId`, so the upper band plotted
their **sum** while the legend named only one of them. On 2025-10 it drew
1,194,984,855 where the named series was 578,067,481 — **overstated 2.07x.**

The sentence was true about the axis and silent about the stacking. It survived
three review passes precisely *because* it was reassuring: readers reached a
statement that the chart was honest and stopped there.

`tsc`, ESLint, `npm run build` and translation parity were all green throughout.
None of them can see what a chart draws.

> **Verify the rendered output against recomputed source data, never against the
> code's description of itself.** For a chart that means: recompute each series,
> then check the value at the visual extreme against the series the legend names.
> A component that explains why it is correct has earned more scrutiny, not less.

## 12. Reproduce the artefact before reporting a finding about it.

The 2026-09-03 dashboard audit began by deriving the page's default filter
window from its own code (`max(invoice_date) - 12 months`), recomputing that
window over `backups/supabase_20260903T054820Z`, and matching it against a
screenshot of the live app: record counts, both fiscal components with their
percentages, the net-position figure, the anomaly count, and the concentration
triple — all exact. Only then was any finding written down.

Two things this bought that reading code could not:

- the default window **excludes 1,003 of 5,195 invoices**, which no amount of
  reading would have surfaced as a number;
- every subsequent claim rested on a model already proven to be the system,
  rather than on an inference about which filter state produced the picture.

> **An exact reproduction is the cheapest proof that your model of the system is
> the system.** A near-match is a failed reproduction: it means something is
> still wrong, and every finding built on top of it inherits that error.
