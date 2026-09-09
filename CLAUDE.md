# MCT-37 — invoice line-item classifier for Antillanca

Classifies Spanish invoice line items into accounting categories for
**Antillanca**, a Chilean dairy/agriculture client of Audisis / Grupo ProGestión.

**Status:** v1.3.3 live on Cloud Run — service `mlmodel`, `europe-west1`,
revision `mlmodel-00014-lrp`, 100% traffic. Supabase holds 11,746 corrected
lines as of 2026-09-03: **7,927 auto-accepted, 3,819 in review**, 78 categories.

**Live and the staged payload are identical — nothing is pending.** Both
uploads of 2026-08-19 landed and were verified independently against live.
`002_add_manual_recategorisation_source.sql` is **applied to production**; live
carried all 8 `prediction_source` values; there are **six** now (D-047). Latest
backup: `backups/supabase_20260903T054820Z/`.
**Branch:** `yunt-backend`.
Frontend: branch `yunt` in `../milk-company`, off `feature/dashboard`. The
purchasing forms and read-only ingestion paths are pushed through `4035fef`;
twenty-four further commits are local and unpushed through `dc76546`. Migrations
`005`–`010` are **live**; `011`–`017` are required and not live. Ten audit
findings are still open as decisions, in that
repo's `docs/OPEN_QUESTIONS_2026_09_03.md`; `docs/` there is gitignored by
Afaq's deliberate choice, so those notes live on disk only.

The dashboard classifier adapter was exercised against the real Cloud Run URL
on 2026-09-09: one prediction and a ten-item `/predict-batch` both returned
complete v1.3.3 results. This proves the model connection, not the still-unrun
Resend → Vercel → Supabase end-to-end path.

`app/data/product_lookup.csv` was audited entry by entry on 2026-08-18 by an
independent Codex pass — **1 finding in 696, not actionable.** It is clean; do
not re-audit it. The client brief listing every open question is at
https://claude.ai/code/artifact/47769557-4221-4b7d-a29c-00ca2d3d88a7

**The canonical catalog migration is complete in production (D-044, D-045).**
All three steps ran; step C closed it on 2026-08-26. Live `item_catalog` is
**4,002 rows plus 8 aliases** for the same 11,746 invoice lines, down from 5,411
(4,029 after the migration; P-01 merged 27 livestock rows on 2026-08-26),
and now carries a unique index on the normalized `item_name`
(`item_catalog_normalized_name_uidx`). Verified against live: 0 name mismatches,
0 dangling or null `catalog_item_id`, and the raw-evidence SHA `f87b6fde…`
identical between live and payload. Pre-migration backup:
`backups/supabase_20260825T190718Z/`.

## What this is

Input is an invoice line: `item_text`, `description`, `provider`, plus the
COMPRAS/VENTAS direction from the folder the document came from. Output is top-3
category codes with confidence, and a decision: `auto_accept` or
`review_required`.

The product is **human-in-the-loop by design**. 78 categories are live; the
deployed model emits **67** — read it from `artifacts/v1.3.3-int8/labels.json`
(`classifier_classes`), never by subtracting from the category table. The six
added on 2026-08-14/17 are rule-assigned and cannot be predicted (D-028); four
more carry `trained: false`. `Data/gold/_master_gold.csv` holds 2,577 rows
across 73 classes, 2,329 of them distinct model inputs. Many classes have very
few examples, so the model cannot be trusted alone: the review gate is a feature,
not a shortfall. Of 11,746 lines, 7,927 (67%) are auto-accepted and 3,819 (33%)
sit in review — but **that 67% is contaminated and reads high**: the dashboard's
write sets `decision='auto_accept'` on a *human* pick, and `aggregate.ts:104-107`
counted every such row as automatic. **Fixed 2026-09-09** — the count now
excludes `prediction_source = 'user_selected'`, guarded by
`scripts/check-auto-accept-rate.ts`, which was verified to fail against the
pre-fix code. The 67% above is the old contaminated figure.

The system is two halves that are easy to confuse: an **offline labeling
pipeline** (raw XML → gold → Supabase) and an **online classifier service**
(FastAPI on Cloud Run). The classifier is a tool used by the pipeline.

## Hard limits

- `predicted_code` is **never** a final business classification when
  `decision=review_required`. Displaying it as one caused the production
  incident. Root cause is D-001; the full trace is in git history.
