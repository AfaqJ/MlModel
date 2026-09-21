# The glassbox, tested end to end — what was done, where it showed, how to redo it

Written 2026-09-21 after driving MCT-190 in a browser, signed in, with Outlook open
beside it. Everything below happened; where something was **not** run, it says so.
Times are as the dashboard showed them (Chile). The deployment is
`https://milk-company-git-yunt-mountain-creative.vercel.app` (branch `yunt`,
commit `f15d52a`); I used a local server on `localhost:3000` (same database).

**Live data is now empty of every test.** Baseline: 5,195 invoices · 11,746 lines ·
461 companies · 4,002 catalog rows · 0 purchase requests / orders / quotations /
reports · 3 old discarded jobs (see the end).

---

## 0. Which pages show what

| Page | Shows | Read-only? |
|---|---|---|
| `/carga` | upload form, and under it the history of every job, newest first | history yes, form no |
| `/carga/[id]` | one job: state, lines, email thread | yes (uploaded jobs have approve/reject on `/carga` right after upload) |
| `/solicitudes` | **open** requests only | – |
| `/solicitudes/[id]` | stage strip Request → Quotations → Order, the request, quotations/order forms, email thread | thread yes |
| `/ordenes` | issued orders, each with a "view request" link | yes |
| `/informes` | every report the Yunt mailed | yes |
| `/informes/[id]` | thread, the question as filters, the fetched rows as a table, the PDF | yes |

Nothing on any of these pages names which engine decided a line or how confident it
was (D-108). There is no chat: the conversation is email, shown read-only.

**How an object moves between pages** (all observed):
- A **job** never moves. Its history row and its page are the same object; its
  *state* changes in place (Under review → Waiting for approval → Saved). The row
  keeps its place by arrival time.
- A **request** is on `/solicitudes` while open. When its order is issued it
  **leaves that list** ("No open requests") and appears on `/ordenes`; its own page
  stays and now reads *Order generated* with the order card and a PDF button.
- A **hand-made request** shows "opened by hand: there are no emails" until an email
  touches it; then its thread appears on the same page.
- A **report** appears on `/informes` the moment it is mailed.

---

## 1. Jobs (invoices)

### 1a. Email → waiting → approve → saved *(email, then glassbox)*
| Step | Channel | What I did / said | What showed, where |
|---|---|---|---|
| 1 | Email | Outlook → `antillanca.yunt@mountaincreative.cl`, subject `Facturas de prueba glassbox`, body `Hola, adjunto facturas de prueba para revisar.`, attached a ZIP of 3 documents (4 lines, fake supplier). | ~40 s later `/carga` history got a row: Email · `afaq@…` · 3 docs · 4 lines · **Under review**. |
| 2 | Glassbox | Opened the row. | Job page **Under review**; it moved to **Waiting for approval** on its own (no click). Tiles 3 confirmed · 1 Yunt suggestion · 0 need review · 3 documents. Note: "answered by email, read-only". |
| 3 | Email | Yunt's mail `Re: Facturas de prueba glassbox`: "Revisé 4 línea(s) de 3 documento(s). Todavía no he guardado nada." with Confirmadas (3) and Sugerencias del Yunt (1: *Pago Arriendo Operacion* → EXP-15.8, antes EXP-14.1), ending with the phrase to type. | The same text appeared in the job page's thread. Nothing written to the database yet. |
| 4 | Email | Replied `SÍ, ADELANTE` (first line). | Job page → **Saved**: "The invoices and their lines were saved." The suggested line moved from *Yunt suggestions* into *Confirmed* (in place). Thread gained my reply and `Listo, quedó guardado: 3 documentos con las categorías aprobadas.` |
| 5 | Database | Checked. | Invoices 5,195 → 5,198; lines 11,746 → 11,750; batch `completed`. **This is the emailed-approval-writes-rows path MCT-189 had not shown live.** |

