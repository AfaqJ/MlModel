# MCT-189 — reliable invoice classification across ML and Yunt failures

Implements D-108. Branch: `afaq/mct-189-make-invoice-classification-reliable-across-ml-and-yunt`
in `../milk-company`, cut from `yunt`. The glassbox UI is **not** in this branch
(separate ticket and branch, Afaq 2026-09-18).

## What changes, in one paragraph

Today both doors read the files, call Cloud Run for every line, write the rows,
then ask the Yunt to review what was already written. After this change one
orchestrator settles the exact accounting rules locally, sends only what is left
to Cloud Run, and lets the Yunt review the *proposal*. Nothing becomes business
truth until a person approves, except in the one case where the Yunt is down and
the ML answered, which writes immediately and sends the complete audit report.

## The four cases (D-108)

| ML | Yunt | Unresolved after local rules | What happens |
|---|---|---|---|
| up | up | any | Yunt reviews the whole proposal → report → approval → one atomic commit |
| down | up | ≤ 10 | Yunt classifies those lines with precedent context → report → approval → commit |
| down | up | > 10 | Nothing saved. "Sistema no disponible, reenvía más tarde." |
| up | down | any | Commit immediately + complete audit report (inline ≤25 lines, else XLSX) |
| down | down | any | Nothing saved. "Retry later." |

Rejected batches keep no partial state and no retry queue. A resend starts a new
job.

## Pipeline

`src/lib/ingest/orchestrate.ts` (new), called by `/carga` and the inbound route.

1. `readFiles` — ZIPs and loose XML, unchanged (D-107).
2. Catalog resolution — unchanged.
3. **Local accounting rules** (new `src/lib/ingest/rules.ts`), in Cloud Run's
   order: petrol/transport → electricity meter → sales business rule → product
   lookup. Same normalization (`normalize_text`), same answers, `auto_accept`.
4. **Only unresolved lines** go to `/predict-batch`.
5. Merge by `input_id`. A missing or duplicated result aborts the batch.
6. Data-quality flags and the auto-accept downgrade — unchanged.
7. Availability decision per the table above.

### Rule data

`src/lib/ingest/rules-data.json`, generated from the authoritative CSVs in
`ML-model/app/data/` (`business_rules.csv`, `electricity_meter_map.csv`,
`product_lookup.csv`; the petrol plate/bidon sets come from
`app/inference/fuel_context.py`) by `scripts/generate-rules-data.ts`.
`taxonomy_aliases.csv` is **not** included: Cloud Run never loads it and all 22
of its rows are already in `business_rules.csv` (checked 2026-09-17).

The Cloud Run cascade stays until every direct caller uses the orchestrator.
`scripts/check-rules-parity.ts` proves the TS rules and Cloud Run answer
identically over a real month.

## Availability detection

- **ML down** = any `/predict-batch` failure after the existing three retries, or
  any row-level error. It is down for the whole batch; nothing partial is saved.
- **Yunt down at the start** = the eve dispatch is refused.
- **Yunt down mid-run** = `agent/hooks/review-failure.ts` on `turn.failed` /
  `session.failed`, matched to the job by the session id stored at dispatch.
  This is what catches credits running out halfway.
- **Yunt silent** = nothing heard 4 minutes after dispatch. Probe by reading
  `GET /eve/v1/session/:id/stream`, which is read-only. A failure event or a
  missing session means down; still working means keep waiting. **Never** re-POST
  the job to probe it: the same `operationId` returns the live session while it
  is resumable but starts a *second* review once it is terminal, and a follow-up
  message cancels an active turn (`eve/docs/channels/eve.mdx`).
- Either way the job then takes the ML-only row (commit + audit report) or, with
  no ML result, the "retry later" row.

## Staged approval

Migration `038_yunt_staged_batches.sql` extends `yunt_batches`:

- `status` gains `reviewing`, `awaiting_approval`, `rejected`.
- `mode` — `ml_yunt`, `ml_only`, `yunt_fallback`.
- `plan jsonb` — the complete normalized write plan (companies, invoices, items).
- `plan_hash text` — sha256 of the plan; approval must match it.
- `report jsonb` — the line report shown or sent.
- `approval_token uuid`, `sender text`, `review_session_id text`,
  `approved_at`, `approved_by`.
- `commit_yunt_batch(p_batch_id, p_plan_hash, p_confirmation_request_id)` —
  one transaction: verifies status, hash, sender binding and one-use token, then
  writes every document. Committing twice returns the first outcome.

No expiry (Afaq 2026-09-17, amends D-108). A staged batch closes on approval or
rejection. Resending the same files returns the same pending proposal.

## The Yunt's review, before the write

Reuses the existing compact grouping (`batch-review.ts`) over the prepared batch
rather than stored rows. Per group the Yunt returns one of:

- **keep** — the ML or rule category stands;
- **suggest** — a different category, with precedent evidence;
- **unsure** — the line stays review-required.

Client-facing wording never says the model was wrong (D-080). Stored in
`yunt_batch_proposals` by a new `submit_batch_proposal` tool that validates
category codes and evidence ids exactly as `submit_review_chunk` does.

### Fallback-only tools

When the ML is down, the review session is issued with `mode = 'yunt_fallback'`
on the job row. `fallback_precedent` (read-only search over settled lines) and
`submit_fallback_classification` are exposed by a dynamic resolver only for such
a session, and each executor re-reads the job row and refuses any other mode. No
process-global flag (D-108).

