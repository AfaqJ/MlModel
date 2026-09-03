# Frontend fix ledger — decisions from Afaq

One row per issue found in the 2026-08-27 audit. Nothing is implemented until
the Decision column is filled in by Afaq. Status: `ASKED` / `DECIDED` / `DONE`.

> **STANDING RULE (Afaq, 2026-08-27).** Confirm something is genuinely useless or a
> duplicate *before* acting on it. Never delete — **comment out**, so it can be restored.
> Log every removal somewhere it can be reported to the supervisor.

Fixes land in `/Users/afaq/Desktop/Mctech/milk-company`.

**UI names, not routes:** `Catálogo de Ítems` = /productos · `Analítica` = /dashboard · `Extractor XML` = /extractor
Audit: `AUDIT.md` + https://claude.ai/code/artifact/c63313ec-389e-4bf8-bf23-18e53bad19dc

---

## A. One-line fixes

| # | Issue | File | Status | Decision |
|---|---|---|---|---|
| A1 | Fetch failure renders as zeros; error card unreachable | `dashboard-view.tsx:132-154` | DECIDED | **Fix as proposed.** Delete `setLinesReady(true)` from the `catch`; error card renders. |
| A2 | `??` blocks description fallback; blank on all 4,029 products | `historial/page.tsx:41` | DECIDED | **Drop the header-level description entirely.** A description belongs to the *item occurrence*, not the canonical header. Each history row shows its own `invoice_items.description` exactly as stored. Do NOT pick a 'latest' one to represent the header. |

## B. Review gate — presentation per surface
Root fix is one `resolveCategory` function. Each row below is how that surface
should *look* once it can tell confirmed from pending.

| # | Surface | File | Status | Decision |
|---|---|---|---|---|
| B1 | Categories tab — KPI cards, amount/share/lines | `tabs/categories-tab.tsx`, `analytics/aggregate.ts:206-258` | DECIDED | **(a)** List **every** category from the `categories` table, including zero-money ones. **(b)** Remove click-to-isolate on the cards — adds nothing. **(c)** Cards report **confirmed revenue only**. **(d)** Pending money moves to the **top KPI tile row** (beside Total Volume / Sales) as an 'awaiting review' tile; hover shows spread across guessed categories. **(e)** If the tile row overflows, scroll it horizontally. |
| B2 | **Analítica → Ítems** — category column per product | `tabs/items-tab.tsx:62-79,192-197` | DECIDED | **KEEP the tab and fix it** *(reversed an earlier "remove" after checking)*. Verified **not** a duplicate: it is the only place showing **total spend per item**, plus item codes and meter-tracked count, and the only one that respects the date filter. Category column follows the review gate — confirmed category, or **En revisión** with the guess in a separate suggestion column. Mixed units get the C1 hover treatment. |
| B3 | **Explorador** — invoice detail + per-line category | `tabs/explorer-tab.tsx:120-300` | DECIDED | **Make the invoice expand inline (dropdown), like Catálogo de Ítems.** Today the detail renders in a card *below* the table, so clicking the `>` looks like nothing happened. Inside it list every line with its category; lines awaiting review say **"Need review"**. This view is per-invoice, not per-category. |
| B4 | **Concentración** — category Pareto / HHI | `ai-engine.ts:433-474` | DECIDED | **Confirmed only in the chart.** Add a separate "revenue in pending" tile showing the concentration of pending money. **Do not put pending into the graph** — it would swamp genuinely small categories. |
| B5a | Category filter on **Catálogo de Ítems** | `productos/items-view.tsx:59,76` | DECIDED | **Both, pending marked.** A client told "your review rows sit in category X" must be able to filter to X and find them. |
| B5b | Category filter on **Analítica** | `analytics/filters.ts:75-90` | DECIDED | **Confirmed only.** Pending money is reported separately in the top tile — counting it in the KPIs too would double-count and the arithmetic would stop adding up. |
| B6 | **Catálogo de Ítems** — category column + category-count badge | `productos/columns.tsx:49-69`, `items/group.ts` | DECIDED | Keep the existing badge + 'seen in N other categories'. **Add:** hovering the category reveals all applicable categories for that catalog item, pending ones marked. |
| B7 | **Historial** — category column + KPI | `historial/columns.tsx:97-110,148-168` | DECIDED | **Leave as is.** Verified: a separate `status` column already shows a "needs review" badge per row, so the state is disclosed. KPI stays unchanged — not worth complicating. |
| B8 | New "pendiente de revisión" tile — CLP 949,052,038 / 9.3% | new | DECIDED | Same as B1(d) — top KPI row, hover reveals spread by guessed category. Not a Categories-tab element. |

