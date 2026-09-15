# STATE — where this project is right now

Updated every session. Last 5 sessions only; anything older that still matters
lives in `DECISIONS.md`.

## Session — 2026-09-15 (b)

**Yunt documents themed and rebuilt; two chart bugs found on live and fixed.**
Frontend `yunt` is at `8809120` (after `9ec8689`), Preview Ready.

- One document theme, `src/lib/documents/theme.ts` (Pastizal hex copied from
  `globals.css`), and a small dependency-free PDF canvas,
  `src/lib/documents/pdf.ts`. Report PDF: moss band, criteria in plain Spanish,
  total/groups/period tiles, optional chart, detail table with total row, page
  footers. Every chart request now arrives **inside the PDF**; the loose `.svg`
  attachment is gone (D-093). Spreadsheet uses the same colours, CLP number
  format, a total row only when every group is present. Purchase-order PDF
  rebuilt to match the print page: black and white with a sage-deep rule and
  labels; the print page got the same accents. Criteria never print query
  mechanics (`sort`, `limit`) and never English enum values.
- Dashboard pages no longer double the shell's padding or cap their width
  (`/carga`, solicitudes, órdenes, productos, historial, extractor,
  levantamiento). `/carga` stat tiles got a card ground.
- Proof: `scripts/render-yunt-documents.ts <dir>` writes every file type from
  sample data with no email or model call; the four `check-*` document scripts
  pass; a live test order (`SOL-2026-0015` / `OC-2026-0010`, $370.000) was made
  through the screens, its print page and PDF route checked, then deleted.
  Three live emails (PDF by month, pie by category, sheet by supplier) all came
  back as themed files.
- **Bug found on live:** the pie drew 10 of 69 categories and took each share of
  those ten — "24,3%" was really 17,1%, and the centre showed $2.841 MM against
  $4.029 MM. Now the rest is one "Otros" slice and shares use the query total;
  share charts refuse measures that do not add up (D-094). Carried over from the
  old SVG code; the sample data had only 8 categories, so no local render could
  show it.
- **Bug found locally:** footers read "Página 1 de 1" on multi-page reports
  (page count read while later pages were set aside). Both have regressions in
  `check-yunt-report-periods.ts`, each verified to fail without its fix. The pie
  fix was then rendered from the real live aggregate (read-only).
- **Blocker:** the retry email got no reply — Vercel logs show the Anthropic API
  refusing with *credit balance is too low*. The Yunt answers nothing until
  credits are topped up. No token usage is recorded anywhere we own (no admin
  key, nothing logged per request); real spend is only in the Anthropic Console.
- Cleanup: the test order, request and all four inbound requests deleted by
  exact id; every purchasing/Yunt table is 0, invoices 5,195 / lines 11,746.
  Request counter now at `SOL-2026-0016`. Two empty Outlook drafts from the
  session remain in Drafts (Outlook did not remove them).
- **Gotcha — Outlook web drops the first keystrokes** of the To field after a
  click, turning the address into `tillanca.yunt@…`, and focus jumps between
  open drafts. Zoom on the chip before sending; Backspace the chip and retype
  with the field already focused; set Subject with `form_input`.
- **Gotcha — poppler renders Helvetica-Bold as regular on this Mac.** The file
  was right (`pdffonts`); render with `sips` (Quartz) to judge a PDF by eye.
- **Gotcha — the eve request sends no `cache_control`**, so every model turn
  re-pays the full system prompt and tool list. Worth checking before volume.

## Session — 2026-09-15

**Live database restored to baseline.** Compared every tracked table with
`backups/yunt_team_handover_20260913/`: the only differences were the 09-14
repeat-purchase test data (fixture supplier *Proveedor Prueba Recompra*, folio
`TEST-BROWSER-030`, its catalog item and line, `SOL-2026-0009`–`0014`,
`OC-2026-0004`–`0009`, 13 inbound requests, 9 drafts) and the five detached
handover invoices / twelve lines. A scoped script deleted exactly those rows and
re-inserted the sample with original IDs; counts, core ID sets and the 17
restored rows' fields were verified against the snapshot. Deleted rows and the
script: `backups/pre_baseline_restore_20260915/`. A full wipe-and-reload was
considered and rejected: same end state, more risk. Request/order number
counters were not reset — the next request is `SOL-2026-0015`.
Gotcha: a `select=*` read of every table in parallel hung for 14 minutes; per-
table `count` plus ID-column reads answered the same question in seconds.

**UI/UX polish merged and pushed to `yunt`** (`mountain-creative/milk-company`,
head `55f8797`, Preview rebuilds from it). Everything below was driven in the
browser at 390 / 700 / 900 (sidebar open) / 1280 / 1600 px, and `check.sh` is
all green with 0 lint errors and a passing build.

- Numbers use Chilean format in both UI languages: `4.192`, `$9.260 MM`,
  `9,8%` — one formatter, `src/lib/dashboard/format.ts` (D-090).
- Sidebar highlights the current page; Órdenes de compra, Nueva solicitud and
  the print-order page have back links. Leftover hardcoded text translated,
  including a translated file picker (`src/components/file-input.tsx`).
- Empty states have icon + action; orders month filter is a month-level
  calendar (`src/components/month-picker.tsx`); duplicate filter title removed.
- Layout sizes on the space beside the sidebar, not the screen (container
  queries): filters collapse behind one "Filtros" button and open as an even
  2-column grid; KPI grid goes 2→4 columns; KPI figures scale with the card.
  Header shows icon-only language/role pickers below tablet width, and the
  title only when it fits (D-092).
