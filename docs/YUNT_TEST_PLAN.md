# Testing the Yunt against the real Claude API

Written 2026-09-11, when every remaining ticket was blocked on the key and
nothing else. Read `STATE.md` first for where the project stands.

The point of this file is that **the first paid run should not be the first run.**
Two silent failures were found on 2026-09-10/11 that every automated check had
passed, and both were found by using a real screen. The API path will have more.
Finding them with a stub costs nothing; finding them with Sonnet costs money and,
worse, a confusing half-result that looks like a model problem when it is a
schema problem.

## Where the key goes

`agent/agent.ts` selects `anthropic/claude-sonnet-5`, a **Vercel AI Gateway**
model id (D-076). That routes through the gateway, not straight to Anthropic, so
the credential is a gateway one:

| Path | What to set | Where |
|---|---|---|
| **Gateway, recommended** | `AI_GATEWAY_API_KEY` | `.env.local` for local runs; Vercel Preview env for the deployed Yunt |
| Gateway via linked project | nothing — `VERCEL_OIDC_TOKEN` is already in `.env.local` | refresh with `vercel env pull`; the token expires, roughly twice a day |
| **Anthropic direct** | `ANTHROPIC_API_KEY` | needs `npm install @ai-sdk/anthropic` and `model: anthropic("claude-sonnet-5")` in `agent/agent.ts` |

If the key Afaq has is an **Anthropic** key (`sk-ant-…`), it is the third row:
the gateway will not accept it. That row also changes `agent.ts` from a
compile-only config into a runtime one in eve's terms, so make the change, run
the free dry run below, and watch for eve complaining at startup before
concluding it worked.

Direct-to-Anthropic has one advantage worth the install: **usage and spend show
up in the Anthropic console**, per request. Through the gateway they show up in
Vercel. Given the whole concern here is not racking up a bill blindly, the
console you can actually read is the one to bill against.

## Step 0 — the free dry run, before the key is wired

`reviewAfterWrite` calls `dispatchOrCloseReview(db, staged, dispatch)`, and
`dispatch` is already a parameter with a default. Pass a stub that returns a
canned, well-formed review response and the entire chain runs with no API call:

- the review packets are built and chunked,
- `submit_review_chunk`'s guard rejects findings citing evidence it was not given,
- proposals are written, approval parsing runs, the apply happens, undo replays,
- the outbox decides whether an email goes out.

**Everything that is not the model's wording is exercised here.** Schema
mismatches, chunk boundaries, the exact-line approval rule, the later-edit-wins
refusal, the undo replay. Run this first and fix what it finds. It is the single
highest-value hour in this plan and it costs nothing.

Then run it again with a *deliberately bad* canned response — a finding citing a
category that was never offered, a malformed approval line — and confirm the
system refuses rather than storing it. A guard that has never been seen to fail
is not known to work.

## Where test data comes from

Afaq put two options on the table (2026-09-11), and they answer different
questions. **Both are allowed. Whichever is used, the rows come out again.**

### Option A — synthetic lines

Invent a document with a fake supplier RUT and a folio that cannot collide.
`scripts/89_cleanup_mct155_test.py` is the worked example: anchored on RUT
`77123456-7` and folio `999001`, dry-run by default, and it verifies the row
counts return to baseline itself.

Best for testing **behaviour you can specify in advance** — a deliberate
arithmetic error, a junk item name, an amount above the document total. You
control the answer, so a wrong result is unambiguous.

Weak for judging category quality: a made-up item has no precedent, so every
line lands in review and proves nothing about proposals.

### Option B — held-out real lines

Afaq's framing: *"take a chunk out of the original lines that are already in the
data, remove them from the data, then send them again so they act as new unseen
data."*

This is the stronger test of the **proposal**, because the client's own label is
the answer key. It is also already implemented offline and read-only:

    .venv-backend/bin/python scripts/87_measure_precedent_quality.py 400

That script removes each line's own row from its evidence before proposing —
the same rule the batch review follows, since a batch may not cite itself. Run
it **before** spending anything on the API. It costs nothing and it is the
honest measurement.

The live variant — actually deleting rows and re-ingesting the file — tests
something the script cannot: the real pipeline end to end, with a known answer
at the end of it. Four things to know before doing that:

1. **It is not truly "unseen".** Deleting `invoice_items` removes the precedent
   evidence, which is the point — but the line's `item_catalog` row and any
   `item_aliases` survive, so `product_lookup` and catalog matching still fire.
   You are testing the proposal path with a known answer, not a cold start.
   Making it genuinely unseen means removing the catalog entry too, which other
   invoices reference. Do not.
2. **The invoice row must go, not just the lines.** Dedup is
   `seller_rut | document_type | folio`, so a re-sent document whose invoice row
   still exists is rejected as already registered and nothing runs.
3. **Choose lines whose label you trust.** Only the 7,927 human-confirmed rows
   are an answer key. A row still in review is not a ground truth, it is a
   guess, and grading against it measures nothing.
4. **Take a small, contiguous, named chunk** — one supplier, one month — so the
   undo is a single scoped delete and re-insert rather than a scatter.

### Putting them back, which is not optional

- **Back up first.** `.venv-backend/bin/python scripts/81_backup_supabase.py`.
- **Write the undo before the write**, and dry-run it before it has anything to
  find, so you know it runs. Verify the counts against baseline afterwards.