## Report and email

`src/lib/yunt/job-report.ts` builds one row per line: document, supplier,
item/description, quantity, unit, unit price, amount, proposed category,
decision source, review status, Yunt flag/reason. **Decision source and review
status are stored but never shown to the client** (Afaq 2026-09-18, amends
D-108): naming which engine settled a line, or its confidence, advertises where
the model is weak. The client's copy is grouped instead:

- **Confirmadas** — line, supplier, quantity, price, category.
- **Sugerencias del Yunt** — where it proposes a different category, with the
  precedent behind it.
- **Requieren revisión** — what nothing settled. Set them in the dashboard, or
  reply and the Yunt does it.

**One email per job**, not two: either the proposal or "sistema no disponible".
No reception acknowledgement — D-064's first email dies with the post-write path.

- ≤ 25 lines: inline table. Above: XLSX attachment (`xlsxAttachment`) with a
  short inline summary.
- Approval by email is the existing exact `SÍ, ADELANTE` first line on a direct
  reply (D-080, D-084), bound to sender, thread, job and plan hash.
- An emailed job is approved **only** by email (Afaq 2026-09-18). The dashboard
  is read-only for it.
- An uploaded job is approved on `/carga`, which shows the same lines.

## Provenance of an approved line

Every line in an approved batch is written with `prediction_source =
'yunt_applied'` (Afaq 2026-09-18). No migration: `014` already allows the value
and `src/lib/analytics/aggregate.ts:129` already excludes it from the automatic-
accept figure, so that figure reads 0% for new batches and keeps its meaning for
the stored history. What the model proposed stays recoverable from the stored
plan.

## What is removed

`reviewAfterWrite` from both doors, the findings email queue for intake, and the
post-write review dispatch. `apply_proposal` / `undo_application` stay: they
serve corrections to rows that are already stored.

## Proof

New `scripts/check-*.ts`, run by `check.sh`:

- `check-rules-parity.ts` — TS rules vs Cloud Run over a real month.
- `check-orchestrator-matrix.ts` — all five outcomes, both doors, with stubs.
- `check-staged-approval.ts` — hash, sender and token binding; double commit is
  a no-op; a changed plan invalidates an earlier approval.
- `check-job-report.ts` — the 25-line rule and every required column.
- Existing ingest/review checks stay green.

Then the real screens, signed in, on `localhost:3000`.

## Built, 2026-09-18 (`milk-company` `f77314e`)

All of the above, on branch
`afaq/mct-189-make-invoice-classification-reliable-across-ml-and-yunt`.

- `src/lib/ingest/rules.ts` + `rules-data.json`, generated by
  `scripts/generate-rules-data.ts`. **Parity proved**: 932 lines of a real month,
  443 settled by rule, 22 petrol held for review, 467 sent to the model, zero
  disagreements with Cloud Run (`scripts/check-rules-parity.ts`).
- `src/lib/ingest/orchestrate.ts` — the matrix, both doors. `runJob` replaces
  `writePreparedIngest`, which is deleted.
- `supabase/038_yunt_staged_batches.sql` — staged plan, `commit_yunt_batch`,
  `reject_yunt_batch`, `yunt_batch_proposals`, `yunt_similar_settled`, and
  `begin_yunt_review` redefined to run before the write. **Not applied yet.**
- `src/lib/yunt/pre-write-review.ts` (dispatch, bounded wait, stream probe),
  `batch-verdicts.ts`, `job-report.ts`, `job-mail.ts`, `approve.ts`,
  `post-commit.ts` (quality flags after the write, since a flag points at a
  stored line).
- Agent: `submit_batch_proposal`, `approve_batch`, `reject_batch`,
  `revise_batch_categories`, `fallback_precedent` (dynamic, double-gated), and
  `agent/hooks/review-failure.ts`.
- `/carga` now posts to `/api/carga` and answers on `/api/carga/decision`;
  `actions.ts` is gone.
- Removed: `after-write.ts`, `send_review_findings`, `submit_review_chunk`,
  `review-result.ts`, and the post-write half of `review-jobs` /
  `review-persistence`, with their checks.
- New checks: `check-rules-parity`, `check-orchestrator-matrix`,
  `check-staged-approval`, `check-job-report`. Full `./check.sh` green.

**Not done yet:** migration `038` pasted into production, and the real screens
driven signed in. Nothing is deployed.

## Proved live, 2026-09-19

Migration `038` applied (backup `backups/supabase_20260919T122424Z`). Live data
unchanged throughout: 5,195 invoices / 11,746 lines before and after.

| What | Result |
|---|---|
| Rules vs Cloud Run, real month | 932 lines, 0 disagreements |
| Three stored files on `/carga` | 3 already registered, 0 new, nothing written |
| Five new 2026-07 invoices, classifier off | `yunt_fallback` proposal: 3 suggestions, 2 left for a person, each citing real precedent — nothing written |
| Reject through `/api/carga/decision` | `{rejected:true}`, job closed, nothing kept |

**Fixed from that run:** the refusal for a verdict with no category now says what
to send instead; and "antes X" is printed only when the category actually moves
(in fallback the Yunt's own answer is also the recorded proposal).

**Still to prove:** ML and Yunt both up on screen, an approval writing rows, and
the email path end to end. The agent does not mount under plain `next dev`: run
`npx eve dev` on Node 24 (127.0.0.1:2000) and set `YUNT_EVE_URL` to it.