- Pastizal theme: moss sidebar, oat ground, sage actions, wheat headline tile,
  moss table header row with oat frozen column and centred titles (D-091).
- Hydration error in the pending KPI card fixed (skeleton `div` inside `p`).
- Sidebar names stay "Solicitudes de compra" and the inner page stays
  "Órdenes de compra" — Afaq decided against renaming.

**Folders consolidated.** The `.worktrees/ux-operational-home` copy is deleted;
`../milk-company` is the only frontend checkout, on `yunt`, clean apart from
generated `AGENTS.md`/`CLAUDE.md`. The previously uncommitted MCT-166 cache
edits and two script edits (`preflight-go.ts`, `check-yunt-test-fixture.ts`)
are parked as two commits on local branch `parked/mct-166` — not for merge.
The unreachable mock page `productos/[id]/ordenes/[orderId]` stays as is.

Performance review (read-only, nothing changed): Analytics downloads every
invoice line for the range into the browser (~12 pages) and aggregates in
`dashboard-view.tsx:240-256`; the DB-side aggregate is only the catalog's
`item_summary` view. The catalog loads all 4,002 summaries server-side, so its
search covers every item. Sidebar prefetch is kept deliberately.

Gotchas: switching branches or rebasing while `next dev` runs replays each
intermediate commit, so the page briefly shows old themes — a dev artefact, not
a user-facing bug (production CSS verified to contain only Pastizal tokens).
After a branch switch Turbopack kept serving the old CSS until the dev server
was restarted. In a worktree whose `node_modules` is a symlink, Turbopack
refuses to start; `--webpack` works.

## Session — 2026-09-14

The repeat purchase-order flow is complete in `../milk-company` and pushed to
`mountain-creative/milk-company` branch `yunt` at `fe5ea4b` (following
`19337ca`). The branch Preview is
`https://milk-company-git-yunt-mountain-creative.vercel.app`. It is not the
production app. The classifier/data-pipeline repository is separately
`AfaqJ/MlModel`, branch `yunt-backend`; do not treat the two as one branch.

The final visible Outlook coverage ran for all three purchase cases: a new
purchase follows the normal request-plus-order path; an exact recent historic
purchase offers a repeat with supplier, RUT, historic category and price; and a
similar spelling is only suggested until the buyer explicitly selects the
historic item. A changed repeat invalidates the previous confirmation and
creates a new draft. Local TypeScript, Next build, Eve build, and
`scripts/prove-030-repeat-purchase-orders.sh` passed. Migration `030` is live.
D-088 remains the controlling decision.

The temporary repeat fixture and its test records were removed on 2026-09-15
as part of the baseline restore.

Dashboard upload was demonstrated locally and on Preview as a dry run only,
using a temporary copy outside the repository. It shows deterministic catalog
matches, category/decision suggestions and a `Save to database` second step.
No save occurred. The dashboard does not start a Yunt conversation or send a
review email: after a real save it can dispatch EVE review work, but today has
no review inbox or notification surface. The email ingestion route is the
conversational route. This is a product gap, not evidence of a failed upload.

Team handover additions are uncommitted in `handover/yunt-team-test/`:
`TEAMS_MESSAGE_REPEAT_FLOW.md`, `yunt-real-outlook-threads-english.pdf`, and
`YUNT_TECHNICAL_ONBOARDING_TODO.md`. Preserve the existing
`yunt-unseen-invoices.zip`; it is Rodrigo's intentional test sample.

Gotcha: UI contributions go to `mountain-creative/milk-company:yunt`, never
`yunt-backend` (that is this classifier repo). Stage named paths only.

## Session — 2026-09-13

Team handover prepared after acceptance. Verified the saved baseline, took a
fresh full 23-table snapshot, extracted 5 unchanged original XML invoices / 12
lines, and detached only those exact IDs. Proved restore to identical row hashes,
then detached again for team testing. The five core tables also match the
independent 2026-09-11 backup field for field (zero changed/added/removed rows
before detachment). Snapshot/undo controls:
`backups/yunt_team_handover_20260913/` and `scripts/91_yunt_team_sample.py`.
The real app XML parser confirms all identities/amounts; no paid model call.

Preview `a16fc51` is Ready: exact @mctechstudio.com matching and Cristian's Gmail
are added through `YUNT_ADDITIONAL_ALLOWED_ADDRESSES`; the unreadable existing
allowlist stays untouched. Focused checks and build passed. Teams copy, HTML
talking script, field meanings and reference labels live in
`handover/yunt-team-test/`. D-087 records the changed test boundary. Gotcha:
Vercel sensitive values cannot be read back; an additive setting avoided
overwriting unknown recipients. Browser policy blocked local HTML visual QA.

Delivered a boss-facing English HTML capability guide at
`docs/YUNT_CAPABILITY_GUIDE.html`. It states the supported workflows,
hard guardrails, limitations and concrete answers to the operational “what if?”
questions. It is deliberately specific about the difference between model
interpretation and database enforcement.

Applied migration `029` live, then ran the final live acceptance. Commit
`8bec6c2` is pushed to the `yunt` preview branch: an expected purchase-order
two-quotation preflight now produces a concise request for the missing quote
instead of leaving an inbound request open. The error condition is recognized
narrowly; unrelated database failures still surface normally.

Live proof: a neutral email created `SOL-2026-0002`; one CLP 600,000 quotation
was refused before confirmation; the second quotation unlocked an exact order
proposal; a direct `SÍ, ADELANTE` created `OC-2026-0002`, closed the request,
and emailed its PDF to the requester. Separate live emails returned the requested
styled XLSX, PDF and SVG monthly reports. `MCT-152`, `MCT-157` and parent
`MCT-142` were closed in Linear with this evidence. Test-only records were
removed and every tracked live table again matches the baseline exactly.

