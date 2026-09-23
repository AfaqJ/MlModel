# STATE — where this project is right now

Updated every session. Last 5 sessions only; anything older that still matters
lives in `DECISIONS.md`.

## Session — 2026-09-22 — B_july70 live at 100% (D-118, D-119), Verisure rule shipped, Jev concluded

**Now live, verified:** Cloud Run traffic for `mlmodel` is 100% on `mlmodel-b-july70-rc1`
(`scripts/88_prove_deploy.sh` passes against the base URL). `CLASSIFIER_URL` already pointed at the
base URL, not a revision tag, so no Vercel change was needed — the Yunt calls B_july70 on its next
classifier call. Picked over F_targeted_fix because F's headline August number was training-
contaminated (D-118 §1); B_july70 wins every honest exam.

**Verisure → `ADM-1.2` is now a real deterministic rule, month/contract-agnostic (D-119).**
Checked against real ledger data first: 18/18 Verisure lines ever seen (2025 locked843, July 2026,
August 2026) are `ADM-1.2`, no exceptions, matching Cristian's email exactly. **First attempt was
wrong and Afaq caught it in-session**: 16 exact `item_text|provider` rows keyed on the full invoice
text, which embeds the month and a contract number — would have silently stopped working every month
starting in September. **Replaced with a new `providerRules` mechanism** (new
`app/data/provider_rules.csv`, new `RulesData.providerRules` field, matched in `applyRules()`
independent of item_text) for suppliers whose entire business with this client is one thing. Verified
live against 2025, 2030, and a never-seen contract number — all resolve correctly, because the rule
never reads the wording at all. Regenerated `rules-data.json` on **both** `milk-company` branches —
`yunt` and `experiment/jev-typesafe`. Python/Cloud Run (`app/inference/business_rules.py`)
deliberately NOT touched — the TS `applyRules()` layer already intercepts these lines before either
classifier runs, so the fix works without a second Cloud Run redeploy, but
`scripts/check-rules-parity.ts` will report a real, known, temporary Python/TS disagreement until
that side catches up. **Neither `milk-company` branch is committed yet.**

**B_july70's remaining August wrong-auto-accepts (6, pre-Verisure-fix) split exactly two ways:**
4/6 were Verisure (now fixed above), 2/6 are the unresolved fuel/plate case — the same gap Cristian
named himself: untagged fuel is "our team to place" (his words, 2026-08-18).

**Checked whether the Yunt's precedent search would have caught the Verisure bug on its own — it
would not have, and the reason matters:** `yunt_category_precedent`
(`supabase/025_invoice_context_precedent.sql`) ranks `human_confirmed` evidence first but falls back
to the model's own past `pipeline_auto_accepted` guesses when nothing human-confirmed exists. No
Verisure line had ever been human-corrected in Supabase, so the only "precedent" available was the
model's own prior wrong guesses agreeing with each other. **The precedent safety net has a blind
spot exactly where a bug is systematic** — worth remembering for the next one.

**Real client email thread (Cristian, read via Outlook this session) cross-checked against
`docs/CLIENT_CONVENTIONS.md` — everything in it was already accurate**, independent confirmation the
doc is trustworthy: plumbing-including-buildings (§9.2), GEA technician hours (§9.1), bale-making
contractor-is-not-a-signal (§9.5), hardware stores having no defaultable rule, bank commissions →
`ADM-3.1`. Nothing new to add there. Useful framing for the client conversation, in his own words
(2026-09-07): *"most of the invoices requiring review are the items we discussed that cannot be
reliably distinguished using a clear rule"* — he already accepts this, in writing.

**Jev (Typesafe AI) experiment — concluded for now, branch `experiment/jev-typesafe` in
`milk-company`, left as-is, not merged, not deleted.** Six rounds of prompt iteration (category-
description hints, an explicit `NEEDS_REVIEW` abstain option, positive rules sourced from real error
patterns) closed most of the accuracy gap to B_july70 on `locked843` (~73–76% on commits, comparable
to or better than B's 71.0%), but cross-validation on July and August (`--exam july`/`--exam august`
in the eval script) showed the tuning does not generalize consistently: Jev beat B_july70 on July
accuracy (51.5% vs 46.2%) but was ~5x less safe (14 vs 3 wrong auto-accepts); on August it flipped
(46.8% vs 60.6% accuracy, 2 vs 6 wrong auto-accepts, safer). **B_july70's wrong-auto-accept count
stayed in a tight band (6, 3, 6) across all three months; Jev's swung from 2 to 24** — that
instability, not either single accuracy number, is why Jev isn't ready. Two real analytical mistakes
happened and were caught mid-session by checking full label distributions instead of single examples
(`CONTROL DE ROEDORES` is 17:1 `EXP-7.0`, not the reverse; GEA splits 6:2:2 across three categories,
not one) — fixed version is what's on the branch. Full payload structure and every hint are in
`milk-company/experiments/jev-eval/run.ts` (`--dump` flag shows the exact API payload).
**Untried if this resumes:** Typesafe's `examples` field (distinct from `what`/`not_for`), real
precedent retrieval (few-shot real historical lines per call), hierarchical two-stage classification,
calibrating Jev's own auto-accept threshold instead of reusing B_july70's 0.75/0.50.

