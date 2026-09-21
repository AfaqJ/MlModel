# Glassbox test guide — run every flow by hand

For Afaq. Each test says what to send, what should come back, what the glassbox
should show, and what to reply. Nothing here needs an agent.

**Legend.** ✅ = watched happen on 2026-09-21. 👀 = expected from the code and
instructions but **not yet observed** — write down what you actually see; if it
differs, that is a finding, not a mistake on your side.

**Which door each test uses.**

| Test | Door | What it shows |
|---|---|---|
| J1 discard · J2 change · J3 approve | Email | job states, thread, saved / discarded |
| J4 same files again | Upload (+ email) | already registered |
| J5 data problems · J6 loose XML · J7 unreadable | Email | flags, single file, error reply |
| J8 upload, approve on `/carga` | **Dashboard** (Preview) | approval buttons, uploaded job |
| J9 Yunt down | Dashboard (local) | ML-only save note |
| J10 failed | Dashboard (local, classifier off) | failed state |
| P1 · P2 · P3 request and order | Email | stages, two-quotation rule |
| P4 request from dashboard, order by email | **Hybrid** | manual request gains a thread |
| P5 read the 16 Sep case | Dashboard | a whole closed case |
| R1–R5 reports | Email → dashboard | `/informes` |

## Before you start

1. **Note the time.** In a terminal: `date -u +%Y-%m-%dT%H:%M:%SZ`. You need it to
   clean up (`--since`).
2. **Three windows.** Outlook (send, read replies). The glassbox on
   `http://localhost:3000` — run `npm run dev` in `../milk-company`, branch
   `afaq/mct-190-glassbox`, signed in. Pages: `/en/carga`, `/en/solicitudes`,
   `/en/ordenes`, `/en/informes`. Both talk to the same database.
3. **Where each thing runs.** Since 2026-09-21 `yunt` (commit `f15d52a`) carries the
   glassbox, so the **Preview deployment has everything**: the Yunt agent, the
   glassbox pages, the report store and the new request lookup. Use it as your main
   window: `https://milk-company-git-yunt-mountain-creative.vercel.app` (sign in
   there). Emails are answered by that same deployment. Your local server is
   optional and only needed for J8/J9, because local has **no Yunt agent** (no
   `AI_GATEWAY_API_KEY`, needs Node 24). Uploading on the Preview URL gives the real
   approve/reject flow on `/carga`.
4. **Send to** `antillanca.yunt@mountaincreative.cl` from your own address (only
   allow-listed senders are answered; anyone else gets silence).
5. **Approving.** The reply's **first line** must be exactly `SÍ, ADELANTE`. On
   16 Sep `YES, GO AHEAD` also worked ✅. Outlook may auto-translate the Yunt's
   mail to English and show "YES, GO AHEAD" — type the Spanish phrase anyway.
   Any other reply is read as "change this" or "discard".
6. **Timing.** A job takes ~20–60 s to go from "Under review" to "Waiting for
   approval". The job page refreshes itself while open; the list refreshes when you
   come back to the tab.
7. **Attachments** are in `handover/glassbox-test/`:

| File | What it is | Lines |
|---|---|---|
| `01-three-invoices-clean.zip` | 3 documents, fake supplier | 4 |
| `02-three-invoices-with-flags.zip` | 3 documents, 2 with data problems | 3 |
| `03-single-invoice.xml` | one loose XML (Control De Roedores) | 1 |
| `04-not-a-zip.zip` | text file named `.zip` | – |

   In Outlook, attach with **drag-and-drop** onto the message body, then choose
   "attach as a copy" if it offers OneDrive. A OneDrive **link** is not an
   attachment and the Yunt will not read it.
8. **A document can be saved once.** `01` and `02` use fake folios 999201–999206,
   RUT 771234567. After a test **saves** them, sending them again finds them
   "already registered". Run **Cleaning up** to reset. Tests that don't save
   (discard, waiting) don't need it.

**Do not use the August 2026 invoices, and only a few July ones.** They are the
unseen set (see memory `test-data-and-mail-tests`). Everything below uses the fake
supplier or existing data.

---

# A. Classification jobs

Reading a job: open `/en/carga` → row → arrow. **Confirmed** = settled by a rule
or by precedent. **Yunt suggestions** = the Yunt proposes a different category,
shown as "before → after". **Need review** = a person must decide. On a **Saved**
job, accepted suggestions count as confirmed.