The purchase-request form now surfaces the three newest invoice prices as soon
as a known catalog item is selected. It offers latest-price × quantity as an
explicit Estimated budget button; it never overwrites typed planning data
(D-086). Local UI proof used Bodega lecheria Maitén: CLP 2,697,000 per recorded
unit × 20 offered CLP 53,940,000, and an entered CLP 123 remained unchanged when
quantity changed. Regression check, ESLint and production build passed.

## Now

**Next session is ML retraining** on the latest labelled data — see `Next` 1.

**Blocked on Afaq: Anthropic API credits are exhausted.** Every Yunt email
reply fails until they are topped up (seen 2026-09-15 14:02 in Vercel logs).

**Yunt documents are themed and on the `yunt` Preview (`8809120`)**: report
PDF with charts inside it, spreadsheet, purchase-order PDF, one theme file.
See the 2026-09-15 (b) entry.

**The repeat-purchase feature is pushed, deployed to the `yunt` Preview, and
visibly accepted in Outlook for new, exact-repeat and similar-name flows.**
Migration `030` is live. The current Preview is
`https://milk-company-git-yunt-mountain-creative.vercel.app`. The app is on
`mountain-creative/milk-company:yunt`; the classifier/data work is in the
separate `AfaqJ/MlModel:yunt-backend` repository.

**The dashboard is not yet a Yunt conversation surface.** It can preview a ZIP
and, after a save, trigger background review; it currently does not show the
result as a Yunt discussion or notify the uploader. Email remains the working
Yunt interface for conversational review and purchasing.

**Purchase planning is clearer in the dashboard.** A known item now shows its
three newest recorded prices during request entry, and its most recent unit
price can calculate a budget suggestion after the buyer provides quantity. The
buyer must press the button to use it; no input is automatically changed.

**The UI/UX polish and the Pastizal theme are on `yunt` (`55f8797`) for Preview
review before production.** See the 2026-09-15 entry for what changed.

**Closed on live evidence: `MCT-150`, `MCT-141`, `MCT-149`, `MCT-160`, and
`MCT-153`.**

| Proved live | Evidence |
|---|---|
| Approve a proposal | `096b6abe` ADM-1.4 -> ADM-1.8; `5b204210` -> EXP-2.6 |
| Reject one | Honoured, nothing touched |
| Correct with an unsuggested category | Staged, restated, applied |
| Undo | All four before-values restored exactly |
| Approval phrase not on first line | Refused, nothing applied |
| Query with no data (2024 fuel) | No data, no invented number, no empty Excel |
| Query with data (2025 fuel) | CLP 93.146.229 = independent recount, to the peso |
| Spreadsheet | Opened: BOM, semicolons, accents, filter header, rows sum exact |
| PDF | Opened: qpdf clean, 12 months chronological, total exact |
| Refusal | Out-of-scope question refused; genuine `yunt_refusals` row written |
| Fresh inbound ZIP | Folios `999201`–`999206`: 6 new documents, 7 lines and a reception report |
| Grouped findings email | One Sonnet review: 3 concrete flags, 4 unapplied proposals, each citing its prior records |
| Purchase request | Missing year prompted a question; exact confirmation opened `SOL-2026-0001`, no supplier contacted |
| Purchase order | One quote at CLP 600,000 was refused before confirmation; two quotes then direct exact confirmation created `OC-2026-0002`, closed the request and emailed the requester `OC-2026-0002.pdf` |
| Styled report outputs | Real emails returned the themed XLSX, the report PDF and (2026-09-15) chart reports drawn inside the PDF; the loose SVG attachment is gone (D-093) |

**Bugs found and fixed (all shipped):**
1. Proposal lookup had **never once worked on live** (D-081) - it compared
   Resend's API uuid to an RFC Message-ID. Earlier "success" was a manual script.
2. Client-facing reason printed model filler instead of the precedent (D-080).
3. A category written as the Yunt prints it (`EXP-2.6 Otros Gastos Salud Animal`)
   matched nothing.
4. Report replies delivered literal `\n` instead of line breaks.
5. Monthly chart ordered by amount, not by month - the line was not a trend.
6. Charts capped at 10 rows, silently dropping April and June, no disclosure.
7. A reply promised a PDF and carried an .svg.

**Live is at baseline (restored 2026-09-15).** 5,195 invoices / 11,746 lines /
461 companies / 4,002 catalog items / 78 categories; every purchasing and Yunt
table is empty. The handover sample is back, so the team ZIP is no longer
unseen. The
acceptance records are `docs/YUNT_LIVE_ACCEPTANCE_2026-09-12.md` and
`docs/YUNT_LIVE_ACCEPTANCE_2026-09-13.md`; the presenter-ready guide is
`docs/YUNT_CAPABILITY_GUIDE.html`.

## Next

1. **Retrain the classifier on the latest labelled data (next session's focus).**
   Start by establishing, from the data rather than prose, what "latest
   labelled" is: `Data/gold/_master_gold.csv` (2,577 rows / 73 classes at last
   count), the 2026-09-02 client labels in `reports/client_reply_2026_09_02/`,
   and the 11,746 human-corrected live lines — read the backing gold `source`,
   never `prediction_source`. Rules that bind the retrain: never promote an
   unaudited row (`docs/LABELING_RULES.md`); dedup on the built input string
   (D-013); client conventions outrank row counts (`docs/CLIENT_CONVENTIONS.md`,
   D-040); rule-assigned classes are not trained (D-028); a class under 2
   examples fails loudly; `artifacts/v1.0.0/` and `v1.1.0/` are protected; accept
   only through `docs/TEST_CHECKLIST.md` "Before accepting a retrain" including
   the income slice and `scripts/77_model_trust_report.py`. Train in
   `.venv-train`; PyTorch never enters `.venv-backend`.