**Still open, in order:**
1. Recalibrate B_july70's auto-accept threshold on locked843 — still running on v1.4.1's reused
   0.75/0.50, not its own tuning (D-118 §4).
2. Commit the Verisure fix on both `milk-company` branches (currently uncommitted).
3. The Yunt reliability smoke test (D-116/D-117, still only unit-tested) — needs the AI Gateway
   budget checked first.
4. Demo date still unknown — ask Afaq.

## Session — 2026-09-21/22 (handover) — Yunt reliability (D-113–D-117), July/August model evaluation

**Read `reports/overnight_2026_09_21/README.md` first** — it lists where the July/August
invoices, the accountants' ledgers, the ML reports and every script are.

**Start here:** variant **F_targeted_fix** is training now (background, PID logged in
`reports/overnight_2026_09_21/train_F_targeted_fix.log`; `caffeinate -i -w <pid>` is attached
so a closed lid no longer stalls it — it already lost ~100 minutes once to sleep before that).
Check progress: `tail -c 300 reports/overnight_2026_09_21/train_F_targeted_fix.log | tr '\r' '\n' | tail -3`.
When it finishes, score it — `.venv-train/bin/python scripts/104_eval_overnight.py --model F_targeted_fix=models/overnight_2026_09_21/F_targeted_fix --exam locked843` plus a rerun of
`august_score.py` with F's path swapped in — against **B_july70**, the current leader (below),
before deciding which model goes forward. Nothing has been deployed; the live classifier is
still v1.4.1.

### The classifier: two real months of evidence now, not one

- **The old test set overstated accuracy**: 98% of its suppliers were already in training, vs
  67% for July. **B_july70** (old training data as-is + 70% of July's suppliers, no diet
  changes) is the honest winner so far, checked on data it never trained on both times:
  - July's held-out 30% of suppliers: 46.2% top-1 vs v1.4.1's 37.7%, 3 wrong auto-accepts vs 7.
  - **August, entirely offline** (rule engine run locally via `august_offline_rules.ts` — pure,
    no DB — ground truth from the accountant ledger, both SetFit dirs scored locally, no
    Cloud Run call, nothing written anywhere): 60.6% top-1 vs 43.6%, 6 wrong auto-accepts vs 9.
  - The "diet fix" variants (A/C/D: thinned supplier caps, rule-row downweighting) all scored
    **worse** than both v1.4.1 and B — a genuine negative result, don't repeat that approach.
- **Variant F** adds only 47 hand-picked rows to B's training: categories still under 30
  examples, plus ADM-1.2 (ithe Verisure monitoring line — B calls it ADM-1.7 at 0.96–0.99
  confidence, in *both* July and August). **Two rows were caught and dropped, not trained
  through**: fuel wording that is genuinely ambiguous without the plate (same text, opposite
  label in old gold vs the August ledger — proven, not assumed, by a real collapse
  contradiction) and one milk-filter line with the same kind of client-filing conflict; both
  are for the client to resolve (D-041), not us. A second check caught 2 more candidate rows
  that were word-for-word duplicates of **locked test rows** — including those would have
  leaked test answers into training under a new id; both dropped before training started.
  57 August lines + 117 July lines were deliberately held out of F's training, for an honest
  recheck (`reports/overnight_2026_09_21/F_holdout_exam.csv`).
- **Recurring, real bug for the client, found in both months**: Verisure monitoring lines are
  booked ADM-1.2 (Comunicaciones) by the accountants; the model is very confident they're
  ADM-1.7 (Otros Gastos Administracion), every month. Worth a fifth business rule regardless of
  which model ships.
- **Not yet run**: the mandatory income-slice gate (`docs/TEST_CHECKLIST.md`) on either
  candidate. Do this before treating either as a release candidate — aggregate accuracy alone
  is not a release gate here.

### The Yunt review path: D-114 through D-117, all pushed and on the Preview

Built because two live 100-invoice test runs each wasted real money on a bug, in this order:

1. **Run 1** — the AI Gateway key had a $5 lifetime budget; it ran out mid-review, and the
   pre-existing code saved the whole batch unapproved (the old D-108 "ML only" row). **Fixed
   (D-114):** a Yunt that does not finish now never causes a write; the wait follows session
   liveness (probed every 30s) instead of a fixed 240s/270s deadline, capped by what's left of
   the function's now-800s limit (Fluid compute, was 300s).
