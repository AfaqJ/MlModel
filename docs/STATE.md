# STATE — where this project is right now

Updated every session. Last 5 sessions only; anything older that still matters
lives in `DECISIONS.md`.

## Session — 2026-09-21

**MCT-190, the glassbox, is built on `afaq/mct-190-glassbox` in `../milk-company`
and driven in the browser, signed in — all three surfaces, every case below. It
is on `yunt` and deployed to Preview (D-109).** Migrations
`039` and `040` are live. `check.sh` is green.

**What Cristian and the team see, read-only, in the client's words:**
1. **Jobs** — the history sits under the upload form on `/carga` (no tabs); a row
   opens `/carga/[id]`: lines by current state (confirmed / suggested / needs
   review; on a saved job an accepted suggestion is confirmed), the state, and the
   email thread. States driven: reviewing → waiting for approval → saved (email),
   discarded (email), failed (both services down), already-registered upload
   (creates no job), ML-only fallback (saved without the Yunt).
2. **Purchase** — `/solicitudes/[id]` gets a Request → Quotations → Order strip
   and the thread. Driven: closed with an order (the real 16 Sep case, SOL-2026-0016
   / OC-2026-0011), open needing two quotations, open with the rule not applying,
   manual (no emails). The order is a stage, not a page.
3. **Reports** — `/informes`: thread, the question as filters, the fetched rows as
   a table, the PDF re-drawn from stored data. Driven with two seeded reports
   (PDF and spreadsheet) through the real query and store code, then removed.

**Proved live: an emailed approval writes rows** — a 3-document synthetic ZIP
(fake RUT 771234567) mailed from Outlook, proposal, `SÍ, ADELANTE`, batch
`completed`, invoices 5,195 → 5,198 and lines 11,746 → 11,750, then removed by a
scoped delete. Live is back to baseline on every table touched; the 16 Sep
purchase thread and every earlier row were left alone.

**Later the same day.** The job/request/report thread now also walks *up* the
reply chain: the row a draft binds to is often the third message, and the first
two ("I need 10L of Petroleo…") were missing — `SOL-2026-0016` now shows all 12
messages. Found by Afaq reading the page.

**A real gap, fixed in the branch, not deployed:** every purchasing tool needs the
internal request id, so a request opened in the dashboard cannot be ordered by
email — the Yunt answers "necesito el identificador interno". New read-only tool
`find_purchase_request` (by `SOL-…` number, or the open list), one instruction
line, `check-yunt-find-request.ts`; proved against live data. `SOL-2026-0019` was
ordered by email only by pasting the id as a workaround (`OC-2026-0012`, fake
supplier, CLP 13,000, **left on live on purpose**).

**Deployed.** `afaq/mct-190-glassbox` pushed and fast-forwarded into `yunt`
(`46b25af` → `f15d52a`); `npm run build` passed locally, the Vercel Preview is
Ready (`milk-company-git-yunt-mountain-creative.vercel.app`), and the new lookup was
proved on it: a request made in the dashboard (`SOL-2026-0020`, since removed) was
found from its number in an email and an order proposed. Production is still the
2026-09-16 build.

**Hand-run guide:** `docs/GLASSBOX_TEST_GUIDE.md`, attachments in
`handover/glassbox-test/`, and `scripts/91_glassbox_test_cleanup.py` (scoped,
dry-run first, refuses `SOL-2026-0016`).

**Open, found this session:**
- **A second, unwanted reply.** One `SÍ, ADELANTE` produced both the correct "Listo,
  quedó guardado" and "No encontré documentos que pudiera leer en ese correo" —
  the latter is only sent when a message has ZIP/XML attachments that did not
  yield files, and no inbound row was recorded for it. Needs the Preview logs.
- **Reports are stored from `f15d52a`.** Nothing older is backfilled.
- **Do not run `scripts/90_yunt_live_test_undo.py --apply`** while the Yunt team
  has purchase requests live: its Test 3 deletes every `created_via='yunt'`
  request and order, and it has no per-test switch.
- The failed-job page gives one generic sentence; the stored error is internal
  and is never shown, so "why it failed" is not itemised.

## Session — 2026-09-19

**MCT-189 is built, proved end to end, and merged into `yunt` (head `46b25af`),
which is pushed — Vercel Preview runs it and the Resend webhook points there.
Production is untouched and still serves the 2026-09-16 build.** The glassbox
branch `afaq/mct-190-glassbox` was cut from that head; see the 2026-09-21 session.