2. Afaq tops up Anthropic credits; then resend one pie-chart email to prove
   D-094 end to end (`Envíame un gráfico de torta con las compras de 2025 por
   categoría.`), and delete its inbound row afterwards.
3. Before any new team test on unseen data, detach a fresh sample: the
   2026-09-13 one is back in live, so `yunt-unseen-invoices.zip` is seen data.
4. Afaq reviews the `yunt` Preview
   (`https://milk-company-git-yunt-mountain-creative.vercel.app`) and decides
   whether it goes to production. Still unverified by eye: historical-category
   chips on a real open request, and the `/carga` stat tiles with a loaded ZIP.
5. Optional performance work: move the Analytics aggregation into the database;
   store `item_summary` and refresh it on import; consider prompt caching for the
   eve agent. MCT-166 stays parked on `parked/mct-166`.
6. Decide whether to build a dashboard review inbox/notification flow. Until
   then, describe `/carga` as deterministic upload/classification.
7. Run broader ambiguous-wording and longer-session tests before claiming
   tool-choice or memory reliability across all 25 tools.
8. After any future team testing, inspect exact new identities before cleanup.
   `90_yunt_live_test_undo.py --apply` assumes all Yunt purchases are
   disposable; do not use that once team work begins.
9. Keep `MCT-165` in Backlog.

**Ticket count: 25 total - 23 Done, 0 In Progress, 2 parked (`MCT-154`,
`MCT-143`).**

**Gotchas worth keeping.** Click Outlook's Send by element ref, never by
coordinate - a coordinate click silently saves a draft. Poll for a NEW request
id, not for the newest row to settle. Name paths in `git add`; a wide add swept
the parked MCT-166 files into a feature commit. In the live-test rollback,
application rows are reached through their application (not a batch id), catalog
records must be proven absent from the pre-test identity snapshot before deletion,
and purchase-order drafts must be deleted before their order. `scripts/` and
`backups/` are gitignored here, so undo scripts and snapshots live on disk only.
A Resend HTTP 200 without `message_id` is incomplete: retry, never resend.
A preview URL answering 401 is Deployment Protection, not a broken route.

## Prior checkpoint (superseded by `Now` above)

**Step 0 had been run before the key was added.** `docs/GO_RUNBOOK.md` became the
operative file: the three tests were prepared, the fixtures existed and had
been read through the real ingest, and the undo was written and dry-run.

**Four blockers were found for free before anything was spent; all are now
resolved.** At that checkpoint there was no model credential on Vercel (the agent runs
in the deployment, so `.env.local` is not enough); every deploy since
2026-09-10 fails because the eve service emits an Edge `_middleware`, which is
fixed here with `runtime: "nodejs"` but unverified until a push; Vercel
Deployment Protection answers 401 to every request, Production included, so the
Resend webhook has never been able to reach `/api/yunt/inbound` at all; and 18
commits are unpushed, so the newest working Preview is two days behind. Details
and the fix for each are in `GO_RUNBOOK.md`.

**`YUNT_ALLOWED_ADDRESSES` is one address: `afaq@mctechstudio.com`.** Read from
`.env.local`, which earlier docs assumed was unreadable. Mail from anywhere else
is ignored in silence, so every test email must be sent from there.

### Completed actionable list, answered by Afaq on 2026-09-11

Completed in this order. Kept as history because D-077 through D-079 explain
the resulting architecture.

1. **Afaq adds the Anthropic key to Vercel himself**, so it never passes through
   a transcript. Unflagged, not sensitive, so a later session can confirm it is
   there (D-077):
   `vercel env add ANTHROPIC_API_KEY preview` — paste at the prompt.
2. **Switch the agent to the direct Anthropic path** (D-077): `npm i
   @ai-sdk/anthropic`, `model: anthropic("claude-sonnet-5")` in
   `agent/agent.ts`, and `YUNT_REVIEW_MODEL` in `src/lib/yunt/after-write.ts`
   to `claude-sonnet-5` in the same commit — D-076 says those two move together.
   In the same edit, `defaultTools: false` (D-078).
3. **Push `yunt` and watch the deploy.** 18 commits, and the top one carries the
   `runtime: "nodejs"` middleware fix for
   `Edge Runtime is not supported in services`. Afaq has asked for this to be
   done for him. If the deploy still fails, the next thing to try is Next 16's
   `proxy.ts` (`npx @next/codemod@canary middleware-to-proxy .`); the Edge
   function is what Vercel refuses, not the middleware's logic.
4. **Deployment Protection is still on and nothing bypasses it.** Afaq thought
   he had added a bypass; `vercel env ls` shows no automation-bypass secret on
   the project, and a request carrying a made-up bypass value is redirected to
   the Vercel login exactly like one carrying none. So Resend has never reached
   `/api/yunt/inbound`, and no email test can pass until either protection is
   off for the project or a Protection Bypass for Automation secret exists and
   is appended to the webhook URL in Resend as
   `?x-vercel-protection-bypass=<secret>`. The svix signature covers the body,
   so a query string does not invalidate it. **This is a Vercel dashboard
   setting and it needs Afaq.**