2. **Run 2** (after D-114/D-115) — 3 of 4 packets delivered their reviews in 2–3.5 minutes; the
   job discarded **all four**, including the three that had already been paid for, because the
   wait logic treated "one packet done, one still owed" as healthy only until the *whole* thing
   hit the ceiling. **Fixed (D-116):** packets that delivered are kept; a group nobody reviewed
   in time is marked "needs a person" in the staged plan rather than silently dropped or
   discarded with everything else.
3. **Audit pass after that (D-117)**, done because Afaq does not want a third wasted run: one
   failed session no longer aborts the whole wait (only total silence for 45s does); a silent or
   never-started packet is retried exactly once; a failed dispatch no longer orphans sessions
   that already started and are being paid for; each review session is capped at $1.50
   (a packet costs ~$0.3–0.7, so this is a loop guard, not a target).
4. **D-115** (cost, same audit): the Yunt is no longer shown lines the client's own rules
   already settled (~25% of lines, ~1/3 of the spend) — only classifier lines and rule-held
   lines (unplated fuel, DTE 43) go to review. Reasoning dropped `high`→`medium`.

**Honest status: D-114 and D-115 were proven live** (run 1 confirmed the no-save behaviour and
the correct error reply; run 2 confirmed packets dropped from 6→4 correctly). **D-116 and
D-117 have NOT been live-tested — only unit-tested** (9 scenarios in
`scripts/check-await-verdicts.ts`, plus a 400-line/10-packet case in
`check-orchestrator-matrix.ts`). The next real send is the actual test of them. **Do the
3-invoice smoke send first** (`handover/glassbox-test/A-EMAIL-flow-3-unseen-july-invoices.zip`
— this was planned twice and never actually sent), then `~/Desktop/july-100-invoices.zip`,
then the month. Watch the Vercel logs for `[yunt] packet N delivered after Ss` and
`... is silent; starting it once more` — that's the new behaviour proving itself.

**Open:** the income-slice check; picking B vs F once F is scored; re-setting the auto-accept
confidence bar for whichever model ships (never on July/August numbers, only on `locked843`);
raising the client questions from the ledgers (placeholder plates, Verisure, sulfato de cobre,
AdBlue, Spartan Check, the milk-filter conflict); a full pipeline rehearsal (email → rules →
model → Yunt → approval) on a still-unseen slice before the actual demo; the demo date itself
is still unknown — ask Afaq.

## Session — 2026-09-21 (evening) — handover to the next session

**Start here.** `yunt` in `../milk-company` is pushed at `e2f7f48` (Preview build
not confirmed Ready). Migrations `041` and `042` are live (`042` confirmed by a
query on both functions). This repo's commit `b59f3fa` (D-111/D-112 docs) is on
`yunt-backend` and **not pushed**. Production is still the 2026-09-16 build, held
by Afaq.

**Built and pushed this session:**
1. **The agent's clock** (`382188b`). Each message handed to the agent now carries
   "Fecha y hora del mensaje (America/Santiago)" from Resend's `created_at`; the
   instructions and the two draft tools tell it to resolve "mañana / el lunes / fin
   de mes" against it and state the date back. Check: `scripts/check-yunt-dispatch.ts`.
   **Proved:** the message the agent receives. **Not proved:** what the model then
   writes — needs a real "needed by tomorrow" email.
2. **`041` proved** (`prove-041-confirmation-chain.ts`: accepted + five refusals, cleaned up).
3. **D-111** (`4056d95`, migration `042`): any waiting job is approved or discarded
   from its page or `/carga`. Approve opens a dialog of the latest stored proposal
   grouped by category; the request carries the plan hash (409 if it moved, 400 if
   absent). Check: `scripts/check-approve-guard.ts`. **Driven in the browser:** the
   button on an emailed job, the dialog, Cancel writes nothing, the 400/409 answers.
   **Not driven: the actual save of an emailed job** — Afaq is testing it with
   `handover/glassbox-test/exact-replay-fake-supplier/S1-…zip` (steps in the chat;
   cleanup with `scripts/91_glassbox_test_cleanup.py`, dry run first).
4. **D-112**: the Yunt may suggest from wording, description and supplier when
   there is no precedent. Instruction-only. **Unmeasured** — read the "Yunt
   suggestions" group of the next real jobs before trusting it.
5. **Theme** (`663106d`): graphite chrome, charts keep their colours (Afaq's call
   after his boss disliked the colourful UI; someone else will do the UI proper).

**Open, in rough priority:**
- Afaq's manual tests: D-111 save of an emailed job; the clock via email.
- Two jobs left waiting **on purpose**: `a9fa59e8…` (3 real July invoices, email) and
  `3b82b3db…` (CUMBRE CONSULTORES upload). Approving either writes real invoices.
