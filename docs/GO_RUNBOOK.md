# GO — the runbook for the first paid runs

Written 2026-09-11, before the key existed, so that "Go" is mechanical rather
than exploratory. `docs/YUNT_TEST_PLAN.md` is the reasoning; this is the order
of operations. Step 0 is **done** — what it found is at the bottom.

## Current progress — checkpoint 2026-09-11

All four pre-run blockers are resolved. The key and protection bypass are live;
`yunt` is pushed; the current Preview is Ready; and a protected GET reaches the
inbound handler and returns 405.

Test 1 has ingested and reviewed the seven-line archive. One Leasing proposal
was applied exactly once. The pending action is its undo: reply
`SÍ, ADELANTE` to the latest Yunt email, then verify the application, proposal
and invoice line against the recorded before-state. Selective approval, a
user-supplied category, negative confirmation cases and stale-proposal refusal
remain. Tests 2 and 3 have not started.

Two live defects were fixed on the way: hidden action context now survives the
email thread, and Resend HTTP 200 responses without an RFC Message-ID are
retried. Current frontend commit: `7d8b632`.

## Blockers found before spending anything (resolved history)

Four things would each have turned a paid run into silence. All were resolved
before the first paid run.

| # | What | Who |
|---|---|---|
| 1 | Anthropic credential on Vercel | resolved |
| 2 | eve middleware deployment failure | resolved and deployed |
| 3 | Deployment Protection blocked Resend | resolved with automation bypass |
| 4 | unpushed `yunt` commits | resolved |

Two smaller ones: the local `VERCEL_OIDC_TOKEN` is ~38 h expired (`vercel env
pull`), and `YUNT_ALLOWED_ADDRESSES` is exactly one address —
**`afaq@mctechstudio.com`**. Mail from anywhere else is ignored in silence, so
every test email must be sent from there.

## The order

    # 0. once, before anything
    cd ../milk-company && vercel env pull && npx tsx scripts/preflight-go.ts afaq@mctechstudio.com
    cd ../ML-model && .venv-backend/bin/python scripts/90_yunt_live_test_undo.py --snapshot
    .venv-backend/bin/python scripts/81_backup_supabase.py

Preflight must print `all clear`. It checks the credential against the model id
in `agent/agent.ts` (a `sk-ant-` key with a gateway id is the most likely silent
failure), that `YUNT_REVIEW_MODEL` still matches `agent.ts` (D-076), that both
fail-closed variables are set, and that the classifier answers as v1.3.3.

If the key is an **Anthropic** one, `agent/agent.ts` needs the direct path:
`npm i @ai-sdk/anthropic`, then `model: anthropic("claude-sonnet-5")`. Preflight
says so in those words rather than leaving it to be discovered.

### Test 1 — one invoice email  (MCT-160, 141, 149, 150)

The archive already exists and has already been read through the real ingest:

    .venv-backend/bin/python scripts/91_make_yunt_test_zip.py
    cd ../milk-company && npx tsx scripts/check-yunt-test-fixture.ts

Six COMPRAS documents, seven lines, supplier RUT `77123456-7`, folios
999101-999106, **~928 tokens of review packet**. Every wording but one is
already in `item_catalog`, so the batch creates no catalog rows and the
precedent search has real evidence. `Temp_Inference/yunt_test/yunt_test_6.md`
says what each document is for. In short: one auto-accept control, three
categories where the client's own filing disagrees with the classifier, one
deliberate arithmetic error, one junk item name.

Email it from `afaq@mctechstudio.com` to `antillanca.yunt@mountaincreative.cl`.
Then, in order:

1. The webhook is reached at all (blocker 3), and a message addressed elsewhere
   on the shared Resend account is ignored (D-061).
2. The reception report comes back **before** any review — and once, with the
   key removed, to prove storage never waits for the model (D-064).
3. The review runs. Read `yunt_proposals`: the three disagreements should come
   back as EXP-15.8, ADM-1.8 and EXP-7.0, each citing evidence.
4. A second email arrives only because there are findings (D-064, D-065).
5. Reply with the exact confirmation line alone. Then check a bare "sí" does
   **not** approve, and that the line quoted further down a reply does not either.
6. Apply, then undo. Compare `final_code`, `decision` and `reviewed` before and
   after.
7. Edit one line of proposal B by hand, then try to apply it. It must refuse.

Steps 5-7 are the only parts of the chain step 0 could not reach: the exact-line
rule and the stale-proposal refusal live in SQL, not TypeScript.

    .venv-backend/bin/python scripts/90_yunt_live_test_undo.py --sender afaq@mctechstudio.com
    .venv-backend/bin/python scripts/90_yunt_live_test_undo.py --sender afaq@mctechstudio.com --apply