5. **Delete the leftover test row** — one `purchase_requests` row,
   `SOL-2026-0003` "Petroleo Diesel", whose description already says
   `PRUEBA 4 ... Eliminar despues`. Afaq has confirmed it is his test row.
   Back up first, write the delete as a scoped PostgREST call anchored on that
   `request_id`, and re-snapshot the baseline afterwards
   (`scripts/90_yunt_live_test_undo.py --snapshot`), because the purchasing
   baseline moves from 1 to 0.
6. **Delete the Python `yunt/`** (D-079), and in the same commit take
   `CLAUDE.md`'s warning about it, and the `.venv-yunt` test conventions, out
   with it.
7. **Then run the three tests**, in `docs/GO_RUNBOOK.md`'s order. Everything
   they need already exists: the archive, the fixture check, the undo and its
   snapshot.

**The earlier MCT-155 cleanup returned live to baseline exactly** — 5,195 invoices /
11,746 lines / 461 companies / 4,002 catalog items / 78 categories. Backup
`supabase_20260911T074329Z`. The
MCT-155 test batch was written to live, read, judged and removed; the undo script
`scripts/89_cleanup_mct155_test.py` restored the counts exactly and is the pattern
to copy for the next live test (anchored on one fake supplier RUT, dry-run by
default, verifies the baseline itself).

**Migrations: `024`, `026` and `027` are CONFIRMED live; `023` and `025` are
believed live but NOT re-verified.** `024` is proved by the signed-in dashboard
reading `yunt_flags` without error; `026` by a quotation saved with no file at
all; `027` by flags actually landing on a save. Everything in `023`–`027` is
idempotent, so re-pasting is safe and is the cheapest way to settle the last two.

**The classifier was redeployed on 2026-09-10 and ingest works again.** Revision
`mlmodel-00015-mjr`, image tag `v1.3.3-plate`, 100% of traffic. The model is
untouched — `artifacts/v1.3.3-int8/` has no commits since the previous deploy and
`/artifact-check` reports the same 278,181,947 bytes — so this shipped code, not
weights: `5ef2fd7` had added `transport_plate` to `app/api/schemas.py` that
morning while Cloud Run still ran the container built before it, and Pydantic
answers `422 extra_forbidden` to an unknown key. Every ingest failed at the
classify step for a few hours, found by driving `/carga` rather than by a test.

`docs/TEST_CHECKLIST.md`'s "Before deploying" list is now
`scripts/88_prove_deploy.sh`; all seven checks pass against the live revision,
including the incident path and its direction guard. The income slice does **not**
gate this kind of release — it gates accepting a *retrain*, read off
`model_card.json`, and there is no new model card. Rollback stays a traffic shift
to `mlmodel-00014-lrp`, no rebuild.

**The review now runs on Sonnet 5 at `high` reasoning (D-076).** Two files must
agree: `agent/agent.ts` picks the model, `YUNT_REVIEW_MODEL` in
`src/lib/yunt/after-write.ts` stamps it on each attempt as provenance. What would
reverse it is review *quality*, not cost — see D-076 for what to watch for.

**`reviewAfterWrite` now takes an optional dispatcher** (`2e496a6`), so the whole
review chain — packets, chunking, the submit guard, proposals, approval, apply,
undo — can be driven by a stub with no API call. That is step 0 of the test plan
and it should happen before the key is wired.

**`MCT-164` is done and closed.** The apparent label inconsistency was
deterministic all along. `dte.ts` now keeps `<Transporte><Patente>` as
`invoices.transport_plate`, and `025` ranks an exact `meter_code` match above
mere same-wording evidence. Measured on the fixed 400-line held-out run,
confidently-wrong proposals fell **5.75% → 2.76%**, 97.2% of proposals correct.
Reproduce with `.venv-backend/bin/python scripts/87_measure_precedent_quality.py 400`.

**At that earlier checkpoint, `MCT-152` was implemented but not closed.** `reply_with_report` queries the
aggregate RPC itself and attaches a real PDF or one of five code-drawn SVG
charts (bar, monthly line, stacked bar, pie, table). Filter, accounting basis,
credit-note rule and truncation disclosure are printed on the artefact. Focused
generator check, targeted lint, `tsc --noEmit` and a visual PDF render all
passed. What remains is the acceptance run from one real stored question.

**`MCT-155` is done and closed.** Flags are written, shown per line in both
languages, and have been read on live data and judged useful. There is no
approve/undo half: a flag reports a problem in the supplier's document and never
changes a value (D-070), so there is nothing to approve. Category proposals keep
their own approve-and-undo path, which is `MCT-150`.

**`YUNT_ALLOWED_ADDRESSES` was never unset.** It has been on Vercel Preview
since 2026-09-09, value unknown because every var is sensitive-flagged and reads
back as `[SENSITIVE]`. That is what produced the wrong note in earlier docs.
`vercel env rm` is blocked by the permission classifier, so converting them to
readable needs Afaq. He has said this is a readability preference, not a blocker.

**Git.** `ML-model` is on `yunt-backend`; this checkpoint and its test fixtures
follow `f3dff7b`. `milk-company` is on `yunt` at `7d8b632`, pushed and deployed.
Three uncommitted performance files remain parked: dashboard and
products cache experiments plus the analytics hint nesting fix. Do not mix them
into feature work without reopening `MCT-166`.
Parked branch `yunt-recurring-reports-v2` holds the V2 recurring-reports work
and its own `026` — renumber that one when it is resumed (D-069).

**Purchasing is proved end to end on live**, by using the screens rather than
reading them: request → quotations → order above CLP 500,000 refused with fewer
than two → allowed with two → request closed → numbered PDF. `MCT-140`,
`MCT-161`, `MCT-168` and `MCT-169` are closed on that evidence. Test rows are
marked `PRUEBA`; delete by `title like 'PRUEBA%'`, orders before requests.