## C. Wrong numbers

| # | Issue | File | Status | Decision |
|---|---|---|---|---|
| C1 | Mixed-unit quantity sum + avg unit price (KG+L+UN added) | `tabs/items-tab.tsx:82-108,202-215` | DECIDED | **Quantity:** show the single unit normally. For mixed units show a compact card; hover reveals the full breakdown (`40 KG`, `10 UN`, …). **Price:** never one blended average — show avg per unit type separately (avg/KG, avg/UN), again as a compact card with the detailed math on hover. Keep the dashboard uncluttered; detail lives in the hover. |
| C2 | **Catálogo de Ítems** — bare `$` with decimals | `productos/columns.tsx:12-23`, `items-view.tsx:39-50`, `historial/columns.tsx:10-21` | DECIDED | **(a)** Use the existing zero-decimal CLP formatter everywhere. |

## D. Misleading labels

| # | Issue | File | Status | Decision |
|---|---|---|---|---|
| D1 | "Contrapartes / N ítems distintos" tile | `kpi-cards.tsx:66-71` | DECIDED | **Leave as is.** Afaq read it in context: the tile sits directly under the date filter, so its period-scoping is obvious to the user. No rename needed. |
| D2 | **Analítica → Ítems** KPI row label | `tabs/items-tab.tsx:138-163` | DECIDED | **Leave as is — follows the D1 precedent.** The KPI row sits under the same visible global date filter, so its period-scoping is as obvious here as on the Contrapartes tile. |
| D3 | **Concentración** — reframe dimensions as COMPRAS / VENTAS | `ai-engine.ts:403-474,729-749`, `tabs/concentration-tab.tsx:34` | DECIDED | **(a) Two separate stacked charts**, each with its own scale and line count — COMPRAS = who we bought from, VENTAS = who we sold to. Antillanca excluded **by RUT** (name has 6 spellings). Rationale from Afaq: nowhere else in the app says who we mostly paid and who we mostly sold to. Keep everything git-tracked so it can be reverted. |
| D4 | Payment-form totals mix payables and receivables | `ai-engine.ts:529-598` | DECIDED | **Render the verified meanings:** `1`=**Contado**, `2`=**Crédito**, null=**No especificado**. Keep the direction split; never add payables to receivables. |
| D5 | Overdue % — no paid flag exists, and directions are mixed | `ai-engine.ts:543-608` | DECIDED | **Comment out the overdue/aging chart.** With no paid flag nothing can be called overdue. → Q1 for the colleague. |
| D6 | HHI threshold labels borrowed from antitrust law | `tabs/concentration-tab.tsx:34-41` | DECIDED | **DEFERRED** — Afaq wants to understand it properly first. Park; revisit later. Nothing changes meanwhile. |
| D7 | **Concentración** — trading-relationship table capped at 25 | `tabs/concentration-tab.tsx:172-223` | DECIDED | **Show all rows, searchable by seller and by buyer** so a specific trading relationship can be looked up. |
| D8 | **Geografía** — city click filters either side | `analytics/filters.ts:47-67` | DECIDED | **(a)** Make the filter direction-aware so the drill-down matches the bar. |
| D9 | Category totals sum *whole invoices*, not matching lines | `analytics/filters.ts:119-152` | DECIDED | **Item-level, not invoice-level.** A figure labelled for a category contains only that category's lines, never whole invoices that merely include one. |
| D10 | Internal `prediction_source` tags exposed to the client | `analytics/global-filters.tsx:29` | **CORRECTED 2026-08-27** | **The audit finding was wrong.** Checked against `origin/feature/dashboard`: `predictionSources` existed only as an unused *type field*, never as a rendered control. No internal tag was ever reaching a client through it. Nothing was disabled; an accurate note replaces the finding. The rule still stands (R6) - the client sees only confirmed vs awaiting review. |