- Any dedup key on training rows must contain **every field the model
  consumes**. The input template is now
  `[transaction_type] | item_text | description | provider`, so dedup happens on
  the *built* string — see D-013, which supersedes D-001's narrower key. A key
  narrower than the input is what destroyed 47 milk-sale rows.
- Never promote an unaudited row to gold. See `docs/LABELING_RULES.md`.
- A client-sourced label outranks any number of rows that disagree with it.
  See `docs/CLIENT_CONVENTIONS.md` — counting rows got this wrong twice. Where
  the client filed the same kind of item consistently, that filing beats the
  model too (D-040); the model disagreeing is usually the undertraining.
- Never resolve in the payload a question currently open with the client (D-041).
- **Before acting on any `D-NNN`, say which one and what it makes you do, in
  plain language, and wait** (D-043). Not only when it conflicts with what Afaq
  asked — every time it is load-bearing for the next step.
- Read the backing gold `source`, never the `prediction_source` tag. It is six
  values now (D-047) — `model`, `product_lookup`, `meter_lookup`, `business_rule`,
  `cleanup`, `user_selected` — and `cleanup` means only "a pass we ran once".
  The provenance of the 2026-09-02 client labels is in
  `reports/client_reply_2026_09_02/`, never in this column.
- Supabase is already loaded and **there is no standing re-load path.** The
  numbered one-shot uploaders were deleted on 2026-08-26: each was written
  against a database state that no longer exists, and re-running one would have
  fought the canonical catalog migration. Do not re-create them. Every *offline*
  change to live data is a scoped write over PostgREST (`scripts/supabase_rest.py`)
  that touches only the rows it names, dry run first, backed up first.
- **The dashboard is now the one exception, and the only online writer** (D-048).
  It assigns categories through a Next.js Server Action carrying the user's
  session — never a browser-side call, because the publishable key is visible to
  anyone. Row-level security is the gate: anon sees **0 rows in every table**, and
  read and write are granted separately, so a `SELECT` policy proves nothing about
  `UPDATE`. Never write `needs_review`; it is GENERATED and returns 400.
- Never modify `Data/Raw_Data/` — it is the only irreplaceable thing here.
- Never overwrite `artifacts/v1.0.0/` or `artifacts/v1.1.0/` (protected paths).
- Never release on aggregate accuracy alone. The income slice is a mandatory
  gate — see `docs/TEST_CHECKLIST.md`.
- Supabase writes require an explicit flag. `Temp_Inference/.env.loader` holds
  live keys: never echo them, never commit them.
- A class with fewer than 2 examples cannot be trained and must fail **loudly**.