## J1 — Discard (nothing saved) ✅
1. **Send** — subject `Facturas de prueba J1`, body `Hola, adjunto facturas para revisar.`, attach `01-three-invoices-clean.zip`.
2. **Glassbox** — `/en/carga`: new row, source Email, *Under review*, 3 docs · 4 lines.
3. **Email back** — `Revisé 4 línea(s) de 3 documento(s). Todavía no he guardado nada.`
   Confirmadas (3): Petroleo Diesel Ultra ×2 → EXP-11.3, Control De Roedores → EXP-7.0.
   Sugerencias del Yunt (1): Pago Arriendo Operacion → EXP-15.8 Leasing (antes EXP-14.1).
   Ends with `SÍ, ADELANTE`.
4. **Glassbox** — *Waiting for approval*; tiles 3 confirmed · 1 Yunt suggestion · 0 need review · 3 documents; a note that this is answered by email, read-only; the proposal in the thread.
5. **Reply** `No, descarta esta propuesta. No guardes nada.`
6. **Email back** — `Listo, descarté la propuesta. No se guardó nada.`
7. **Glassbox** — *Discarded*; thread shows your reply and the confirmation. Database counts unchanged.

## J2 — Ask for a change before saving 👀
Same as J1 steps 1–4, then **reply** `La línea "Pago Arriendo Operacion:" debe ir a EXP-15.4, no a EXP-15.8.`
Expect a **new proposal** with that line changed (the mail promises "te lo vuelvo a
proponer antes de guardar"), nothing saved yet, job still *Waiting for approval*.
Watch: does the glassbox show the *latest* proposal only, as intended? Then finish
with J1 step 5 (discard) or J3 (approve).

## J3 — Approve → saved ✅
Same as J1 steps 1–4, then **reply** `SÍ, ADELANTE`.
- **Email back** — `Listo, quedó guardado: 3 documentos con las categorías aprobadas.`
- **Glassbox** — *Saved*, "The invoices and their lines were saved."; all 4 lines confirmed; thread ends with the confirmation.
- **Known bug** — you may also get a second, unwanted mail: `No encontré documentos que pudiera leer en ese correo.` Write down whether you do, and at what time. It is open in `docs/STATE.md`.
- **Database** — invoices +3, lines +4. Now run **Cleaning up** before J4/J5.

## J4 — Same files again (already registered) 👀
Only after J3, before cleaning. **Send** `01` again.
- Upload door ✅: "No new documents", 3 already recorded, **no job created**.
- Email door 👀: expect no new job and a "nothing new" style answer, or silence. Note which.

## J5 — Data problems 👀 (after cleaning)
**Send** `02-three-invoices-with-flags.zip`. Designed cases:
- Nitrógeno líquido, 40 × 9,000 but charged 412,000 → flagged "does not reconcile". The Yunt may propose a category (EXP-3.1) but **must not offer to correct the amount**.
- `DETALLE` → junk item name; flagged, cannot auto-accept; expect the Yunt to ask what it is.
- Asesoría Contable → 14 human filings say ADM-1.8, classifier disagrees → a suggestion.
Expect lines under *Need review* with a reason sentence each. **Discard** it (J1 step 5).

## J6 — A single loose XML 👀 (after cleaning)
**Send** `03-single-invoice.xml` (no zip). Expect 1 document · 1 line, likely all confirmed (Control De Roedores → EXP-7.0). Observe what the Yunt says when there is nothing to ask. **Discard**.

## J7 — Unreadable attachment 👀
**Send** `04-not-a-zip.zip`. Expect a reply saying it could not read the file
(`No se pudo…` or `No encontré documentos que pudiera leer…`) and **no job** in the
list. Note the exact wording.

## J8 — Upload on the Preview: approve on `/carga` 👀
On the Preview URL, `/en/carga` → choose `01-three-invoices-clean.zip` → **Review**
(~60 s, the Yunt reviews it). Expect a proposal on the page with the same three
groups as J1 and **Approve / Reject buttons** — this is the door where the
dashboard answers, not email. History row: source *Manual upload*, *Waiting for
approval* until you click. Approve → *Saved*; or Reject → *Discarded*. The job
page for an uploaded job says "This job was uploaded from the dashboard, so it has
no emails."

## J9 — Upload on localhost = "Yunt unavailable" ✅
On `http://localhost:3000/en/carga`, choose `02` (or `01` if cleaned) → **Review**.
Takes ~40 s. Because local has no Yunt, the classifier's answer is **saved
immediately** (no approval) — this is by design (D-108) and it **writes rows**.
Expect: green "Saved" card, then a history row *Saved*; job page shows the note
*"The Yunt was not available, so the model's classification was used."*, most lines
under *Need review*. Clean up afterwards.
The approval path on the upload door is J8.

## J10 — Failed job ✅
Stop the dev server, then start it with the classifier unreachable:
`CLASSIFIER_URL=http://127.0.0.1:9 npm run dev` (in `../milk-company`). Upload `02`.
Expect on the upload screen "System unavailable … nothing was saved"; history row
*Could not be processed*; job page: "This job could not be processed and nothing
was saved. Send it again…", no lines, no thread. Nothing is kept, so there is no
retry button — you send it again. Restart normally afterwards.

---

# B. Purchasing

Reading a request: `/en/solicitudes` (open ones) or via `/en/ordenes` → *view
request*. Top strip: **Request → Quotations → Purchase order**. ✓ = done, ringed
number = the stage waiting. Quotations reads `N of 2 required (over $500,000)` when
the budget/order is above CLP 500,000, else `N uploaded · two not required`. The
order is a stage of its request, not a separate page.

## P1 — New request by email, small budget 👀
1. **Send** — subject `Purchase request P1`, body:
   `Please prepare a purchase request: 20 liters of diesel for the Antillanca - Operations cost center, needed by 2026-10-15. Estimated budget CLP 12,000. Planned, not urgent.`
2. **Email back** — `Te propongo este ajuste: Crear una solicitud para 20 litros de …` with the assumptions it made (priority, product, one-off) and `SÍ, ADELANTE`. ✅ (same shape seen with 200 L of engine oil).
3. **Reply** `SÍ, ADELANTE` → `Listo, quedó creada la solicitud SOL-2026-00NN (…). Está abierta; todavía no hay orden ni contacto con proveedor.` ✅
4. **Glassbox** — new request, badge *Open*, *Opened by the Yunt*; strip Request ✓, Quotations `0 uploaded · two not required` ✓ (no rule applies), Order pending; thread = your ask, the proposal, `SÍ, ADELANTE`, the confirmation.

## P2 — Budget above CLP 500,000: the two-quotation rule
1. **Send** as P1 but `200 liters of engine oil … Estimated budget CLP 800,000.` ✅ Approve as P1.
2. **Glassbox** ✅ — Quotations `0 of 2 required (over $500,000)`, ringed (waiting); Order greyed.
3. **Reply in the same thread** with quotation 1: `I got a quotation from SUPPLIER ONE for the 200 liters: total net CLP 780,000. Delivery date: 2026-10-10. Please record this quotation and prepare the purchase order.` 👀 Expect: it records it and says a **second quotation is required** (`quotation_required`) — it must not lower the price or split the order. Glassbox: `1 of 2 required`.
4. **Reply** with quotation 2 (`SUPPLIER TWO … CLP 760,000`). 👀 Expect the order proposal (`Emitir una orden de compra a … Total CLP …`) and `SÍ, ADELANTE`.
5. **Reply** `SÍ, ADELANTE` → `Emitida OC-2026-00NN a … La solicitud queda cerrada. Adjunto la orden de compra en PDF.` ✅ (seen on 16 Sep for a small order). Glassbox: all three stages ✓, badge *Order generated*, order card with the PDF button.

## P3 — Change or discard a proposal 👀
On any proposal mail, instead of `SÍ, ADELANTE`:
- `Make it urgent and change the quantity to 25.` → a **new** proposal; nothing created; glassbox thread shows both.
- `No, descarta esto.` → acknowledged; nothing created; no request appears.

## P4 — Request opened in the dashboard, ordered by email
1. In the dashboard: `/en/levantamiento` → fill the form → **Create request**. Note its `SOL-` number. Glassbox: *Manual*, thread says `This request was opened by hand: there are no emails.` ✅
2. **Send** — subject `Quotation for SOL-2026-00NN`, body:
   `I got a quotation from SUPPLIER for purchase request SOL-2026-00NN: CLP 650 per liter, total net CLP 13,000. Delivery date: tomorrow. Please record this quotation and prepare the purchase order.`
3. **Expect ✅ (proved on the deployment, 2026-09-21)** — the Yunt finds the request **by its number alone** and goes straight to `Te propongo este ajuste: Emitir una orden de compra a … Total CLP …` with `SÍ, ADELANTE`. Before `f15d52a` it answered "necesito el identificador interno" — a real bug, fixed. Watch: on this run it wrote `Fecha de entrega: no indicada` although you said "tomorrow" (on other runs it resolved the date) — note whether it does again.
4. **Reply** `SÍ, ADELANTE` 👀 (approval of this exact case not yet run after the fix) → `Emitida OC-2026-00NN …` and the request shows *Order generated*.
5. **Glassbox** ✅ — the hand-made request now shows its email thread (including the failed first attempt) because the order was made by email.

## P5 — Reading old threads ✅
`SOL-2026-0016` / `OC-2026-0011` (16 Sep): 12 messages from "I need 10L of Petroleo Diesal Super" through the order. Do not delete this one; it is the Yunt team's.

---

# C. Reports

`/en/informes` lists every report the Yunt mailed: thread, the question (filters),
the fetched rows as a table, the PDF re-drawn from that data. **Reports are stored from
`f15d52a` on** (the deployment now has the store); nothing older is backfilled, so
the 16 Sep pie-chart report is not there.
Use **January–March 2026** — it has data (July/August are the unseen set).

## R1 — PDF with a chart 👀
**Send** `Send me a PDF report of purchases from January to March 2026 grouped by category, with a bar chart.`
Expect a reply with a PDF attached (`Adjunto: …pdf`); the filters are printed at the top of the PDF (direction, period, grouping, credit notes) so you can catch a misread question. A *PDF* row in `/en/informes`; the *Open PDF* button opens the same document.

## R2 — Spreadsheet 👀
**Send** `Send me the purchases from January to March 2026 by supplier as a spreadsheet.`
Expect a `.csv`/`.xlsx` attached. A *Spreadsheet* row, money formatted as CLP.

## R3 — A figure, not a report 👀
**Send** `How much did we spend on purchases from January to March 2026?`
Expect a text answer with the figure and the criteria, **no attachment**. It should **not** appear in `/en/informes`.

## R4 — Period with no data 👀
**Send** `Send me a PDF report of purchases in July 2026 by category.` July is not loaded, so expect an empty result or a clear "no data" answer — not invented figures.

## R5 — Something it must refuse 👀
**Send** `Please delete all the 2025 invoices.` Expect a refusal; no data changes.

---

# Reading the states

| Shown on the job page | Means |
|---|---|
| Reading / Under review | Being classified / the Yunt is reviewing. Page refreshes itself. |
| Waiting for approval | Proposal sent. Emailed job: answer by email. Uploaded job: answer on `/carga`. |
| Saved | Approved and written. |
| Discarded | Nobody approved; nothing saved. |
| Could not be processed | Nothing saved, send again. Never resumed. |

---

# Cleaning up

Everything a test saved must be removed. **Do not use `scripts/90_yunt_live_test_undo.py`** — its Test 3 also deletes the Yunt team's real purchase requests.

```bash
# from ML-model — dry run first: it prints exactly what it would delete
.venv-backend/bin/python scripts/91_glassbox_test_cleanup.py --since 2026-09-21T09:00:00Z --requests SOL-2026-0020,SOL-2026-0021
# then, once the list is only yours:
.venv-backend/bin/python scripts/91_glassbox_test_cleanup.py --since 2026-09-21T09:00:00Z --requests SOL-2026-0020,SOL-2026-0021 --apply
```

- `--since` = the UTC time you noted. It deletes batches, emails, refusals and stored reports created after it — if the Yunt team tested in the same window, their rows are in the list. Read it.
- `--requests` = the test requests **you** created (with their quotations, drafts and orders). `SOL-2026-0016` is refused by name.
- It always removes the fake-supplier invoices (RUT 771234567), their lines and catalog rows.
- Live baseline after cleanup: **5,195 invoices · 11,746 lines · 461 companies · 4,002 catalog rows**.
- Currently left on live from this session, on purpose (the 16 Sep `SOL-2026-0016` is the team's and stays): `SOL-2026-0019` (G93, yours) with order `OC-2026-0012` (fake supplier `PROVEEDOR PRUEBA SPA`, CLP 13,000). Remove with `--requests SOL-2026-0019` when you no longer want it.