## E. Performance

| # | Issue | File | Status | Decision |
|---|---|---|---|---|
| E1 | **Catálogo de Ítems** — full 11,746-line scan → `item_summary` view | `items/queries.ts:201-246` | DECIDED | **(a)** Do it, but **after** the review-gate fix, so the corrected rule goes into the SQL. Claude writes the `create view`; Afaq runs it in the Supabase editor. |

## F. Security

| # | Issue | File | Status | Decision |
|---|---|---|---|---|
| F1 | Roles not enforced server-side | `middleware.ts:35-58` | DECIDED | **(c) Leave it** — single trusted user for now, not worth it yet. Revisit before any wider rollout. |
| F2 | RLS verification in production | Supabase | DECIDED | **(b) Skip** — Afaq confirms it is configured. |

## G. Dead code and stubs

| # | Issue | File | Status | Decision |
|---|---|---|---|---|
| G1 | `src/components/dashboard/**` + `src/lib/dashboard/**` orphaned (40 files) | — | DECIDED | **Do NOT delete.** Already unreferenced, so nothing to comment out — leave the files in place and record them as dead in the repo docs. Revisit only if confirmed redundant later. |
| G2 | `project/` Vite prototype with mock data | — | DECIDED | **Do NOT delete.** Already excluded from the build. Leave in place, record as dead. |
| G3 | 9 stub routes URL-reachable, showing invented numbers | `app/[locale]/*` | DECIDED | **(c) Keep reachable, add a visible "demo / no funcional" banner** on each. |

## H. Smaller

| # | Issue | File | Status | Decision |
|---|---|---|---|---|
| H1 | `PredictionSource` type declares 3 values; live has 8 | `analytics/types.ts:11-12` | DECIDED | **Fix the type — internal correctness only**, no user-facing effect once D10 lands. |
| H2 | Table chrome hardcoded English | `ui/data-table-pagination.tsx:26-94`, `ui/data-table.tsx:93-112` | DECIDED | **(a) Translate the interface only.** Never translate content coming from the database — item names, descriptions, company names render exactly as stored. |
| H3 | **Duplicate history button** — one in row actions, one in row expansion | `productos/columns.tsx:175`, `items-view.tsx:251` | DECIDED | **Keep one.** Found by Afaq, not by the audit. |


---

## Open questions for the colleague / client

| # | Question | Why it matters |
|---|---|---|
| Q1 | **Is payment status (paid / unpaid / paid-on date) available anywhere?** It is in none of the five live tables. | Without it nothing can be called "overdue" — the aging chart is unprovable and is being commented out (D5). If a feed exists, the chart comes back. |

## Verified while deciding — what `payment_form` means

Document types are SII codes (33 Factura, 61 Nota de Crédito, 34 Exenta, 43 Liquidación,
56 Nota de Débito), so this follows the SII DTE schema, where `FmaPago` is 1=Contado,
2=Crédito. Tested on 5,195 live invoices via the gap between `invoice_date` and `due_date`:

| value | n | median gap | due same day | reading |
|---|---:|---:|---:|---|
| `1` | 1,968 | **0 days** | 93% | **Contado** — settled on issue |
| `2` | 2,482 | **21 days** | 35% | **Crédito** — real terms |
| null | 745 | 9 days | 43% | unknown — render "No especificado" |

Schema intent and observed behaviour agree, so it is safe to display as real labels
(`docs/EVIDENCE_RULES.md` §1).


---

## Verified while deciding — direction of trade

