# MCT-37 — invoice line-item classifier for Antillanca

Classifies Spanish invoice line items into accounting categories for
**Antillanca**, a Chilean dairy/agriculture client of Audisis / Grupo ProGestión.

**Status:** v1.4.1 live on Cloud Run — service `mlmodel`, `europe-west1`,
revision `mlmodel-00018-sll` (image `mlmodel:v1.4.1-names`), 100% traffic,
deployed and verified 2026-09-16. Trained on gold merged with every settled
Supabase label (D-099). Roll back with a traffic shift to `mlmodel-00017-vg5`,
`mlmodel-00016-p8z` (v1.4.0) or `mlmodel-00015-mjr` (v1.3.3). Prove a deploy
with `scripts/88_prove_deploy.sh <url>`. The
live database is **at baseline** (restored 2026-09-15): 5,195 invoices / 11,746
corrected lines, 78 categories, every purchasing and Yunt table empty. The
five handover-sample invoices are back, so `yunt-unseen-invoices.zip` is no
longer unseen. Baseline snapshot: `backups/yunt_team_handover_20260913/`; the
rows removed by the restore: `backups/pre_baseline_restore_20260915/`.
Before the handover sample, live and the staged payload were identical. Both
uploads of 2026-08-19 landed and were verified independently against live.
`002_add_manual_recategorisation_source.sql` is **applied to production**; live
carried all 8 `prediction_source` values; there are **six** now (D-047). Latest
backup: `backups/supabase_20260903T054820Z/`.
**Branch:** `yunt-backend`.
Frontend: branch `yunt` in `../milk-company` (the only frontend checkout) is
pushed at `e2f7f48` (2026-09-21), whose Preview carries MCT-189, the agent's clock and D-111/D-112; the Resend
webhook points at that Preview, so inbound invoice mail runs the new pipeline.
Production (`milk-company.vercel.app`) still serves the 2026-09-16 build. Afaq holds the production deploy. The Yunt uses
Vercel AI Gateway through `AI_GATEWAY_API_KEY`; D-101 supersedes the earlier
direct-Anthropic decision D-077.
The `MCT-166` cache edits are parked as commits on local branch
`parked/mct-166`; do not fold them into feature work. Migrations
`004`–`042` are live (`039`/`040` MCT-190's read grants and `yunt_reports`; `041` confirmation follows the thread, D-110; `042` lets the dashboard answer any waiting job, D-111 — all pasted 2026-09-21). `024`, `026` and `027` are confirmed by behaviour;
`023` and `025` are believed live but were never re-verified — all are
idempotent, so re-pasting settles it. Ten audit
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
deployed model emits **76** — read it from `artifacts/v1.4.1-int8/labels.json`
(`classifier_classes`), never by subtracting from the category table. Every
category with a settled label anywhere is trained, deterministic rule or not
(D-095, D-099); only `EXP-15.6` has no rows at all. The training set is
`Data/candidates/retrain_2026_09_16/` — gold merged with every settled Supabase
label, 4,251 distinct model inputs. `Data/gold/_master_gold.csv` alone is
**not** the labelled set and training from it left three categories
unlearnable. Many classes have very
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
- **Wording alone does not decide a category, and assuming it does manufactures
  ambiguity that is not there.** Measured 2026-09-10: 29 item wordings appeared
  to be filed under several categories, and every one turned out to be
  deterministic. **23 wordings / 882 lines are decided by `meter_code`** —
  different electricity meters are different cost centres. **6 wordings / 625
  lines are petrol, decided by the DTE's `<Transporte><Patente>`** (plate →
  `ADM-1.4`, jerrycan → `EXP-11.4`, see `docs/CLIENT_CONVENTIONS.md`). Both are
  now readable: `dte.ts` keeps the plate as `invoices.transport_plate` and `025`
  ranks an exact `meter_code` match above same-wording evidence (D-068), which
  cut confidently-wrong proposals from 5.75% to 2.76%. Rows written before
  2026-09-10 still carry no plate. Before concluding the client's labelling is
  inconsistent, look at what else the row carries and read
  `CLIENT_CONVENTIONS.md` (`MCT-164`, closed).
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
the same corpus — identical numbers, asserted as equalities. The superseded
Python reference was deleted under D-079; change
`../milk-company/src/lib/ingest/` for ingestion work.
**Two doors reach one pipeline** — `/carga` takes uploaded ZIPs or loose XMLs, and
`POST /api/yunt/inbound` takes email through Resend (ZIP or XML attachments, D-107); both call `runIngest`, and
the upload page is permanent rather than a stopgap (D-060). Both doors now call `runJob`.
**The email path carried a real ZIP on 2026-09-19** and worked end to end on
Preview: two July invoices in, proposal mailed back, nothing written, a natural
"descarta esto" reply closed the job and was answered. An emailed approval
writing rows was proved live on 2026-09-21 (3 synthetic invoices / 4 lines, then removed). Migrations `021` and `027` grant exactly what
the operator needs — any signed-in user, because v1 has no roles (D-052) — and
both are live; a signed-in person has saved through `/carga`, the replay changed
nothing, and the deterministic quality flags land. **`021` missed `yunt_flags`
and that was not a cosmetic gap:** the flag write happens inside the review, and
`reviewAfterWrite` swallows its own errors by design (D-064), so the refusal
skipped the entire post-write review while the screen reported success. When
something that should have written rows wrote none, read
`milk-company/.next/dev/logs/next-development.log` before theorising.
Never bypass RLS with the service key from a browser-triggered action; the
absence of a service key in `.env.local` is what proved the save went through
as the user. Two environment variables fail *closed* and look like bugs if you
do not know: an empty `YUNT_ALLOWED_ADDRESSES` means the Yunt can mail nobody,
and an unset `YUNT_INBOUND_ADDRESS` means it ignores every message. Both are
**set on Vercel Preview**, but every variable there is sensitive-flagged and
reads back as `[SENSITIVE]`, so their values cannot be confirmed from the CLI —
that unreadability is what made earlier docs claim the allowlist was unset. That
second one matters because the Resend account is shared and **a Resend webhook
cannot be scoped** — every endpoint on the account receives every inbound
message, so filtering by recipient is our job (D-061).
**That order is now inverted on `yunt` (merged 2026-09-19, `46b25af`), so
Preview runs it: the Yunt reviews the proposal and nothing is written until a
person approves (D-108 and its 2026-09-18 amendments, MCT-189,
`docs/MCT_189_PLAN.md`). One orchestrator, `src/lib/ingest/orchestrate.ts`,
serves both doors; `writePreparedIngest`, `reviewAfterWrite`,
`submit_review_chunk` and `send_review_findings` are deleted. The client's own
accounting rules run in Next.js from `src/lib/ingest/rules-data.json`,
generated from this repo's CSVs — proved identical to Cloud Run on 932 real
lines. Production still serves the 2026-09-16 build, which is the old order
below; D-064's post-write review survives only as D-108's ML-only row, and
migration `038` already stopped it starting.** The old order, for reading
production: the deterministic ingest
writes even when Claude is unavailable. Immediately
after a successful write, the Yunt reviews every line through compact groups,
then sends a second email only when it has a finding or proposal; the first
reception email never depends on the agent (D-064). That reply is sent without
asking — it is the second half of the sender's own exchange, and the outbox, not
the model, decides whether anything goes out (D-065). Approval-gated apply and
exact undo now exist locally; migration `014` is live, and the approved
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
| **What to run when the key is wired** | **`docs/GO_RUNBOOK.md`** |
| **How to test against the real API without wasting it** | **`docs/YUNT_TEST_PLAN.md`** |
| **What the glassbox tests did, where each state shows, how to redo them** | **`docs/GLASSBOX_TEST_GUIDE.md`** |
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