**Next possibilities from *Waiting for approval*:** reply the phrase → *Saved*;
reply "descarta" → *Discarded* (nothing kept); reply a change ("línea X a categoría
Y") → a **new** proposal, still waiting *(not run — 👀)*; no reply → it just waits.
An **emailed** job cannot be approved from the dashboard (the database refuses).

**Oddity seen:** that one reply also produced a second, unwanted mail from the Yunt,
"No encontré documentos que pudiera leer en ese correo." Only one inbound row was
recorded, so the cause needs the Vercel logs. Open in `docs/STATE.md`.

### 1b. Email → reject *(19 Sep, before this session; page checked today)*
July ZIP, 2 invoices; reply `No, descarta esta propuesta por ahora. No guardes nada.`
→ Yunt: `Listo, descarté la propuesta. No se guardó nada.` → job page **Discarded**,
"No se guardó nada", both lines still listed as *Need review*, thread shows the whole
exchange. Nothing was ever written.

### 1c. Upload with Yunt available *(not run)*
Needs the deployment (local has no agent). Expected: proposal on `/carga` with
approve/reject buttons; row *Waiting for approval*. 👀

### 1d. Upload, Yunt unavailable → saved at once *(dashboard, local)*
Chose the 6-document fake-supplier ZIP on `/carga` → Review. ~40 s. The screen said
"Saved — the Yunt was not available, so the model's classification was saved", and
the history got a row **Saved** with the note on its page: *"The Yunt was not
available, so the model's classification was used."* 3 confirmed, 4 need review.
This path **writes without approval by design** (D-108). I removed it afterwards.

### 1e. Failed job *(dashboard, local with the classifier off)*
Started the server with `CLASSIFIER_URL=http://127.0.0.1:9`, uploaded again.
Upload screen: "System unavailable … nothing was saved." History row **Could not be
processed**; job page: "…nothing was saved. Send it again whenever you like: nothing
is left half done." No lines, no thread, no retry button. *Next:* send the files
again; a new job starts from scratch.

### 1f. Everything already registered *(dashboard)*
Uploading documents already in the database: "No new documents · N already
recorded", **no job created** — so there is nothing in the history for it.

---

## 2. Purchasing

Stage strip meaning: ✓ done · ringed number = waiting · grey = not yet. Quotations
reads `N of 2 required (over $500,000)` above CLP 500,000, otherwise
`N uploaded · two not required`.

### 2a. Request by email, budget over $500,000 *(email → glassbox)*
1. **Email**: subject `Purchase request glassbox test`, body `Please prepare a purchase request: 200 liters of engine oil for the Antillanca - Operations cost center, needed by 2026-10-15. Estimated budget CLP 800,000. Planned, not urgent.`
2. **Yunt** replied with `Te propongo este ajuste: Crear una solicitud para 200 litros de Aceite de motor …`, its assumptions (planificada, producto, compra única) and the phrase.
3. **Email**: `SÍ, ADELANTE` → `Listo, quedó creada la solicitud SOL-2026-0017 …`
4. **Glassbox**: `/solicitudes` → *Open (1)*; the page: *Open*, *Opened by the Yunt*; strip Request ✓ · **Quotations 0 of 2 required (over $500,000)** ringed · Order grey; thread = ask, proposal, approval, confirmation.

*Next:* send a quotation by email → it records it; above $500,000 it must ask for a
second (`quotation_required`) *(not run — 👀)*; with two, it proposes the order.

### 2b. Request from the dashboard, order by email *(hybrid)*
1. **Dashboard** `/levantamiento`: the request `SOL-2026-0019` ("G93", 20 L, Fundo Raices, budget $12.976). The page said "opened by hand: there are no emails".
2. **Email** `Quotation for SOL-2026-0019` — "I got a quotation from PROVEEDOR PRUEBA SPA … CLP 650 per liter, total net CLP 13,000. Delivery date: tomorrow. Please record this quotation and prepare the purchase order …"
3. **Yunt** (old build): "necesito el identificador interno exacto" — **a real bug**: it could not find a request from its number, and a person never has the id. I pasted the id once **only to finish the run** (that is not a valid test of the real flow).
4. **Fix**, shipped in `f15d52a`: `find_purchase_request` (by `SOL-…` number, or the open list).
5. **Proved on the deployment** with a fresh dashboard request `SOL-2026-0020` (10 L, $50.000) and an email quoting **only the number**: the Yunt found it and proposed `Emitir una orden de compra a PROVEEDOR PRUEBA SPA. 10 L a CLP 4800 por L. Total CLP 48000.` It wrote `Fecha de entrega: no indicada` although I said "tomorrow" (other runs resolved it) — watch for that. I did not approve this one.
6. **Glassbox for `SOL-2026-0019`** after I approved: request left `/solicitudes` ("No open requests"), appeared on `/ordenes` as `OC-2026-0012`; its page: *Order generated*, strip all ✓, `1 uploaded · two not required`, order card with **Ver / guardar PDF**, and the thread now showed all 8 messages **including the failed first attempt**.

### 2c. The 16 Sep case, read on the page *(existing thread, since removed)*
`SOL-2026-0016` / `OC-2026-0011`: 12 messages from "I need 10L of Petroleo Diesal
Super" to the issued order. I first showed only 8 (the page began at the third
message); you spotted it and I fixed it to follow replies **upward as well as
downward**. That is why the strip and thread now start at the first message.