- **Never leave a test row untagged.** A leftover `purchase_requests` row titled
  "Petroleo Diesel" survived the 2026-09-10 purchasing tests because the `PRUEBA`
  convention was not applied to it, and nothing in its content says it is a test.
  A test row that reads as a real one is worse than no cleanup, because the next
  person cannot tell.

### What the backup does and does not cover

`scripts/81_backup_supabase.py` exports **five tables** — `categories`,
`companies`, `item_catalog`, `invoices`, `invoice_items` — as a logical row
export over PostgREST, with a per-table row count and SHA, checked against what
the server reports. The three most recent are byte-for-byte consistent at
5,195 / 11,746 / 461 / 4,002 / 78, and live matches them exactly as of
2026-09-11.

It does **not** cover:

- **schema, indexes or RLS policies** — it restores data, not structure, so it
  is no defence against a bad migration;
- `item_aliases` (**8 rows live, backed up nowhere**);
- `purchase_requests`, `quotations`, `purchase_orders`;
- any `yunt_*` table — batches, flags, proposals, applications.

So for a held-out test on invoices and lines, the backup is a real safety net.
For anything touching aliases, purchasing or the Yunt's own tables, it is not —
write the undo and rely on that instead.


## The three real tests

Each one closes several tickets because the tickets sit on one path. Do them in
this order; each leaves the system in the state the next one needs.

### Test 1 — one invoice email, all the way through

**Closes MCT-160, MCT-141, MCT-149, MCT-150.** Four tickets, one email.

Send one email to `YUNT_INBOUND_ADDRESS` with a **small** ZIP attached — six
documents, not a month. Billing is per line, not per document, and six lines
exercise exactly the same code as six hundred.

What must happen, in order:

1. Resend delivers to `POST /api/yunt/inbound`. The webhook cannot be scoped, so
   every endpoint on the shared account sees every message — confirm ours ignored
   anything not addressed to it (D-061).
2. The deterministic ingest writes the invoices and replies with the reception
   report. **This must succeed with the model unavailable** (D-064) — worth
   proving by pulling the key for one run.
3. The post-write review runs, groups the lines, and proposes categories with
   evidence.
4. A second email arrives only if there is something to say (D-064, D-065).
5. Reply with the exact confirmation line, on its own. Check that a general
   "yes" does **not** approve, and that quoted text further down cannot approve.
6. The group applies. Undo puts every line back — category, reviewed flag, and
   provenance.
7. Edit one line by hand, then try to apply a proposal covering it. The Yunt must
   refuse and say so, not overwrite the person's decision.

Steps 5–7 are MCT-150's done-when: *a real approval and a real undo against live
data, before and after matching.*

**Before it runs:** back up (`scripts/81_backup_supabase.py`), and write the
undo first. `scripts/89_cleanup_mct155_test.py` is the pattern — anchored on one
fake supplier RUT, dry-run by default, and it verifies the counts return to
baseline. Do not reuse it; it is written for one specific batch.

### Test 2 — one question thread

**Closes MCT-152, MCT-153.** Two turns of one conversation.

Ask something that produces an artefact: *"¿Cuánto gastamos en fertilizantes por
mes este año?"* The answer must arrive as a real PDF or chart with the filter,
accounting basis, credit-note rule and any truncation printed on it. MCT-152 is
already implemented and needs exactly one acceptance run from a real stored
question; none existed before now, which is why it could not close.

Then ask something it should refuse — something the data cannot answer, like a
question about a supplier's margins. It must say it does not fit and record it.
That is MCT-153.

**Every number must come from a tool** (D-053). If a figure in the answer cannot
be traced to a query result, that is a bug, not a rounding difference.

### Test 3 — one purchasing email thread

**Closes MCT-156, MCT-157.**

Email a plain request — *"necesito 20 sacos de sal mineral para el Fundo
Raíces"*. A request should open. Then take it to an order and confirm the
CLP 500,000 two-quotation rule fires from the email path using the **same** code
the form uses, not a second copy.

Mark test rows `PRUEBA` and delete by `title like 'PRUEBA%'`, orders before
requests.

### After all three

**MCT-142** is the parent and closes when its children do. **MCT-165** — judging
whether a quotation is genuine before it counts toward the CLP 500,000 rule — is
unbuilt and is not part of this plan.

## Not racking up a bill

- **One small ZIP.** Six lines, not a month. Cost scales with lines.
- **Fix with the stub, confirm with the model.** Any failure that is not about
  wording or judgement should be reproduced in Step 0 and fixed there, then
  re-run once against the API. Never iterate on a bug by re-calling the model.
- **One change per run.** Two changes and a failed run tells you nothing.
- **Read the review packet before sending it.** `buildBatchReview` produces it
  without any API call. If the packet is wrong, the answer will be wrong, and you
  can see that for free.
- **Watch the first runs for quality, not cost** (D-076). A category proposal
  citing evidence it was not given, a refusal it should not have made, or
  reasoning that does not follow from the attached rows — any of those means go
  back to Opus. One line in `agent/agent.ts` and one in `after-write.ts`, and
  they must move together.

## Two variables that fail closed and look like bugs

Both are set on Vercel Preview, and every variable there is sensitive-flagged, so
they read back as `[SENSITIVE]` and cannot be confirmed from the CLI.

- An empty `YUNT_ALLOWED_ADDRESSES` means the Yunt can mail **nobody**.
- An unset `YUNT_INBOUND_ADDRESS` means it **ignores every message**.

A test where nothing happens at all is more likely one of these than a broken
pipeline.