Measured on 5,195 live invoices. **Afaq's guess was inverted**, so this is recorded
explicitly to stop it recurring:

| | Antillanca's side | counterparty is | invoices | money |
|---|---|---|---:|---:|
| **COMPRAS** | **BUYER** (88%) | the **supplier** we bought from | 5,107 | CLP 5,784,554,917 |
| **VENTAS** | **SELLER** (100%) | the **customer** we sold to | 88 | CLP 6,278,389,520 |

Two consequences for the D3 redesign:

1. **VENTAS is 88 invoices — 1.7% of documents but 52% of the money.** The two sides are
   wildly asymmetric (few enormous milk deliveries vs thousands of small purchases). The UI
   must not present them as comparable magnitudes.
2. **"Antillanca" is spelled at least 6 ways** in `buyer_name` — `ANTILLANCA SPA`,
   `ANTILLANCA S A`, `ANTILLANCA SPA.`, `Antillanca Spa`, `ANTILLANCA SpA`, `Antillanca SPA`.
   Any "exclude our own company" logic **must match on RUT, never on name**.

## D7b — city dimension: checked, and it is NOT a duplicate

| | Geografía tab | Concentración → `city` |
|---|---|---|
| Total / sales / purchases per city | ✓ | ✗ |
| Invoice count, counterparty count | ✓ | ✗ |
| Distribution + direction-split charts | ✓ | ✗ |
| **HHI** | ✗ | **✓** |
| **Pareto count** ("N cities cover 80%") | ✗ | **✓** |
| **Top share %** | ✗ | **✓** |
| **Pareto curve** | ✗ | **✓** |

Different questions: Geografía answers *"how much per city, by direction"*; Concentración
answers *"is spend concentrated in a few cities"*.

**DECIDED:** it qualifies as Afaq's "small addition" case — `analyzePareto(..., "city", ...)`
already exists and already supports the city dimension, so this is a rendering move, not new
logic. **Move the 4 concentration tiles + Pareto curve into the Geografía tab, then comment
out `city` from the Concentración dimension list.** The deferred D6 (HHI threshold labels)
travels with it.

## Cross-cutting decisions

**GF1 — Global filter scoping.** *(Afaq, 2026-08-27)*
A global filter is **ignored on any tab whose own purpose is to break down by that same
dimension** — and when ignored, the tab must **say so visibly** ("filtro de empresa no
aplica aquí"), never silently do nothing.

| Filter | Concentración | Geografía | Categorías | Ítems | Explorador |
|---|---|---|---|---|---|
| Date | applies | applies | applies | applies | applies |
| Category | applies | applies | applies | applies | applies |
| Transaction type | ignored (tab splits it) | applies | applies | applies | applies |
| Company | ignored (tab is about spread) | applies | applies | applies | applies |
| City | ignored if city stays | ignored (tab is cities) | applies | applies | applies |

**GF2 — Git discipline.** *(Afaq, 2026-08-27)*
Everything stays git-tracked and revertible. Work on a branch; commit before each
group of changes so any step can be undone independently.

## Reversals — decisions changed after checking

| # | First logged | Changed to | Why |
|---|---|---|---|
| B2 | Comment out the Ítems tab as a duplicate | **Keep and fix it** | Afaq's standing rule forced a check before acting. It is not a duplicate: total spend per item, item codes, meter-tracked count and date-filter awareness exist nowhere else. Catálogo de Ítems shows only the *last* price, so "how much did we spend on X this year" would have lost its only home. |
| G1, G2 | Delete | **Leave in place, record as dead** | Never delete; comment out instead. Both are already unreferenced, so there is nothing to comment out. |

## Also found while verifying

- **`payment_form` is rendered raw to the client** in the Explorador detail header
  (`explorer-tab.tsx:201`) — it prints `1` or `2`. Second site for the D4 fix.
- **Concentración offers 5 dimensions**: `seller`, `buyer`, `category`, `city`, `item`.
  `city` duplicates the Geografía tab; `item` duplicates Catálogo de Ítems.