---

## 3. Reports

### 3a. PDF and spreadsheet *(seeded, not emailed)*
Preview did not have the report store when I tested, so I wrote two reports through
the **real query and store code** (Jan–Mar 2026 purchases by category) against live
data, then deleted them. `/informes` listed both; each page showed the thread, the
question as criteria (Dirección: Compras · Período · Agrupado por: categoría · Notas
de crédito: excluidas), the fetched rows as a table (`EXP-6.4 Guano $149.074.200 · 1
línea` …, "Lista recortada: no es el conjunto completo"), and a document section.
The PDF button returned a valid PDF (`%PDF-`, 6.9 KB); an unknown id returned 404.
The spreadsheet variant first showed raw numbers (`214523465`); fixed to `$214.523.465`.
**A real emailed report has not been run since the store went live.** 👀

---

## 4. Recreate it yourself

Package: `handover/glassbox-test/`

| File | Use |
|---|---|
| `A-EMAIL-flow-3-unseen-july-invoices.zip` | **email** flow — 3 real July purchase invoices, 3 lines: Cooperativa Agrícola y Lechera (*GASOLINA 93*), Multimotos Osorno (*REPARACION MOTO HONDA*), Importadora Somagel (*DECALCIFICANTE*) |
| `B-DASHBOARD-flow-3-unseen-july-invoices.zip` | **dashboard** flow — Cumbre Consultores (2 lines: *Cobertura fotográfica*, *Diseño de PPT*), Verisure (*MONITOREO … CONTRATO*), Santander (*COMISION DE MANTENCION DE PLAN*), 4 lines |
| `exact-replay-fake-supplier/S1-…zip`, `S2-…zip` | the fake-supplier documents I used, if you want to see exactly what I saw (S1 = 4 clean lines; S2 = one arithmetic error, one junk name, one suggestion) |

All six July invoices are **not in the database** (checked by RUT + type + folio) and
none is from August. **Sending is safe; approving is what writes.** To see every
state without spending them, **reject** at the end. If you do approve one, undo it
with the script below.

**Job by email (1a/1b):** attach **A** to a new message to the Yunt (drag it onto the
body; if Outlook offers OneDrive choose "attach as a copy" — a link is not read).
Watch `/carga`. Reply `SÍ, ADELANTE` or `No, descarta esto`.
**Job by dashboard (1c):** on the **deployment** `/carga`, choose **B** → Review →
approve or reject on the page.
**Failed (1e) / Yunt-down (1d):** local server only (see above).
**Purchase (2a/2b):** copy my texts; for the hybrid, create the request on
`/levantamiento` and email a quotation naming only its `SOL-…` number.
**Reports (3):** email `Send me a PDF report of purchases from January to March 2026
grouped by category, with a bar chart.` (Jan–Mar has data; July does not.)
Approving text is always the first line `SÍ, ADELANTE` (`YES, GO AHEAD` also worked).

**Cleaning up after any run** — dry run first, it prints exactly what it will delete:
```bash
# note the UTC time before you start:  date -u +%Y-%m-%dT%H:%M:%SZ
.venv-backend/bin/python scripts/91_glassbox_test_cleanup.py \
  --since 2026-09-21T09:00:00Z \
  --zip handover/glassbox-test/A-EMAIL-flow-3-unseen-july-invoices.zip,handover/glassbox-test/B-DASHBOARD-flow-3-unseen-july-invoices.zip \
  --requests SOL-2026-0001            # any requests you created; omit if none
# then add --apply
```
It deletes, from `--since` on, the jobs, emails, refusals and stored reports; the
invoices in the zips you name (and only those) with their lines; and the requests
you list with their quotations, drafts and order. Do **not** use
`scripts/90_yunt_live_test_undo.py --apply`: it deletes every Yunt-created purchase
request with no way to choose.

**Left on live, untouched:** three old *Discarded* jobs from 19 Sep (two uploads, one
email) and their 2 email rows, and one 16 Sep report-request row. They show in the
history as *Discarded*. Say if you want them gone too.

## 5. Not run — 👀 for you
Change-request replies (J2/P3) · a second quotation and the two-quotation refusal ·
upload approval on the deployment · **approving an emailed job from its page (D-111, migration `042`): dialog, Cancel, stale-proposal refusal, then "Sí, guardar"** · a real emailed report landing in `/informes` ·
the "same files again" email answer · an unreadable attachment · a report for a
period with no data.