**The original V1 scope has no missing implementation code.** It contains 19
promises; recurring reports (#13 / `MCT-154`) are parked for V2 (D-069), leaving
18 active. All 18 have code, 8 are fully accepted end to end, and 10 still need
live integration or acceptance (see the table below). Outside that original
scope, `MCT-165` — judging whether a quotation is genuine before it counts
toward the CLP 500,000 rule — is still unbuilt and needs the Claude API key.
`MCT-155` is closed; D-070 deliberately forbids the Yunt from proposing edits to
values copied from a DTE.

**Do not drive the Supabase SQL editor.** A previous session typed over editor
buffers holding Afaq's own saved queries. Read live state through
`scripts/supabase_rest.py` or ask him to run a query and paste the result.

### Working agreement, set by Afaq on 2026-09-10

One ticket at a time: implement, check it in the UI at `localhost:3000`, run an
end-to-end test, fix what breaks, update the ticket, close it, move on. Do not
open five things at once. Anything touching production data needs a rollback
path written *before* the write and a backup taken first. Tickets were
AI-generated and are **not authoritative** — correct them when they are wrong.
Post concise, ASCII-only project updates in Linear after each milestone, pitched
at a product manager, not at an engineer.

`agent/tools/` holds 22 tools; `src/lib/yunt/` holds 22 modules. Read that
listing before adding either — three re-implementations were caught only because
someone looked first.

**Grill him where his input is genuinely needed** — his domain knowledge has now
twice beaten a statistical conclusion (the folder-vs-RUT direction, and the
meter/plate finding above). Ask before concluding something about the client's
data is wrong.

### The order of work, as of 2026-09-11

**Nothing is left that does not need the key.** Every open ticket is blocked on a
live run. The plan for those runs is `docs/YUNT_TEST_PLAN.md`, and its step 0 —
driving the whole review chain from a stub, free — should happen **before** the
key is wired, because that is where the non-model bugs are.

**Waiting on Afaq:** the Claude API key (see the test plan for exactly which
variable, which depends on whether it is a gateway key or an Anthropic one), and
a real invoice email for `MCT-160`.

**Still unverified, cheap:** `023` and `025` are believed live but were never
re-checked. Both are idempotent; re-pasting settles it.

**`MCT-162` is done (D-072).** Direction is read from the RUTs in each document
— Antillanca as `RUTEmisor` is a sale, as `RUTRecep` a purchase — and the
`COMPRAS`/`VENTAS` folder is only a fallback for a document naming neither. That
case does not exist: across all 5,584 raw DTEs, Antillanca is on exactly one side
of every one, never neither and never both, and the RUT rule reproduces the
folder on all 5,195 ingested documents with **zero disagreements**. So nothing
already stored is relabelled; what changed is that a flat or differently-named
archive is now accepted instead of rejected file by file. Proved on `/carga`:
six documents in one flat `todo/` folder, four purchases and two sales, read and
split correctly with nothing written. The `no_direction_folder` rejection reason
is gone.

**Deferred deliberately:** `MCT-143` client data questions stay logged, not
raised: Afaq's call on 2026-09-10 was that they do not appear to affect
processing logic. Performance work in `MCT-166` is parked while functionality is
finished. Recurring reports remain parked for V2.

**Ticket coverage is not proven.** The tickets were AI-generated and may not
span the whole scope. Closing them all is not the same as building everything.
Reconcile `docs/Yunt_scope_v1.docx` and `DECISIONS.md` against the closed
tickets at the end — the decision log wins where they disagree (D-059).

### Local UI testing, which is now the fast path

`.env.local` in `milk-company` had both Supabase values as `[SENSITIVE]`; Afaq
filled in the project URL and the **publishable** key (`sb_publishable_…`, the
replacement for the legacy anon key). `npm run dev` then works against live
Supabase with a real signed-in session. It holds **no service key**, which is
what proved `MCT-159`: the save could only have gone through RLS as
`authenticated`.

To put a file into the upload form without a file picker, build the bytes in the
page and assign them through a `DataTransfer`, then `form.requestSubmit()`.

**Do not stage the file in `milk-company/public/`.** It reads as cheaper than
inlining base64 and it is not: the dev server watches that directory, so writing
there triggers Fast Refresh, the page reloads, and the file input is cleared
before the submit lands. The symptom is a submit that silently does nothing,
twice, with no console error. Inline the base64 — a one-document ZIP is about
1.3 KB of it. Also wait for hydration before assigning: on a freshly navigated
page the first `requestSubmit()` can be swallowed, and clicking the real button
by `ref` after setting the file is the reliable form.

## Linear, as of 2026-09-11

Linear mirrors this project feature by feature, so it can be read instead of this
file for *progress*. It is not the design; where a ticket and `DECISIONS.md`
disagree, the decision log wins.

- **Done:** `MCT-139` ingest, `MCT-145` upload page, `MCT-146` save to database,
  `MCT-147` auto-accept rate, `MCT-148` purchasing tables, `MCT-151` answer
  questions, `MCT-158` run pending migrations, `MCT-159` signed-in save,
  `MCT-164` the field that decides the answer.
- **In progress — every one blocked on a live run, none on missing code:**
  `MCT-142` the parent, `MCT-149` review and propose, `MCT-150` approve and undo,
  `MCT-152` PDF/charts (needs one real stored question), `MCT-153` refusals
  (needs one real refusal), `MCT-156`/`157` purchasing from email, `MCT-141`
  receive by email.
- **Todo:** `MCT-160` the first real email.
- **Backlog, parked for V2:** `MCT-154` recurring reports (D-069).
- **Backlog, parked performance:** `MCT-166`; removing the broken cache stopped
  its error loop but did not satisfy its no-second-query done-when.
- **Done:** `MCT-163` hardcoded Spanish and `MCT-167` the order-centric list
  (`205451d`); `MCT-162` direction from the RUTs (D-072) and `MCT-155` quality
  flags, both closed 2026-09-11 with proof comments.
- **Backlog, deferred on purpose:** `MCT-143` client data questions.

Tickets are written at product level on purpose — no file names, no migration
numbers, no function names — so an implementation discovery cannot turn one into
a lie. The *how* lives here and in `DECISIONS.md`.

## What the Yunt promises, and what it does today

The 19 numbered items are the scope sent to the team, in the client's own
words (`docs/Yunt_scope_v1.docx`). Where that document and `DECISIONS.md`
disagree on *how*, the decision log wins (D-059) — but this list is what
Antillanca was told they are getting, so it is the honest measure of progress.

**Implementation: 18 of 18 active V1 promises have code; #13 is parked for
V2. Acceptance: 8 of those 18 are proved end to end, and 10 still need a live
email, model run, migration or real request. Nothing agentic is live-proved
yet.**

| # | What Cristian was promised | Today |
|---|---|---|
| 1 | A mailbox that acts only on agreed senders | Built. Never carried a real message |
| 2 | A ZIP containing SII XML under `COMPRAS` and `VENTAS` | Proved through `/carga`; the real mailbox path is still unproved |
| 3 | Duplicate detection on RUT + type + folio; sending twice changes nothing | Done |
| 4 | Lines classified and **written to the database** | Built and proved through `/carga` on live; the email route remains unproved |
| 5 | An acknowledgement in minutes, then a written report | Built as a receipt first and a findings email later; never live-proved |
| 6 | Data quality flags, and fixes proposed on approval | **Done.** Built, calibrated, persisted, shown per line in both languages, and accepted on live data. D-070 corrects the scope: DTE values are reported, never changed; only category changes can be proposed |
| 7 | Category proposals with evidence, grouped | Built and grounded; deterministic precedent quality measured at 97.2% of proposals correct. The real Claude review still needs its key and acceptance run |
| 8 | Approve a group, get confirmation, undo it | Built with database-enforced confirmation and undo; no live agent run yet |
| 9 | Five query tools answering open questions | Done. All five built and their figures independently proved; `022` is live |
| 10 | Figure in the body, list as spreadsheet, report as PDF, filter printed on top | Built and visually checked. No real stored question has received one yet |
| 11 | Charts from a fixed set, drawn by code | Done. Five fixed types, code-drawn inside the report PDF (D-093); pie/stacked shares use the whole total (D-094) |
| 12 | Says so when a question does not fit, and we learn from the list | Built and migration `017` is live; no real refusal exists yet |
| 13 | Month-end summary, post-batch digest, weekly review list | **Parked for V2** (D-069). A first pass exists on a side branch; the post-batch half is arguably already the findings email |
| 14 | Form one: what is needed, how much, by when, for which farm | Done and exercised on live |
| 15 | A request stays open until an order closes it | Done, database-enforced and exercised on live |
| 16 | Form two, with the two-quotation rule above CLP 500,000 | Done; refusal with fewer than two and success with two were both proved on live |
| 17 | A purchase-order PDF Antillanca sends themselves | Done. The print page and true PDF use one loader and were exercised on live |
| 18 | The Yunt fills form one from a plain-language email | Built; exact confirmation turns a stored draft into a request. Migration `018` is live, but no real email/model run exists |
| 19 | The Yunt drafts the order once a quotation exists | Built; exact confirmation issues the order and migration `020` is live. No real email/model run exists |

**Read the middle column, not only the count.** The deterministic base is
proved. The EVE review and action tools are called by the email path in code,
but model credentials and real-message proof are still open. The repository has
22 agent tools; all tools promised by the original scope exist. `MCT-165` is an
important discovered safety gap outside that scope, not evidence that the scope
toolset is missing.

**The next foundation priority is permission, not another feature:** make
`/carga` a real authenticated write without exposing service-role power, clear
the Supabase usage block, run `011`–`019`, then prove one real email and one
upload including replay. In parallel, finish the remaining four read tools.

## V1 checklist

Every box that must be ticked for a working v1. Updated as work lands — if a box
is unticked, there is no code for it. "Built" means proved by a regression;
"live" means the migration has run in Supabase.

### The spine — invoices in, stored, reviewed

- [x] Deploy path, Resend mailbox, ZIP upload page (Phases 0–1)
- [x] Read, deduplicate, resolve to catalog, classify, report (Phases 2–2.5)
- [x] Atomic writer: whole invoice and all its lines in one transaction (D-063)
- [x] `/carga` live save: `021` is live and one real signed-in save has been
      proved on live, then cleaned back to baseline exactly
- [x] Mailbox router: ZIP → deterministic ingest, everything else → the agent
- [x] **Mailbox connected to the writer** — claimed by the Resend message id
- [x] **Email review fires after a write** and never blocks the receipt (D-064)
- [ ] `/carga` review runs under the final operator permission design
- [ ] First real write, against a backup, with Afaq's yes on the day

### The review loop

- [x] Durable review state, packets, atomic completion (`009`–`011`)
- [x] Three grounded EVE tools: load, precedent, submit
- [x] Findings-email outbox: sends only when findings exist (`012`, D-065)
- [x] OIDC-secured, idempotent dispatch to EVE
- [x] **`anthropic/claude-opus-5`, reasoning `high`** in `agent/agent.ts`.
      Settled 2026-09-09 from current published pricing: Opus 5 $5/$25 per MTok
      against Sonnet 5 $2/$10 and Haiku 4.5 $1/$5. `high` is the model default
      and the quality/token balance point; `medium` had been chosen on a cost
      argument, which is the wrong axis when the whole month is a few dollars
- [ ] Proof run: 200 known review rows, counting the confidently-wrong (Phase 5)

### Talking to Cristian

- [x] Inbound requests recorded and threaded by `In-Reply-To` (`013`)
- [x] `reply_to_email` — recipient read from the row, one reply per request
- [x] **All five query tools** (Phase 7, D-053): price history, category
      precedent, invoice-line listing, grouped totals and period comparison.
      Money semantics live in one function and print on every answer — net line
      amounts, IVA excluded, credit notes negated and excluded by default
- [x] **List as a spreadsheet attachment**, queried by the tool rather than
      retyped by the model. CSV with a BOM and semicolons so Excel reads it in
      Chile; a real workbook only if formatting or formulas are ever needed
- [x] **Report as PDF, and charts from the fixed set** — one tool, five chart
      types drawn by code inside the PDF, written without a browser. Acceptance from
      a real stored question is still outstanding
- [x] Refusal path and `yunt_refusals`, one immutable backlog row per request
- [x] Exact restate-then-confirm for apply and undo: code-generated prompt,
      Message-ID/sender/action/target binding, and one-use first-line token

### Acting, with a way back

- [x] **`apply_proposal`** — sealed targets, no row list from the caller, stale
      proposals refused because a person's later edit wins (Phase 6)
- [x] **`yunt_applications`: prior values stored, undo is a per-row replay** —
      `decision` and `reviewed` come back too
- [x] **Data-quality flags: four line checks and one document check**, each
      chosen by measuring candidates against the stored 11,746 lines. A flagged
      `auto_accept` is downgraded to review and nothing else (Phase 4, D-058, D1)
- [x] **Flags persisted to `yunt_flags`** with `source='deterministic'`, written
      when the review attempt opens so an incomplete review still leaves them
- [x] Flags shown per line in the dashboard, in both languages, proved on live
      data and judged useful (`MCT-155` closed 2026-09-11)

### Purchasing

- [x] The two forms, real tables (`005` live) — not yet exercised live
- [x] The Yunt drafts and creates form one from email only after exact
      confirmation (`018`)
- [x] Read one request, its bounded quotations and any existing order without
      exposing private quotation storage paths
- [x] The order form records an optional chosen quotation; the database rejects
      a quotation belonging to a different request (`019`)
- [ ] Attach supplier/price precedent to that buying exchange when requested
      (the grounded price-history tool itself already exists)
- [x] **The Yunt drafts and issues the order from email after exact
      confirmation** (`020`), through the same `create_purchase_order` the form
      calls — the CLP 500,000 two-quotation check has one copy, never a second

### Waiting on Afaq

- [ ] Confirm Supabase is out of its **EXCEEDING USAGE LIMITS** state. The
      `011`–`020` run succeeding suggests it is; not checked directly
- [x] **`024` is run and confirmed live** (2026-09-10). Proved offline by
      `scripts/prove-024-yunt-flags-read.sh` and on live by the signed-in
      dashboard reading `yunt_flags` without error
- [x] `021` written and proved (`scripts/prove-021-carga-writes.sh`)
- [x] `/carga` permission design decided: any signed-in user, no roles in v1
- [ ] **Your yes on the 222 harvested aliases** (`006` is live, so unblocked)
- [ ] Send the first real email to `antillanca.yunt@mountaincreative.cl`
- [ ] Fix the `Confeccion de Bolos` duplicate — three catalog rows, one thing

### Deliberately not in v1

Roles and approval chains on purchase orders (D-052, and the scope document says
so in the client's own words), goods receipt / invoice matching / payment, and
ingestion from the Audisoft API, which is blocked on credentials that return 401
(D-054), and — since 2026-09-10 — **recurring reports**, scope item 13, which
were in v1 until the product questions behind them turned out to be unanswered
(D-069).
## Recent sessions

### 2026-09-12 - queries, reports and charts proved; seven bugs fixed

- **`MCT-150` and `MCT-152` closed** on live evidence with proof comments.
- **Fresh invoice-email acceptance passed**: new folios `999201`–`999206` made
  the real reception report, then a single Sonnet review made 3 flags and 4
  grounded, unapplied category proposals. The findings email names the actual
  precedent count, category and wording rather than model filler.
- **`MCT-141`, `MCT-149` and `MCT-160` closed** in Linear from that evidence.
- **Two cheap harness fixes:** the fixture check accepts an explicit new folio
  base; preflight no longer blocks the valid direct-Anthropic path on an unused,
  expired Vercel OIDC token. `preflight-go.ts` printed `all clear` against live.
- **Money semantics verified to the peso**: the Yunt excluded CLP 2.218.982 of
  credit notes and said so; the naive recount was the wrong one.
- **Three chart/report defects found by opening the delivered files**: value
  ordering on a time series, two months dropped silently, and a body promising a
  PDF while carrying an .svg. All fixed with `check-yunt-report-periods.ts`.
- **Escaped newlines** reached the client in a report reply; normalised at the
  one point all mail leaves through, and in the stored copy too.
- **Lesson**: opening the artefact found three bugs that every green check and
  every correct figure in the email body had missed.