**A second workstream is open: the Yunt**, a digital collaborator over this
data and the dashboard. The scope sent to the team (`docs/Yunt_scope_v1.docx`,
19 items) is a **client-facing menu and is not authoritative** — things were
settled by discussion after it went out, so where it and `DECISIONS.md`
disagree, the decision log wins (D-059). Linear carries only nine issues, made
for recently discovered work; it is not the map either. Ingestion is deterministic
code, not the agent (D-051); purchase orders v1 is two forms with no roles and
no approval (D-052); open questions are answered by ~5 parameterised query
tools with every number computed by code, never by the model (D-053). Rodrigo
wants ingestion from Audisoft's API rather than email, but it returns 401 on
every credential form and is blocked on them (D-054); email stays the fallback.
The recipe is `docs/YUNT_IMPLEMENTATION_PLAN.md`; what still needs Afaq is
`docs/YUNT_OPEN_DECISIONS.md`. **The Yunt is an [eve](https://vercel.com/eve)
agent in Next.js on Vercel, not a Python service** (2026-09-09): tools are
TypeScript files in `agent/tools/`, `approval` is a built-in field, and
execution is durable. GCloud keeps only the classifier. The ingestion pipeline
has been ported to `../milk-company/src/lib/ingest/` and verified by replaying
the same corpus — identical numbers, asserted as equalities. `yunt/` here is the
reference implementation and is deleted once the port completes.
**Two doors reach one pipeline** — `/carga` takes an uploaded ZIP, and
`POST /api/yunt/inbound` takes email through Resend; both call `runIngest`, and
the upload page is permanent rather than a stopgap (D-060). Both routes now
import the atomic writer and the post-write review in local code. **That is not
the same as working live:** the email path has never carried a real ZIP, and
`/carga` uses the signed-in Supabase client while the new writer/review objects
are service-role-only. Its first real save is therefore blocked until a proper
operator permission is added; do not bypass that with the service key. Two
environment variables fail *closed* and look like bugs if
you do not know: an empty `YUNT_ALLOWED_ADDRESSES` means the Yunt can mail
nobody, and an unset `YUNT_INBOUND_ADDRESS` means it ignores every message. That
second one matters because the Resend account is shared and **a Resend webhook
cannot be scoped** — every endpoint on the account receives every inbound
message, so filtering by recipient is our job (D-061).
The deterministic ingest writes even when Claude is unavailable. Immediately
after a successful write, the Yunt reviews every line through compact groups,
then sends a second email only when it has a finding or proposal; the first
reception email never depends on the agent (D-064). That reply is sent without
asking — it is the second half of the sender's own exchange, and the outbox, not
the model, decides whether anything goes out (D-065). Approval-gated apply and
exact undo now exist locally; migration `014` is not live, and the approved
write uses the pending `yunt_applied` provenance value (D-066). Two facts drive
the design.
The classifier **auto-accepts only 8% of the
corpus** while deterministic lookups settle 44%, and 68% of review rows are
undertrained wordings rather than ambiguous items — so a category proposal is a
**precedent search in SQL**, with the model grouping and explaining, never
computing. The agent is a post-write reviewer and conversational front door;
ingestion stays plain code that succeeds with the agent unavailable.

**The DTE XML is ISO-8859-1 and carries no `encoding=` declaration**, so any
parser that assumes UTF-8 corrupts every accented character. Do what
`scripts/10_extract_line_items.py` does at lines 85-87: try UTF-8, fall back to
latin-1.

## Where to look

| Need | File |
|---|---|
| Where we are, recent sessions, next steps | `docs/STATE.md` |
| **What the Yunt will do, as sent to the team** | **`docs/Yunt_scope_v1.docx`** |
| **How every manual case becomes automated** | **`docs/AUTOMATION_PLAN.md`** |
| How the system is built | `docs/ARCHITECTURE.md` |
| The complete staged Supabase payload | `reports/recovery_v1_3_3/supabase_upload/` |
| Why it is built that way | `docs/DECISIONS.md` |
| **How a claim is allowed to become a number** | **`docs/EVIDENCE_RULES.md`** |
| What may enter the gold dataset | `docs/LABELING_RULES.md` |
| How the client wants things labelled | `docs/CLIENT_CONVENTIONS.md` |
| What counts as proof before shipping | `docs/TEST_CHECKLIST.md` |
| How to undo a deploy, an upload, a retrain | `docs/ROLLBACK.md` |
| Hard boundaries, in full | `docs/CONSTRAINTS.md` |

Every file listed above is current. Nothing here is historical — superseded
docs are deleted, not archived, and live only in git history.

## Conventions

Three virtualenvs, deliberately. `.venv-train` has PyTorch; `.venv-backend` does
not (PyTorch must never reach the production container); `.venv-yunt` has neither
the ML stack nor its tests, because the Yunt service ships without them. The two
suites therefore run separately — `tests/` holds both and neither venv can
collect the other's files.

```bash
# classifier
.venv-backend/bin/python -m pytest tests/ -q --ignore=tests/test_yunt_batch.py \
    --ignore=tests/test_yunt_dte.py --ignore=tests/test_yunt_inbound.py

# yunt — 30 tests
.venv-yunt/bin/python -m pytest tests/test_yunt_*.py -q
```

**Never re-load the whole database.** Every correction has been a small, named
set of rows; re-writing 11,746 lines to change a handful is how sessions get lost.
Back up first (`scripts/81_backup_supabase.py`), then write over PostgREST with a
dry run, touching only the rows in scope.

Deploy is **container-only** — `gcloud builds submit` → Artifact Registry →
`gcloud run deploy`. Git is never in the path, which is what keeps the 278 MB
`.onnx` from becoming an LFS pointer. `.gcloudignore` is **required**: without
it `gcloud` falls back to `.gitignore`, which excludes `artifacts/*`, and the
image builds fine with no model inside.