### Test 2 — one question thread  (MCT-152, 153)

Two emails, no attachment. First, one that must produce a real artefact:

> ¿Cuánto gastamos en fertilizantes por mes este año? Mándame el PDF con el
> gráfico mensual.

The PDF or chart must carry the filter, the accounting basis, the credit-note
rule and any truncation on its face. Every figure must be traceable to a tool
result — a number that is not is a bug, not a rounding difference (D-053).

Then one it must refuse:

> ¿Cuál es el margen de ganancia de FEROSOR AGRICOLA en lo que nos vende?

We hold what Antillanca paid, never what a supplier earns. Expect a refusal and
one row in `yunt_refusals`. Both requests are cleaned up by the same `--sender`
anchor.

### Test 3 — one purchasing email thread  (MCT-156, 157)

> PRUEBA — necesito 20 sacos de sal mineral para el Fundo Raíces, para el 30 de
> octubre.

Four facts are required; if one is missing it must ask, not guess. Confirm with
the exact line, and a request opens. Then take it to an order above CLP 500,000
and confirm the two-quotation rule refuses with fewer than two and allows with
two — through `create_purchase_order`, the same function the form calls.

Cleanup is anchored on `created_via = 'yunt'`, **not** on `title like 'PRUEBA%'`.
The Yunt drafts the title from the sender's own words, so the documented wording
filter would not have matched — which is exactly how the 2026-09-10 leftover
survived.

## Not racking up a bill

- Seven lines, not a month. Cost scales with lines.
- One change per run. Two changes and a failed run tells you nothing.
- Any failure that is not about wording or judgement gets reproduced in
  `npx tsx scripts/check-yunt-review-chain.ts`, free, and fixed there.
- `DUMP_PACKET=1 npx tsx scripts/check-yunt-review-chain.ts` writes the exact
  packet to `/tmp/yunt-review-packet.json` with no API call. Read it first.
- Watch the first runs for **quality**, not cost (D-076): a proposal citing
  evidence it was not given, a refusal it should not have made, reasoning that
  does not follow from the attached rows. Any of those means go back to Opus,
  and `agent/agent.ts` and `YUNT_REVIEW_MODEL` move together.

## What step 0 found, and what it fixed

`npx tsx scripts/check-yunt-review-chain.ts` drives the whole chain — six real
DTEs, 67 lines, 58 groups, staging, chunking, the submit guard, proposals, the
findings email, the confirmation prompt and the apply/undo payloads — with a
stub dispatcher and no API call. It also feeds eight deliberately bad answers in
and requires every one to be refused.

- **The classifier can answer `429 Rate exceeded.`** It did, against the live
  service, on the second run. `classify()` threw with no retry, the writer
  refuses to store lines with no category, and on the email path that is a
  reception report saying the attachment could not be read — nothing stored, and
  no webhook redelivery coming. Now retried three times on 429 and 5xx, never on
  a 4xx, with `scripts/check-classifier-retry.ts` behind it.
- Every `rpc()` argument name in TypeScript matches its SQL signature; all 24
  call sites check out.
- The precedent baseline reproduces exactly: 97.2% of proposals correct, 2.76%
  confidently wrong, on 400 held-out human-confirmed lines. Free and read-only.
- Two code comments still said `YUNT_ALLOWED_ADDRESSES` was unset. Corrected.

## Decisions settled before the run

1. **eve's eleven default tools are live** alongside our 22: `bash`,
   `read_file`, `write_file`, `web_fetch`, `web_search`, `agent`,
   `ask_question`, `todo`, `task_update`, `task_cancel`, `load_skill`. Two are
   real risks for an agent whose input is email: `bash`/`web_fetch` are an
   injection surface that the instructions mitigate by prompt rather than by
   capability, and **`ask_question` pauses the session for a channel to render a
   prompt** — the Yunt's only channel is email, which is the deadlock `apply.ts`
   and D-065 were deliberately built to avoid. `defaultTools: false` in
   `agent/agent.ts` turns them off. One line, reversible, and it touches the file
   D-076 guards.
2. **A model flag can be silently dropped.** `deterministicFlagRows` writes
   `source='deterministic'`, the model's findings write `source='yunt'`, and
   `yunt_flags` conflicts on `(batch_id, review_attempt, group_id, flag_type)`
   with `do nothing` — no `source`. So where both find an `amount_anomaly` on the
   same group, the deterministic row wins and the model's reasoning is discarded.
   Defensible; folio 999105 will show it happening.
3. The leftover `purchase_requests` row. Its **description** says
   `PRUEBA 4 ... Eliminar despues`; only its title does not, which is why the
   documented filter missed it. Safe to delete, but it is Afaq's row.