**The email path is proved live.** One ZIP with two July invoices from Afaq's
Outlook: job `ml_yunt`, `reviewing` → `awaiting_approval` in ~60s, a proposal
email listing both lines and asking for `SÍ, ADELANTE`, **nothing written**. A
plain-language reply ("No, descarta esta propuesta por ahora") rejected the job
and was answered: "Listo, descarté la propuesta. No se guardó nada." Live counts
never moved: 5,195 invoices / 11,746 lines.

**The leak that run exposed, now fixed (`46b25af`).** The proposal told the
client "el sistema mismo marcó baja confianza" — model confidence, which D-108
as amended forbids showing. The guard only covered the fixed wording, not the
model-authored reason. Reasons now pass through `colleagueText`, so any sentence
naming the model, its confidence or an internal id is dropped before rendering;
`check-job-report.ts` feeds it that exact sentence.

**(Proved on 2026-09-21: an emailed approval wrote rows.)** Until then it had
checks, not a click. Two July invoices are ready for it whenever Afaq wants. Migration `038` is **live**
(backup `backups/supabase_20260919T122424Z`, verified against the baseline before
pasting). Live data is untouched: 5,195 invoices / 11,746 lines, before and after
every test.

- **The client's accounting rules now run in the dashboard**, generated from the
  ML-model CSVs by `scripts/generate-rules-data.ts`. Parity proved on a real
  month: 932 lines, 443 settled by rule, 22 petrol held for review, 467 sent to
  the model, **zero disagreements** with Cloud Run. The Cloud Run cascade stays
  until its direct callers migrate.
- **Nothing is written before approval** except the ML-only row of D-108. One
  orchestrator (`src/lib/ingest/orchestrate.ts`) serves both doors;
  `writePreparedIngest` is gone, replaced by claim → plan → stage → commit, with
  the plan hashed so an approval can only commit what was shown.
- **Proved in the browser, signed in, against live:** three stored files report
  "3 already registered, 0 new"; five new 2026-07 invoices with the classifier
  switched off produced a `yunt_fallback` proposal — 3 suggestions, 2 left for a
  person, each reason citing real precedent — and **wrote nothing**; reject
  through `/api/carga/decision` returned `{rejected:true}`. Both test jobs are
  `rejected`; nothing pending.
- **Two defects the checks could not see, both fixed:** the Yunt answered
  "unsure" with no category and the refusal did not say what to do instead; and a
  fallback line printed "antes EXP-15.3" against EXP-15.3, a change that never
  happened. Both now guarded.
- **Still unproven:** the ML + Yunt path with both up on screen, an approval
  actually writing rows, and the whole email path. The agent does not mount under
  plain `next dev` — run `npx eve dev` (Node 24; it listens on 127.0.0.1:2000)
  and point `YUNT_EVE_URL` at it.