Two virtualenvs, deliberately. `.venv-train` has PyTorch; `.venv-backend` does
not, because PyTorch must never reach the production container. The Yunt's
TypeScript checks run from `../milk-company/check.sh`.

```bash
# classifier
.venv-backend/bin/python -m pytest tests/ -q
```

**Never re-load the whole database.** Every correction has been a small, named
set of rows; re-writing 11,746 lines to change a handful is how sessions get lost.
Back up first (`scripts/81_backup_supabase.py`), then write over PostgREST with a
dry run, touching only the rows in scope.

**A feature is not finished until it has been used in the browser.** Start the
dev server and drive the real screens on `localhost:3000` — click the buttons,
submit the forms, read what comes back. Type checks and `check.sh` prove the code
runs; they do not prove the feature works. Every defect found on 2026-09-10 —
the dead "Nueva solicitud" button, the redirect that landed on a 404 after
saving, the home-screen rule that never rendered, the accent-stripped supplier
name — passed every automated check and would have reached Antillanca. Ask Afaq
to sign in when a screen needs a session; never ask him to do the checking.

Deploy is **container-only** — `gcloud builds submit` → Artifact Registry →
`gcloud run deploy`. Git is never in the path, which is what keeps the 278 MB
`.onnx` from becoming an LFS pointer. `.gcloudignore` is **required**: without
it `gcloud` falls back to `.gitignore`, which excludes `artifacts/*`, and the
image builds fine with no model inside.