- **Parked:** an email thread for dashboard uploads — the Yunt does not know who to
  write to (`docs/YUNT_OPEN_DECISIONS.md` §8).
- **The stray "No encontré documentos que pudiera leer en ese correo" reply is
  untraced.** Lead: `src/app/api/yunt/inbound/route.ts:220` sends that text for any
  job that ends `empty`, not only when nothing was readable. Needs the Vercel logs
  for ~06:44 Chile on 21 Sep.
- Not yet run, marked 👀 in `docs/GLASSBOX_TEST_GUIDE.md` §5.
- Old test rows untouched: 3 discarded jobs from 19 Sep, their 2 email rows, the
  16 Sep report row. `yunt_test_3.zip` is still in Afaq's OneDrive `Attachments`.
- Ten older audit findings: `../milk-company/docs/OPEN_QUESTIONS_2026_09_03.md`.
- This file needs a consolidation pass (see the note under "Prior checkpoint").

**Gotchas that cost time:**
- After `git checkout` swaps files, Next's Turbopack served **stale CSS in both
  directions**. Dev: stop, `rm -rf .next/dev`, restart. Build: `rm -rf .next/cache`.
  Afaq's `localhost:3000` server was still stale at the end of the session.
- The auto-mode classifier refused to insert synthetic rows into the live database.
  A proof that needs a live write needs Afaq's explicit OK first.
- A check that hardcodes a theme colour breaks on a theme change
  (`check-yunt-spreadsheet.ts` did; it now reads `THEME`).
- To confirm `042`, a `prosrc like '%D-111%'` query reports `false` for
  `reject_yunt_batch` because that function got no comment. Test that the old
  refusal text is **gone** instead.

**Working agreements (unchanged):** client-facing pages and mail never show engine or
confidence (D-108/D-109); tests use synthetic or a few July documents, never August;
mail tests go through Afaq's Outlook; brief in plain language before building.

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
   and the thread. Driven: closed with an order (the 16 Sep case, SOL-2026-0016
   / OC-2026-0011, since removed as test data), open needing two quotations, open with the rule not applying,
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
supplier, CLP 13,000).

**Deployed.** `afaq/mct-190-glassbox` pushed and fast-forwarded into `yunt`
(`46b25af` → `f15d52a`); `npm run build` passed locally, the Vercel Preview is
Ready (`milk-company-git-yunt-mountain-creative.vercel.app`), and the new lookup was
proved on it: a request made in the dashboard (`SOL-2026-0020`, since removed) was
found from its number in an email and an order proposed. Production is still the
2026-09-16 build.

**Live data cleared (Afaq, 2026-09-21):** every test row removed, including
`SOL-2026-0016` / `OC-2026-0011` and its 6-email thread, which he confirmed were
test data. Now: 5,195 invoices / 11,746 lines / 461 companies / 4,002 catalog
rows; purchasing tables and `yunt_reports` empty; 3 old *Discarded* jobs and 3
email rows remain. Two unseen-July ZIPs for a fresh run are in
`handover/glassbox-test/`.

**Approval survives chat (D-110), found by Afaq's own test.** After "I agree, log
them", the Yunt's plain reply carried no confirmation, so his later `SÍ, ADELANTE`
answered a message the gate did not recognise and was refused; separately the model
wrongly refused `YES, GO ahead` (the database is case-insensitive). Fix: migration
`041` (**must be pasted**; prove with `scripts/prove-041-confirmation-chain.ts`),
two instruction changes, pushed to `yunt` at `9e71471`. Also fixed: the Review
button showed no spinner until the job appeared (React holds form-action state);
an uploaded job's page had no approve/reject; a confirmed line could say "a person
should confirm this".

**Hand-run guide:** `docs/GLASSBOX_TEST_GUIDE.md`, attachments in
`handover/glassbox-test/`, and `scripts/91_glassbox_test_cleanup.py` (scoped,
dry-run first; `--zip` undoes exactly the documents in the zips you name).

**Open, found this session:**
- **A second, unwanted reply.** One `SÍ, ADELANTE` produced both the correct "Listo,
  quedó guardado" and "No encontré documentos que pudiera leer en ese correo" —
  the latter is only sent when a message has ZIP/XML attachments that did not
  yield files, and no inbound row was recorded for it. Needs the Preview logs.
- **Reports are stored from `f15d52a`.** Nothing older is backfilled.
- **Do not run `scripts/90_yunt_live_test_undo.py --apply`**: its Test 3 deletes
  every `created_via='yunt'` request and order with no per-test switch. Use
  `scripts/91_glassbox_test_cleanup.py` (dry run first).
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