- **D-108 amended in five places** (no expiry, one email per job, no engine or
  confidence in the client's copy, emailed jobs answered only by email, every
  approved line `yunt_applied`). Plan and results:
  `docs/MCT_189_PLAN.md`. Glassbox moved out to
  [MCT-190](https://linear.app/mctechstudio/issue/MCT-190/glassbox-show-what-the-yunt-did-per-job-request-and-report),
  its own branch and session.

## Session — 2026-09-17 (g)

**The classifier/Yunt reliability policy is final (D-108) and captured in
Linear as urgent Todo [MCT-189](https://linear.app/mctechstudio/issue/MCT-189/make-invoice-classification-reliable-across-ml-and-yunt-failures).** No
pipeline code was changed in this session. The present implementation still
writes before Yunt reviews, treats the classifier as a hard dependency, and
does not implement the new fallback matrix.

- Deterministic accounting lookups move to a shared Next.js orchestrator and
  run before ML. Only unresolved lines go to ML. Keep the Cloud Run copy until
  its direct callers have migrated and parity is proved.
- ML + Yunt: show the proposed complete report, require confirmation, then
  commit. ML only: commit immediately and return a complete audit report. Yunt
  only: allowed only when at most 10 lines remain unresolved after deterministic
  checks; show the report, require confirmation, then commit. Yunt-only above
  10, or neither service: save nothing and ask the user to retry later.
- Whenever Yunt participates, confirmation is required even if it agrees with
  ML. Email therefore needs one durable staged approval record; this is not an
  outage queue, has no cron/retry, and never appears as imported business data.
- Prefer an inline email table through 25 lines; use XLSX above that. Dashboard
  shows the same complete line report. Fallback-only lookup tools are exposed
  and executor-enabled only in a server-issued `ml_fallback` session.
- Still to fix around this work: changing language remounts `/carga` and loses
  the selected upload/result; remove the redundant dashboard card that previews
  the email; mount Yunt on the dashboard only after MCT-189 is implemented and
  proved; then produce the requested granular plain-language flow diagram.
- D-107 was re-proved, not rewritten: `milk-company` `2402bd0` is pushed and
  `yunt == origin/yunt` (0 ahead, 0 behind). Both email and `/carga` accept one
  or many ZIPs/XMLs, including a mix, as one batch. Proof rerun: real month 388
  XML / 902 lines, loose XML equals ZIP, resend is idempotent; inbound router,
  TypeScript and targeted ESLint passed (one unrelated unused-import warning).
- No Linear ticket was created for the ZIP/XML reminder. The only new issue is
  MCT-189 for the reliability implementation.

## Session — 2026-09-17 (f)

**Both ingest doors now take loose DTE XML files (one or many) as well as ZIPs
(D-107).** `milk-company` `2402bd0`, pushed; the nine audit commits before it were
pushed first (`66efc19..3deb814`) and built a Ready **Preview**. Production is
still the 2026-09-16 build. Proofs: `check-ingest-batch` (real month identical as
loose XML vs ZIP), `check-yunt-inbound-router`, six other ingest/review checks,
`tsc`, targeted ESLint, and a signed-in `/carga` dry run with three real XMLs.
Full `check.sh` not run (Afaq's 3–4-feature rule).

- **Found, not fixed — the classifier is a hard dependency of saving.**
  `prepareIngest` catches a classifier failure, but `validatePrediction` in
  `write.ts` refuses any line without a result, so a Cloud Run outage saves
  **nothing** (email reports "No se pudieron procesar…"; `/carga` errors). This
  contradicts D-051 ("ships standalone"). `buildBatchReview` also throws without
  predictions, so the Yunt never runs either.
- **Found, not fixed — a failed review is never retried.** `reviewAfterWrite`
  marks the attempt `unavailable` and nothing ever picks it up again; no cron or
  job exists (`vercel.json` absent).
- **To verify:** `claimBatch` throws on a batch still `processing`; if a function
  is killed mid-write, that message may be stuck forever on redelivery.
- **Reliability plan was being drafted when the session stopped** (Afaq wants:
  who depends on whom, what runs when something is down, what retries and how,
  whether the Yunt may classify when the ML is down — he suggested only under
  10 invoices — then a granular, plain-worded diagram of the final flow). No
  decision taken yet.
- **Facts gathered for that plan:**
  - Resend webhooks on the account: Yunt → `milk-company-git-yunt-…vercel.app/api/yunt/inbound?x-vercel-protection-bypass=…` (enabled, `email.received`); `ppd-agent.vercel.app/api/inbound/resend` (enabled); `ppd-agent-website…` (disabled). Only `mountaincreative.cl` has receiving enabled.
  - eve turns on AI Gateway `caching: 'auto'` for gateway model strings: breakpoints on the last message and before the last user message. Default lifetime **5 min** (write 1.25x, read 0.1x); `1h` exists (`cache_ttl`, write 2x) but is documented on the Responses API only — passing it through eve is unverified. Sonnet 5 minimum cacheable prefix 1,024 tokens. The Yunt's fixed context is `agent/instructions.md` (16 KB) + `agent/category-guide.md` (5.7 KB) + tool definitions.
  - Vercel Cron calls the **production** deployment URL only, so a cron retry cannot run on Preview.
- **Answered in chat, not yet delivered:** Afaq's webhook questions (which two apps, broadcast or not) are still owed.
- **Gotcha:** the browser pane has no file upload; inject files with `DataTransfer`
  fetched from a local file server (port 8765 was taken by something else).

## Session — 2026-09-17 (e)

**Every 2026-09-17 audit ticket is Done in Linear, parents included** (170–188;
171, 172, 173, 174 closed once their sub-issues were). `milk-company` commits,
local on `yunt`, **not pushed**: `575b9f5` (182), `ae742db` (178), `4f33cdb` (183),
`9a8fd2f` (184), `c4c11c4` (185), `daab3ce` (181), `3deb814` (188). `036` and `037`
are live (backups `backups/supabase_20260917T095106Z`, `…T101159Z`). Full
`./check.sh` green after the batch.

- **MCT-182, D-106:** Analítica computes on the server with the *same* TypeScript
  aggregation, not SQL, and sends only what each tab draws (page 5.08 MB → 294 KB;
  all 8 tabs text-identical before/after). Views sit in Next's data cache keyed on
  `analytics_version.changed_at`, which `036` triggers move on any write to
  invoices, lines, categories, companies or the catalog. Raw rows are memoised per
  instance on the same key. Reload 0.4 s on a local `next start`; first load after
  a data change ~5 s. **Dev mode never reads the data cache** — prove caching on a
  production build (`milk-company-prod` in `.claude/launch.json`, port 3001).
- **MCT-183:** Productos searches, filters, sorts and pages on the server; all state
  in the URL (page 3.53 MB → 286 KB; searches return identical items). Search runs
  over memoised summaries, not a DB index.
- **MCT-178 (D-104):** `src/lib/ingest/units.ts` maps spellings to standard units at
  ingest and on every read; 70 of 134 stored spellings map, 64 listed as unmapped.
- **MCT-184 (D-105):** request item search = `search_invoice_wordings` (037).
- **MCT-185:** shared `[locale]/loading.tsx`; Órdenes filter uses `next/form` +
  `SubmitButton`. Every other server button already disabled while busy.
- **MCT-181:** the "Ã³" names were *our* decoder (UTF-8 files with one stray byte
  fell back to Latin-1 whole), repaired by `src/lib/ingest/text.ts` at ingest and
  on read; the 14 stored rows are **not rewritten** (offer a scoped write if Afaq
  wants the database itself clean). Analítica shows the longest name per RUT.
- **MCT-188:** `price_outlier` flag at ingest, 10× from the item+unit median
  (≥5 purchases, credit notes excluded); 3.65% of judgeable stored lines.
- **Payload floor:** both pages still carry ~180 KB of React payload, mostly the
  app-wide translations the layout sends on every page. Out of these tickets.
- **Afaq's working rule (this session):** build first, test minimally per feature,
  run the full `check.sh` only after 3–4 features.

## Session — 2026-09-17 (d)

**MCT-177 and MCT-187 are Done** (`milk-company` `4447d52` and `72f6c07`, local on
`yunt`, not pushed; `034` and `035` live, backups
`backups/supabase_20260917T084405Z` and `backups/supabase_20260917T092218Z`).

- **Production is NOT on today's work.** Pushing `66efc19` built a Vercel
  *Preview* (`milk-company-git-yunt-…`); `milk-company.vercel.app` still serves the
  2026-09-16 build. Afaq: do not promote or push to production yet.
- **MCT-177:** `DscRcgGlobal` is stored as sent in `invoices.document_adjustments`
  (future ingests; `%` resolved to CLP over the lines it applies to). The line-sum
  flag counts adjustments: 430 → 161 of 5,195 documents, 0 newly flagged. Category
  and item spend add each line's share; stored line amounts never change. Invoice
  detail lists the adjustment. Nothing is supplier-specific: no section, no change.
- **MCT-176 excise split: Afaq keeps it,** on condition the price says which it is.
  Ítems now reads "Precio Unit. Prom. (sin impuestos)" with the with-excise price
  on hover. Both the excise and discount splits are now computed over all loaded
  lines, before filters — a category filter used to concentrate them.
- Localhost after `034`: Compras still $4.405.098.457 (02.04.2025–02.04.2026).
- **MCT-187:** new invoices store `invoices.reconciliation` — the three checks
  (line arithmetic, lines ± adjustments = net + exempt, parts = total), each
  ok/false/null with expected and received; flags derive from the same result
  (identical counts over the 5,195 raw documents). Explorer: "Solo no cuadra",
  a row tag, the failing checks in the detail. **Stored invoices are null
  ("unchecked") by Afaq's choice — no backfill.** Recargos counts a surcharge only
  when the line's arithmetic includes it: $4.994.306 → $0 (every stored one was a
  copy). `src/lib/ingest/arithmetic.ts` is the one line formula for both sides.
- **Afaq wants a plain brief before each ticket's build**, stating why it cannot
  break when a supplier changes behaviour.

## Session — 2026-09-17 (c)

**MCT-170, 175, 176, 179, 180 and 186 are Done; `032`, `033` and the `item_summary`
`last_amount` column are live.** Commits in `milk-company` (branch `yunt`, **pushed
2026-09-17 as `9a31459..66efc19`**, so Vercel production deploys it): `8254c72` (170), `3c06cf0` (175), `7570afd` (176), `ddb75ee` (186:
every month labelled), `5f1a6a0` (180: Productos shows "Solo monto" and the
latest amount; view backup `backups/supabase_20260917T071358Z`), `66efc19` (179:
placeholder names such as "Item" read the description, display only). Backups before each migration:
`backups/supabase_20260917T064728Z` and `backups/supabase_20260917T065859Z`.

- **MCT-175:** DTE 61 is negative in every Analítica spend figure (D-103),
  including concentration, payments, geography, insights and item totals. The
  Compras card shows net, with gross and NC beneath. Proved on signed-in
  localhost for 02.04.2025–02.04.2026: Compras went from $4.538.055.105 to
  $4.405.098.457, exactly before − 2 × $66.478.324 of credit notes.
  `dte_references` is stored for new ingests only.
- **MCT-176:** header `ImptoReten` entries are stored for new ingests. A new
  `document_totals` quality flag ("no cuadra según el proveedor") was calibrated
  over the 5,195 stored DTEs: 1,246 mismatches without taxes, 56 with them.
  DTE 43 is skipped because its total subtracts `Comisiones`, which is not
  stored. Desglose Fiscal adds "Otros impuestos" and "Sin desglosar"
  ($19.527.167 on the range above), so its rows equal Total. Items shows unit
  price with stored excise.
- **MCT-176 splits the excise per line by the DTE's own `CodImpAdic`;** Afaq
  confirmed it in (d).
- **Not yet seen live, closed by Afaq's choice:** the "Corrige DTE …" line, stored
  taxes, the new flag and the with-excise price all need a genuinely new document.
  Check them at the first real ingest.
- **Checked in (d):** `66efc19` built only a Preview; production was never updated.
- **Dead code (Afaq: later, only if absolutely safe):** `src/components/dashboard/*` and
  `src/lib/dashboard/{aggregate,invoices}.ts` are imported by no route. Last
  session's edits there were reverted, not committed.
- **Local env:** `.env.local` has no `AI_GATEWAY_API_KEY` (the Yunt needs it,
  D-101) and now does hold `SUPABASE_SECRET_KEY`. Remove that key before
  re-proving that `/carga` saves as the signed-in user.
- **Gotcha:** Afaq rejected a full `check.sh` for each small ticket. It ran once
  for 175+176 and passes.

## Session — 2026-09-17 (b)

**A system-wide audit of dashboard numbers, units and speed is complete, and the fixes are 19 Linear tickets assigned to Afaq (MCT-170–188).** Nothing was changed in code or Supabase. The only live access was reads.

- **Urgent security gap (MCT-170):** the `item_summary` view is `SECURITY DEFINER`, so the anon/publishable key reads it with no session (HTTP 200 with rows). `invoices` correctly returns `[]`. Fix is `security_invoker` plus a grant to authenticated users. It needs Afaq's go-ahead before touching Supabase.
- **Wrong totals (MCT-171):**
  - Analítica adds 103 credit notes (CLP 87.9M) as spend;
  - 1,246 invoices fail total = net + IVA + exempt, because `ImptoReten` isn't stored (982 source files, 981 of them fuel excise 35/28);
  - 473 invoices fail line sum = header, because `DscRcgGlobal` isn't stored;
  - the "Recargos" KPI sums the supplier-copied `RecargoMonto`.
  Rule set as D-103.
- **Units (MCT-172):**
  - 32% of lines have no unit and "each" has ~15 spellings → code map (D-104);
  - 641 amount-only lines show "—" in Productos;
  - 14 supplier names are double-encoded.
- **Speed (MCT-173), measured in dev:**
  - Analítica shows data at 3.3 s with a 4.5 MB HTML payload, and lines finish at ~8 s (10 × ~2 s PostgREST pages). Lines load in `useEffect`, so every remount refetches.
  - Productos takes 2.6 s and ships 3.4 MB.
  - `yunt_invoice_aggregate` (022) already does grouped totals with credit notes negated, but only the Yunt calls it.
- **Stuck-feeling UX (MCT-174):**
  - "G93" isn't found because search reads the catalog name only (→ D-105);
  - there's no empty state;
  - only 2 routes have `loading.tsx`.
- **Gotchas:**
  - `grill-with-docs` and `to-tickets` exist under `~/.claude/plugins/cache/.../mattpocock-skills/.../engineering/` but are `disable-model-invocation`. `grill-with-docs` = load `grilling` + `domain-modeling`.
  - `read-only-postgres` has no connection here; use GET-only `scripts/supabase_rest.py`.
  - The BIOLACT "price outliers" are credit notes (DTE 61).
  - The parser already ignores `RecargoMonto` and `DescuentoPct` for line maths by measurement (see `dte.ts` header).

## Session — 2026-09-17

**The Yunt now uses Vercel AI Gateway, and the historical fuel-report defect is
repaired in production.** Frontend `yunt` is pushed at `9a31459`; migration
`031_repair_scaled_invoice_lines.sql` is live. The gateway change supersedes
D-077 (→ D-101). The production repair changed 212 invoice lines whose quantity
and unit price were provably stored at 10,000x and canonicalised 383 historical
litre aliases. Its audit table keeps the original and corrected numbers.

- Future ZIP ingestion normalises `L`, `Lt`, `LT`, `Litr`, `LTR`, `LTS`,
  `Litro` and `Litros` to `L` before storage (→ D-102). The per-line arithmetic
  guard from D-056 first accepts correct source values unchanged; only a failed
  original calculation followed by a successful known correction is rescaled.
  Anything else stays unchanged and is flagged as unreconciled.
- Live post-repair proof: 0 remaining scale candidates; Gasolina 93 is one `L`
  bucket with 31,203.82 L, CLP 22,672,196 and CLP 726.58/L.
- Proofs: `check-dte-rules.ts` (12 rules), `check-dte-corpus.ts` (4,451 files,
  10,620 lines, exact Python parity), the disposable migration proof, targeted
  ESLint and the production Next.js build all passed. Full-repo ESLint alone
  exhausted 4 GB while scanning generated `.vercel/output`; targeted lint was
  clean.
- **Gotcha — never pull Vercel sensitive variables over a working `.env.local`.**
  The CLI writes `[SENSITIVE]` placeholders because it cannot reveal those
  values, which overwrites usable local secrets. Back up the local file or pull
  into a separate temporary file and merge names deliberately.
- **Raw retention gap:** `/carga` and emailed ZIPs are read in server memory;
  this app stores cleaned relational rows and batch metadata, not the original
  ZIP/XML. The separate `/extractor` accepts standalone XML client-side but does
  not write the invoice database or run this ingest cleanup.

## Session — 2026-09-16 (c)

**v1.4.1 is live: revision `mlmodel-00018-sll`, image `mlmodel:v1.4.1-names`,
100% traffic.** Trained on gold merged with every settled Supabase label
(D-099): 4,251 distinct inputs, 76 classes, 2,000 steps, 76 minutes, one run.
All seven checks in `scripts/88_prove_deploy.sh` pass live. Rollback ladder:
`mlmodel-00017-vg5` (v1.4.1 with blank names), `mlmodel-00016-p8z` (v1.4.0),
`mlmodel-00015-mjr` (v1.3.3).

**All three models on the same 843 locked test rows** (466 of them the rows
v1.4.0 was measured on; no model trained on any of them):

| | v1.3.3 | v1.4.0 | **v1.4.1** |
|---|---|---|---|
| accuracy | 0.501 | 0.610 | **0.777** |
| macro-F1 | 0.486 | 0.624 | **0.709** |
| top-3 | 0.699 | 0.842 | **0.925** |
| auto-accept rate | 0.370 | 0.320 | **0.418** |
| auto-accept precision | 0.644 | 0.882 | **0.966** |
| wrong auto-accepts | 111 | 32 | **12** |
| income (22 rows) | 21/22 | 22/22 | **22/22** |
| rows in unemittable classes | 61 | 32 | **0** |

On the 377 rows that come from the live-only labels: accuracy **0.867**,
top-3 **0.979**, 156 lines auto-filed with **zero** wrong. One honest
regression: on the older 466 rows v1.4.1 makes 12 wrong auto-accepts against
v1.4.0's 6, while being more accurate there too (0.704 vs 0.680).

- **The name list was six weeks stale** — 71 categories against live's 78, so
  `/predict` returned blank names for seven codes (→ D-100). Fixed at the
  source, re-exported with the same weights, redeployed.
- **That exposed a real gap:** `ING-0.7` had no exact-name sales rule, so
  `VENTA DE ACTIVO FIJO` fell through to the model and into review. Four rules
  added; live now answers it by `business_rule`. The test that failed is the
  guard, and it now asserts 78 categories / 7 sales leaves.
- **The familiarity gate is pinned at k=5 / 0.40** via the new `--pin` flag.
  Its own sweep chose k=3 / 0.60, which loses 3 correct auto-accepts and catches
  **zero** wrong ones — strictly worse than no gate. On this model no setting
  catches mistakes cheaply: the cheapest catch costs 17 correct auto-accepts for
  3 catches, because the remaining errors are near-neighbours (D-096 still
  stands; recalibrate, but read the sweep before trusting its pick).
- INT8 parity this time: top-1 disagreement **4.75%** (under even the original
  0.07 default), decision disagreement 3.56%, accuracy 0.7699 → 0.7711.
- Nothing was written to Supabase. The only live access was a read.

## Session — 2026-09-16 (b)

**v1.4.0 was trained on gold only, and gold was not the whole labelled set.**
Live carried 6,842 more settled lines — including the only examples that exist
for `ADM-3.1`, `EXP-15.7` and `EXP-15.8` (215 lines, 0 gold rows). Afaq caught
it. `scripts/102_merge_live_labels.py` now merges gold with every settled
Supabase label by trust order and writes
`Data/candidates/retrain_2026_09_16/` — **4,251 distinct inputs, 76 classes**
against v1.4.0's 2,369 / 73 (→ D-099).

**A v1.4.1 training run is in flight and left running deliberately.** Started
2026-09-16 ~07:50, `models/setfit_retrain_2026_09_16_C`, CPU, batch 8, 2,000
steps, ~1.3 s/step, log `reports/retrain_2026_09_16/train_C.log`. One run only:
two in parallel is what swapped the Mac yesterday. **Next session picks it up
from `Next` 1.**

- The locked split honours **both** earlier splits, so neither v1.3.3 nor
  v1.4.0 ever trained on a row that is now a test row: 843 test rows, 466 of
  them the exact rows v1.4.0 was measured on. Six classes under 5 inputs remain
  untestable (`ADM-1.9`, `EXP-15.1`, `EXP-6.4`, `EXP-8.3`, `ING-0.3`, `ING-0.6`).
- Refused from live: 982 `model` auto-accepts (its own guesses, 0.698 precision)
  and 103 DTE-43 liquidación lines. Conflicts: 167 resolved by trust, 15 dropped
  as ties, plate pairs kept (D-029).
- **`backups/yunt_team_handover_20260913/` is byte-identical to live** and is the
  local mirror to use. `reports/recovery_v1_3_3/supabase_upload/` is **stale** —
  7,335 settled rows, pre-D-047 source names. Nothing was written to Supabase
  this session; the live read was read-only.
- **Decided:** gold plus settled live labels, by trust order (→ D-099). The next
  artifact is **v1.4.1**.
- Regenerable and untracked: `reports/retrain_2026_09_16/live_settled_items.json`
  and `live_invoices.json` (the read-only pull).

## Session — 2026-09-16

**The classifier is retrained and live: v1.4.0, revision `mlmodel-00016-p8z`,
image `mlmodel:v1.4.0`, 100% of traffic.** All seven checks in
`scripts/88_prove_deploy.sh` pass against the live URL; `/model-info` reports
v1.4.0, 73 trained classes, trained 2026-09-16, thresholds unchanged.
Rollback is a traffic shift to `mlmodel-00015-mjr`, which is untouched.

**What was trained.** `scripts/100_build_retrain_candidate.py` built
`Data/candidates/retrain_2026_09_15/` from gold: 2,625 rows → **2,369 distinct
inputs**, 73 classes (v1.3.3 had 1,582 / 67). It fills the missing direction
(1,606 rows from the raw XML line, 0 disagreements; the rest from the category
family), restores 46 audited rows master gold had lost, and adds 2 D-005
synthetic ADM-1.9 rows. Training ran 1,500 steps on CPU into
`models/setfit_retrain_2026_09_15_A`; export with the familiarity index into
`artifacts/v1.4.0-int8` (278 MB INT8).

**Measured on 466 locked test rows no model trained on** (312 are v1.3.3's own
August validation rows), model-only, direction mask applied, thresholds
unchanged, via `scripts/101_evaluate_retrain.py`:

| | live v1.3.3 | **v1.4.0 INT8** |
|---|---|---|
| accuracy | 0.524 | **0.685** |
| macro-F1 | 0.512 | **0.666** |
| top-3 | 0.704 | **0.852** |
| auto-accept rate | 0.406 | 0.416 |
| auto-accept precision | 0.698 | **0.969** |
| wrong auto-accepts | **57** | **6** |
| income (22 rows) | 21/22 | **22/22** |
| rows in unemittable classes | 29 | **0** |

On the 154 test rows drawn from labels added since August: accuracy
0.188 → **0.630**, auto-accept precision 0.082 → **0.959**, wrong auto-accepts
45 → **3**. On the old 312: 0.689 → 0.712, wrong auto-accepts 12 → 3. Per class,
`EXP-1.1` recall 0.05 → 0.89, `AF-1.1` 0.00 → 1.00, `ADM-1.4` 0.12 → 0.75;
regressions are small-count neighbours (`EXP-13.1` 0.40 → 0.20, `EXP-4.2`
0.78 → 0.44 — the Bolos Silo/Heno question is still open with the client).

- **Decided:** every category with gold rows is trained (→ D-095); familiarity
  gate at k=5 (→ D-096); INT8 top-1 ceiling raised to 9% (→ D-097); one locked
  split reused by every candidate (→ D-098).
- One gold label fixed: `SP-00472` ING-0.1 → ING-0.7 (a used milk tank sold is a
  fixed-asset sale; live already said ING-0.7, so Supabase needed no write).
- `tests/test_api.py::test_model_info` no longer pins 67 classes; it reads
  `trained_classes` from the packaged model card. 109 tests pass.
- **Gotcha — two training runs in parallel filled RAM and swap** (9 GB of 10 GB
  swap on a 16 GB Mac). Step time went 4 s → 284 s and a 95-minute run took 9.8
  hours. Run them sequentially: memory, not cores, is the limit. Candidate B
  (per-class cap in the body stage) was killed at step 1249 and never finished;
  A's numbers made it unnecessary.
- **Gotcha — the saved v1.3.3 weights were written by sentence-transformers
  5.5.1 and will not load under the 3.4.1 now in `.venv-train`.**
  `scripts/101_evaluate_retrain.py` therefore loads any SetFit directory as
  plain transformers + mean pooling + the joblib head, which is what the service
  computes anyway. A freshly trained model also needs `_name_or_path` in
  `config.json` before SetFit's model-card helper will load it.
- **Gotcha — numpy 2.2 prints overflow/invalid warnings from the familiarity
  matmul** on the larger index. Checked against float64: identical to 1.4e-8.
  Cosmetic.

## Now

**The reliability design is final (D-108, MCT-189) but not implemented.** The
current code still runs ML before saving and Yunt only after saving. Do not
describe the new matrix as live until MCT-189 is built and all five outcomes
pass for both dashboard and email.

**Both ingest doors already take one or many ZIP/XML files (D-107).** Migrations
`004`–`037` are live. `milk-company` branch `yunt` is pushed at `2402bd0` and is
exactly even with `origin/yunt`; its Vercel Preview built. Production Vercel is
still the 2026-09-16 build, held by Afaq.

**The classifier remains v1.4.1 live and verified** (`mlmodel-00018-sll`). It is a
hard dependency of saving invoices today — see session (f).

## Next

1. **Implement MCT-189 exactly as D-108:** shared Next.js orchestrator,
   deterministic-first partition, availability matrix, Yunt fallback context and
   guarded tools, staged approvals, atomic commit, complete table/XLSX report,
   idempotency, parity and integration tests. Do not add outage retries or
   partial imports.
2. Fix `/carga` language switching so locale chrome changes without losing the
   selected files, preview or approval state. Remove the redundant dashboard
   "How it would look in the email" card.
3. Mount Yunt on the dashboard only after MCT-189 is proved; then create the
   requested granular, practical flow diagram from the implemented behavior.
4. Answer Afaq's webhook questions (facts are in session f).
5. Afaq decides when to deploy production; then measure Analítica and Productos
   on Vercel and run the first real email/XML ingest against the promoted build.
6. Optional: 14-row scoped write for the stored "Ã" names (MCT-181).
7. **STATE.md still needs a consolidation pass:** more than five older session
   entries remain. They were not deleted during this checkpoint because several
   still contain facts not yet promoted to `DECISIONS.md`.

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
