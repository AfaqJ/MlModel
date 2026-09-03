# Frontend correctness audit — 2026-08-27

**Scope.** Static, read-only audit of `milk-company` on `feature/catalog-name-standardisation`; no Supabase connection, build, package install, or source edit was performed. The live-data baseline used by this audit is corroborated by `ML-model/CLAUDE.md:6-14,38-46` and the post-P-01 catalog count by `ML-model/docs/STATE.md:76-84`.

## Decisions this audit leaned on

- **The review gate is the hard limit, not D-001.** A prediction is never a final business classification when `decision='review_required'`; the incident and the distinction from its root cause are stated in `ML-model/CLAUDE.md:52-61`. D-001 explains how an input-blind dedup key collapsed 47 distinct training texts; it is the incident's root cause, not the UI rule (`ML-model/docs/DECISIONS.md:18-40`).
- **D-040:** consistent client filing outranks the model, so a UI must not silently promote a conflicting model prediction (`ML-model/docs/DECISIONS.md:850-875`).
- **D-042:** `client_evidence_backfill` is not client provenance: none of its 612 rows has highest-trust client backing, and `prediction_source` must not be presented as authority (`ML-model/docs/DECISIONS.md:924-949`).
- **D-044:** one real product or recurring service has one canonical catalog ID; spelling/spec/month variants do not create a new product (`ML-model/docs/DECISIONS.md:993-1010`).
- **D-045:** the canonical migration was deliberately paged/idempotent and ended with 4,029 catalog rows before P-01 (`ML-model/docs/DECISIONS.md:1016-1049`); P-01 then reduced live `item_catalog` to 4,002 (`ML-model/docs/STATE.md:76-84`).
- **D-043:** this section records the decisions before the report acts on them; the exception is appropriate because the audit is read-only and writes only this report (`ML-model/CLAUDE.md:68-70`).

## Ranked findings

1. **Wrong client numbers:** the analytics "Item Catalog" is actually distinct catalog IDs observed in the default 12-month invoice window, mixed-unit quantities and prices are added together, payment aging mixes receivables with payables, and a failed line fetch is converted into a successful empty dataset (`milk-company/src/components/analytics/tabs/items-tab.tsx:62-144,161-215`; `milk-company/src/lib/analytics/ai-engine.ts:529-608`; `milk-company/src/app/[locale]/dashboard/dashboard-view.tsx:132-154,391-455`).
2. **Hard-rule violation:** two shared fallbacks promote predictions without checking `decision`; they feed live product tables, category KPIs, charts, filters and explorer rows (`milk-company/src/lib/items/queries.ts:153-180`; `milk-company/src/lib/analytics/types.ts:133-144`). This is the exact known defect recorded as still untouched in `ML-model/docs/STATE.md:102-103`.
3. **Performance:** `/productos` performs a full, wide, 11,746-line joined scan in 1,000-row pages, serializes it into a client component, then groups it into catalog rows in the browser (`milk-company/src/lib/items/queries.ts:94-130,201-246`; `milk-company/src/app/[locale]/productos/page.tsx:24-50`; `milk-company/src/app/[locale]/productos/items-view.tsx:1-3,74-93`).
4. **Dead code / polish:** `src/components/dashboard/**` is not mounted by the live route, `project/` is an excluded Vite mock, nine workflow routes are static stubs, and shared table chrome renders English in Spanish (`milk-company/src/app/[locale]/dashboard/dashboard-view.tsx:21-36,266-276`; `milk-company/tsconfig.json:21-38`; `milk-company/src/components/ui/data-table-pagination.tsx:26-94`).

---

## 1. Review-gate violation

### Confirmed break

Both live data models contain the same unsafe rule:

- `/productos`: `final_category ?? predicted_category` is chosen without inspecting `row.decision`, then copied into `categoryId`, `categoryCode`, and `categoryName` (`milk-company/src/lib/items/queries.ts:153-180`).
- analytics: `effectiveCategoryId` and `effectiveCategoryCode` return final-or-predicted without inspecting `item.decision` (`milk-company/src/lib/analytics/types.ts:133-144`).

For `auto_accept`, a predicted category may be used as the accepted result. For `review_required`, only a reviewed human final value may occupy a final-category field; otherwise the final field must be **Pending review / Unclassified**. A model code/name may still appear in a separately labelled **Model suggestion** field, but pending rows must be excluded from classified-category totals/shares or placed in an explicit pending-review bucket (`ML-model/CLAUDE.md:52-56`).

### Every affected consumer in `src`

| Surface | Evidence | What it does now | What it must do |
|---|---|---|---|
| Product category filter | `milk-company/src/app/[locale]/productos/items-view.tsx:74-82` | Filters on the unsafe mapped `categoryId`, so pending predictions behave like business classifications. | Pending rows must not match a final-category filter unless they have a reviewed final category; optionally offer a separate prediction filter. |
| Product grouping and category-count badge | `milk-company/src/lib/items/group.ts:7-38`; `milk-company/src/app/[locale]/productos/columns.tsx:49-69` | Groups by catalog ID, counts unsafe categories, and renders the latest unsafe category as final. | Count/render reviewed final or auto-accepted categories; show pending status separately. |
| Product per-company expansion | `milk-company/src/app/[locale]/productos/items-view.tsx:257-300` | Renders unsafe code/name for the latest occurrence per company. | Render Pending review, with a separately labelled suggestion if useful. |
| Product history category KPI and table | `milk-company/src/app/[locale]/productos/[id]/historial/historial-view.tsx:46-52`; `milk-company/src/app/[locale]/productos/[id]/historial/columns.tsx:97-110` | Counts and displays predicted categories as established history. | Do not count a pending prediction as a historical classification; display pending and optional suggestion separately. |
| Orphaned dashboard line table | `milk-company/src/app/[locale]/dashboard/columns.tsx:58-70` | Renders the unsafe mapped category as final. | Same gate; this file is currently dead but unsafe if reconnected. |
| Analytics category filter | `milk-company/src/lib/analytics/filters.ts:75-90`; `milk-company/src/components/analytics/active-filters.tsx:64-70` | A category filter attributes pending lines to their predictions and then presents the selected category as an active business filter. | Match only accepted/final classifications; prediction filtering must be explicit. |
| Live Categories cards/KPIs/tooltips | `milk-company/src/lib/analytics/aggregate.ts:206-258`; `milk-company/src/components/analytics/tabs/categories-tab.tsx:19-67` | Aggregates amount, share, line count and distinct item count into predicted categories; code/name and exact-amount title are rendered as classified spend. | Exclude/bucket pending-review rows; denominators must state whether pending spend is excluded. |
| Live Items table | `milk-company/src/components/analytics/tabs/items-tab.tsx:62-79,99-123,177-197` | Takes the first occurrence's unsafe effective category and renders one category for the whole catalog item. | Derive only accepted/final categories and represent multi-category history; do not choose the first prediction. |
| Live invoice explorer | `milk-company/src/components/analytics/tabs/explorer-tab.tsx:240-278` | Resolves `effectiveCategoryId`, then falls back to `predicted_name`; a nearby comment explicitly hides review state from the client (`milk-company/src/components/analytics/tabs/explorer-tab.tsx:299-300`). | Show final/accepted category or Pending review; if prediction is shown, label it as a suggestion and show review state. |
| Live category concentration/Pareto/HHI | `milk-company/src/lib/analytics/ai-engine.ts:433-474`; `milk-company/src/components/analytics/tabs/concentration-tab.tsx:54-168` | Assigns pending amounts to predicted categories and charts their amount, cumulative share, entity count, top share, Pareto count and HHI. | Pending amounts need their own bucket or exclusion from category concentration, with denominator disclosure. |
| Legacy spend-by-category chart and tooltip | `milk-company/src/lib/dashboard/aggregate.ts:149-193`; `milk-company/src/components/dashboard/spend-by-category-chart.tsx:34-44,51-94` | Aggregates/render/tooltips the already unsafe mapped category. | Apply the gate before aggregation. The component is presently orphaned, not live. |
| Legacy category-company matrix and tooltip | `milk-company/src/lib/dashboard/entities.ts:403-457`; `milk-company/src/components/dashboard/category-company-matrix.tsx:39-70,93-129` | Cross-tabulates pending predictions by category and company. | Gate before matrix construction; keep pending explicit. Component is orphaned. |
| Legacy data-quality ambiguity table | `milk-company/src/components/dashboard/tabs/data-quality-tab.tsx:43-50`; `milk-company/src/lib/dashboard/aggregate.ts:543-552` | Renders unsafe mapped category on unreviewed rows. | Label the value as model suggestion, not category. Component is orphaned. |
| Legacy drill filters and labels | `milk-company/src/lib/dashboard/drill.ts:28-48,61-75`; `milk-company/src/components/dashboard/tabs/explorer-tab.tsx:75-81` | Drills and labels by unsafe `categoryId/categoryName`. | Pending predictions cannot define the business-category drill. Components are orphaned. |
| Legacy category profiles | `milk-company/src/lib/dashboard/entities.ts:229-302`; `milk-company/src/components/dashboard/explorer/category-columns.tsx:25-39`; `milk-company/src/components/dashboard/explorer/entity-header.tsx:53-63` | Computes category spend/share/counts and renders names/codes from unsafe fields. | Gate before profiling; use pending bucket. Components are orphaned. |
| Legacy item profiles | `milk-company/src/lib/dashboard/entities.ts:305-366`; `milk-company/src/components/dashboard/explorer/item-columns.tsx:25-38` | Stores the first occurrence's unsafe category as the item's category. | Do not promote a first prediction; represent accepted/final category set. Components are orphaned. |
| Legacy explorer category table/charts | `milk-company/src/components/dashboard/explorer/explorer-panel.tsx:145-162,197-257` | Uses unsafe category profiles and category charts throughout drill-down. | Gate centrally before every derived profile/chart. Components are orphaned. |

### Checked and not violations

- The disabled Model review queue filters to `needs_review` and labels the column **Predicted**, so it uses the prediction as a review hint rather than a final classification (`milk-company/src/lib/analytics/aggregate.ts:353-368`; `milk-company/src/components/analytics/tabs/model-tab.tsx:160-175,206-229`).
- The disabled Risk ambiguity description calls the value `predicted`; it is a diagnostic hint, not a final category (`milk-company/src/components/analytics/tabs/risk-tab.tsx:82-87`).
- There is no category CSV/Excel export in the dashboard or product code. The only live Excel exporter receives user-uploaded XML parse rows and writes them unchanged (`milk-company/src/app/[locale]/extractor/page.tsx:100-109`; `milk-company/src/lib/extractor/excel-export.ts:19-73`). Therefore there is no current review-gate export leak to list.

---

## 2. Why the item catalog page is slow

### Confirmed root cause

The page is a full-table line-history scan masquerading as a paginated catalog browser:

1. The server component starts `fetchItemOccurrences` alongside categories, companies and a count query (`milk-company/src/app/[locale]/productos/page.tsx:24-38`).
2. `fetchItemOccurrences` requests **all** `invoice_items` in explicit 1,000-row ranges until a short page appears (`milk-company/src/lib/items/queries.ts:4-14,212-246`). At the 11,746-line baseline this is **12 sequential data round-trips**, plus the count query and the parallel category/company requests (`milk-company/src/lib/items/queries.ts:218-237,414-430`).
3. Each line carries catalog, predicted and final category joins plus invoice and company fields (`milk-company/src/lib/items/queries.ts:94-130`). The page does not render invoice net, IVA, exempt, total, due date, payment form, tax flag, score, margin, entropy, prediction source, discount or recargo in the catalog table, although those fields are transferred and mapped (`milk-company/src/lib/items/queries.ts:81-87,103-123,181-196`; `milk-company/src/app/[locale]/productos/columns.tsx:28-130`).
4. The complete line array is serialized from the server component into a client component (`milk-company/src/app/[locale]/productos/page.tsx:44-50`; `milk-company/src/app/[locale]/productos/items-view.tsx:1-3`). The browser filters it, groups by catalog ID, sorts every group, and only then lets TanStack paginate the resulting rows (`milk-company/src/app/[locale]/productos/items-view.tsx:74-93,235-305`; `milk-company/src/lib/items/group.ts:7-38`; `milk-company/src/components/ui/data-table.tsx:64-87`).

This is not N+1: each 1,000-line page uses embedded PostgREST joins, not one query per catalog item (`milk-company/src/lib/items/queries.ts:114-130,218-225`). It is not `select('*')`: the selection is explicit, but materially wider than the page needs (`milk-company/src/lib/items/queries.ts:91-130`). It is not silent PostgREST truncation: `.range()` is present and loops (`milk-company/src/lib/items/queries.ts:218-237`). The expensive JavaScript grouping is also work the database can do once, rather than every navigation (`milk-company/src/lib/items/group.ts:7-38`).

No cache wrapper exists in the page or query path, and the Refresh button explicitly calls `router.refresh()`, causing the server scan again (`milk-company/src/app/[locale]/productos/page.tsx:24-50`; `milk-company/src/app/[locale]/productos/items-view.tsx:53-71`). The reasoned cost is 11,746 wide joined rows fetched and serialized to display roughly 4,002 catalog rows, with 12 serial page latencies before grouping; no live timing is claimed because connecting to Supabase was prohibited (`milk-company/src/lib/items/queries.ts:201-246`; `ML-model/docs/STATE.md:81-84`).

### Smallest correct fix

Page `item_catalog` directly with stable ordering and `.range()`; for only the visible catalog IDs, fetch a single batched occurrence summary/latest-row query. The better one-query form is a database view/RPC returning one row per canonical catalog ID with latest occurrence, company/category counts and review-safe category fields, already sorted and paginated. Either form changes the cost from 12 full-history requests plus browser grouping to one or two bounded requests per page and avoids N+1 (`milk-company/src/lib/analytics/queries.ts:129-135` already demonstrates correctly paged direct catalog selection; `milk-company/src/lib/items/group.ts:7-38` defines the aggregation that should move server-side).

---

## 3. Why analytics shows ~3,500 items while catalog shows ~4,000

### Exact query paths

- **Analytics:** the route fetches the entire canonical catalog in pages, but only uses it as a name lookup (`milk-company/src/app/[locale]/dashboard/page.tsx:64-76`; `milk-company/src/lib/analytics/queries.ts:66-98,129-135`). The visible count is instead `Map(catalog_item_id)` over invoice lines in the active filter, then `aggregates.length` (`milk-company/src/components/analytics/tabs/items-tab.tsx:62-123,138-163`). Those lines are fetched through an inner invoice join constrained to the default 12-month range (`milk-company/src/app/[locale]/dashboard/page.tsx:25-44`; `milk-company/src/lib/analytics/queries.ts:156-192`).
- **Catalog page:** it fetches every historical invoice line, then returns one group per referenced `catalog_item_id` (`milk-company/src/lib/items/queries.ts:212-246`; `milk-company/src/lib/items/group.ts:7-38`). It does **not** actually count `item_catalog`; therefore a zero-history catalog row would be absent even there.

### Causes checked

| Candidate | Finding | Evidence |
|---|---|---|
| PostgREST 1,000/max-rows cap | Not the cause. Both paths repeatedly call `.range()` in 1,000-row pages. | `milk-company/src/lib/analytics/queries.ts:20-26,66-98,171-192`; `milk-company/src/lib/items/queries.ts:4-14,218-237` |
| Hard-coded `.limit()` / `.range()` ceiling | Not the cause. The analytics table display is sliced to 100, but its summary is calculated before that slice; fetch safety limits are 200,000/100,000. | `milk-company/src/components/analytics/tabs/items-tab.tsx:125-144`; `milk-company/src/lib/analytics/queries.ts:20-26`; `milk-company/src/lib/items/queries.ts:7-14` |
| Different filters | **Actual cause.** Analytics defaults to the latest 12 months and all other filters further narrow its line set; `/productos` scans all history. | `milk-company/src/app/[locale]/dashboard/page.tsx:25-44`; `milk-company/src/lib/analytics/filters.ts:28-38,128-152`; `milk-company/src/lib/items/queries.ts:201-246` |
| Name deduplication | Not the cause. Both group by `catalog_item_id`, not item name. | `milk-company/src/components/analytics/tabs/items-tab.tsx:62-80`; `milk-company/src/lib/items/group.ts:7-20` |
| Inner join drops rows with no lines in range | **Yes; this is how the date filter takes effect.** Analytics starts from `invoice_items` and inner-joins date-matching invoices rather than seeding from catalog. | `milk-company/src/lib/analytics/queries.ts:156-192` |
| Active/deleted or transaction/review filter mismatch | No such default filter. Transaction and review default to `ALL`; no active/deleted predicate exists in either query. | `milk-company/src/lib/analytics/filters.ts:28-38`; `milk-company/src/lib/analytics/queries.ts:171-190`; `milk-company/src/lib/items/queries.ts:218-225` |

The canonical catalog total should be **4,002** on both surfaces whenever the label means “catalog” (`ML-model/docs/STATE.md:81-84`; D-044 defines the ID semantics at `ML-model/docs/DECISIONS.md:993-1010`). If analytics intentionally retains its current formula, its value should remain the distinct catalog IDs with invoice lines in the selected range—approximately the observed 3,500—but the tile and section must be renamed **Active items in current filters**, not **Distinct Items / Item Catalog** (`milk-company/src/components/analytics/tabs/items-tab.tsx:138-163`; Spanish labels at `milk-company/messages/es.json:1074-1082`). The `/productos` count should come from direct `item_catalog` paging, not be inferred from historical lines (`milk-company/src/lib/analytics/queries.ts:129-135`).

---

## 4. Every metric on every dashboard — inventory

The live route mounts `src/components/analytics/**`; it does not import the legacy tab tree in `src/components/dashboard/**` (`milk-company/src/app/[locale]/dashboard/dashboard-view.tsx:21-36,266-276,355-455`). The legacy tree is still inventoried below because the brief requested it; its status is stated in the Why column.

| Metric | Where shown | Formula (file:line) | Verdict | Why |
|---|---|---|---|---|
| Filtered invoice/line badge | Live global filter bar | Array lengths: `milk-company/src/app/[locale]/dashboard/dashboard-view.tsx:301-306` | CORRECT | Honest current-filter row counts while loading succeeds. |
| Total volume | Live KPI | Sum `invoice.total_amount`: `milk-company/src/lib/analytics/aggregate.ts:76-94,112-128`; render: `milk-company/src/components/analytics/kpi-cards.tsx:28-33` | CORRECT | Invoice totals are summed once, and the Spanish label is “Volumen Total,” not revenue (`milk-company/messages/es.json:767`). |
| Sales and purchases totals | Live KPIs | Split summed invoice totals by `VENTAS/COMPRAS`: `milk-company/src/lib/analytics/aggregate.ts:85-92`; render: `milk-company/src/components/analytics/kpi-cards.tsx:35-49` | CORRECT | Direction split is arithmetically correct for the current invoice filter. |
| Invoice count and average invoice | Live KPIs/fiscal mini-stats | `count`; `Σ total/count`: `milk-company/src/lib/analytics/aggregate.ts:110-125`; renders: `milk-company/src/components/analytics/kpi-cards.tsx:51-63`, `milk-company/src/components/analytics/fiscal-breakdown.tsx:61-68` | CORRECT | Invoice-level arrays prevent line multiplication. |
| Counterparties; distinct-items hint | Live KPI | Distinct counterparty RUT and distinct line `catalog_item_id`: `milk-company/src/lib/analytics/aggregate.ts:83-107,124-125`; render: `milk-company/src/components/analytics/kpi-cards.tsx:66-71` | MISLEADING | Counterparties is correct; “distinct items” is active-in-filter items, not the 4,002-row catalog. |
| Net, IVA, exempt, total and shares | Live fiscal card | Invoice-level sums; each part/`Σtotal`: `milk-company/src/lib/analytics/aggregate.ts:76-94`; `milk-company/src/components/analytics/fiscal-breakdown.tsx:22-59` | CORRECT | It deliberately shows non-balancing source fields instead of normalizing them (`milk-company/src/components/analytics/fiscal-breakdown.tsx:10-16`). |
| Discounts and surcharges | Live fiscal card | Sum line discount/recargo: `milk-company/src/lib/analytics/aggregate.ts:96-107`; render: `milk-company/src/components/analytics/fiscal-breakdown.tsx:71-83` | CORRECT | Line-level values are summed after, not before, normalization. |
| Sales/purchases over time | Live Overview chart/tooltips | Invoice totals by month/direction: `milk-company/src/lib/analytics/aggregate.ts:131-156`; render: `milk-company/src/components/analytics/revenue-chart.tsx:38-107` | CORRECT | Same filtered invoice set and exact tooltip values. |
| Invoice and line volume over time | Live Overview chart/tooltips | Invoice count plus line count joined by invoice ID: `milk-company/src/lib/analytics/aggregate.ts:131-156`; render: `milk-company/src/components/analytics/revenue-chart.tsx:110-171` | CORRECT | No average-of-averages or dual money/count axis. |
| Top issuer/recipient totals, invoice count, average | Live Overview/Companies panels | Group invoice totals by side RUT, `Σ/count`, top 10: `milk-company/src/lib/analytics/aggregate.ts:167-203`; render/scope labels: `milk-company/src/components/analytics/counterparty-panel.tsx:18-90` | CORRECT | The panel changes labels for purchase, sale and all-direction scopes. |
| Concentration narrative insight | Live Overview insight | Seller Pareto count/top share: `milk-company/src/lib/analytics/ai-engine.ts:729-749`; caller fixes dimension to seller: `milk-company/src/app/[locale]/dashboard/dashboard-view.tsx:248-254` | MISLEADING | In `ALL`, seller includes Antillanca itself on sales, yet the narrative frames the result as counterparty concentration. |
| Critical anomaly insight | Live Overview insight | Count `severity==='critical'`: `milk-company/src/lib/analytics/ai-engine.ts:752-760` | CORRECT | It counts exactly what the anomaly detector emitted. |
| Sales-minus-purchases narrative | Live Overview insight | `abs(ΣVENTAS-ΣCOMPRAS)`: `milk-company/src/lib/analytics/ai-engine.ts:763-775` | CORRECT | Copy says directional net difference, not profit. |
| Category amount/share/lines/distinct items | Live Categories cards/tooltips | Unsafe effective category aggregation and share: `milk-company/src/lib/analytics/aggregate.ts:206-258`; `milk-company/src/components/analytics/tabs/categories-tab.tsx:19-67` | WRONG | Pending predictions are counted as final classified categories. |
| Distinct items, total lines, meter-tracked items | Live Items KPI row | Map size, input length, count with meter code: `milk-company/src/components/analytics/tabs/items-tab.tsx:62-144,149-159` | MISLEADING | Lines/meter count are correct for the filter; “distinct/catalog” is not total catalog. |
| Item spend and line count | Live Items table | `Σline.amount`; count: `milk-company/src/components/analytics/tabs/items-tab.tsx:82-84,99-123,199-216` | CORRECT | Correct within current filters. |
| Item category | Live Items table | First occurrence's unsafe effective category: `milk-company/src/components/analytics/tabs/items-tab.tsx:62-79,99-123,192-197` | WRONG | Violates review gate and collapses possible category variation to whichever line appeared first. |
| Item quantity and average unit price | Live Items table | Adds quantities across units; `Σamount/Σquantity`, then labels mixed units: `milk-company/src/components/analytics/tabs/items-tab.tsx:82-108,202-215` | WRONG | Adding KG, L and UN and dividing a combined amount by that sum has no business unit; a “mixed” badge does not repair the number. |
| Payment total and payment-form count/total/average/share | Live Payments | All filtered invoice totals grouped by payment form: `milk-company/src/lib/analytics/ai-engine.ts:529-598`; render: `milk-company/src/components/analytics/tabs/payments-tab.tsx:48-53,106-125` | MISLEADING | It mixes purchase payables and sales receivables because the caller passes all directions (`milk-company/src/app/[locale]/dashboard/dashboard-view.tsx:257-262`). |
| Overdue amount/count/percent and aging buckets | Live Payments | Past due date over all invoices; percent is overdue invoice count/all invoice count: `milk-company/src/lib/analytics/ai-engine.ts:543-608`; render: `milk-company/src/components/analytics/tabs/payments-tab.tsx:54-65,77-104` | MISLEADING | No paid/settled flag, and both receivables and payables are mixed; disclosure only covers the first limitation (`milk-company/messages/es.json:1168`). |
| Average payment terms | Live Payments | Mean `(due-issued)` for invoices with valid due dates: `milk-company/src/lib/analytics/ai-engine.ts:563-568,607` | CORRECT | Correctly excludes missing/invalid due dates and rounds only for display (`milk-company/src/components/analytics/tabs/payments-tab.tsx:66-74`). |
| Category Pareto, HHI, top share, entity/Pareto counts | Live Concentration, category mode | Category amount shares and HHI: `milk-company/src/lib/analytics/ai-engine.ts:433-474`; render: `milk-company/src/components/analytics/tabs/concentration-tab.tsx:92-168` | WRONG | Review-gate violation changes every category concentration number. |
| Seller/buyer/city/item Pareto, HHI, top share, counts | Live Concentration, other modes | Group, percentage, cumulative 80%, HHI: `milk-company/src/lib/analytics/ai-engine.ts:403-474` | MISLEADING | Arithmetic is correct, but antitrust thresholds are applied to one client's invoice shares, not market shares (`milk-company/src/components/analytics/tabs/concentration-tab.tsx:34-41`). |
| Seller→buyer network totals/counts | Live Concentration table | Group invoice totals by seller/buyer, sort, top 25: `milk-company/src/lib/analytics/ai-engine.ts:676-699`; caller: `milk-company/src/app/[locale]/dashboard/dashboard-view.tsx:263-264` | MISLEADING | Table renders the capped list without saying it is top 25 (`milk-company/src/components/analytics/tabs/concentration-tab.tsx:172-223`). |
| City total, sales, purchases, invoices, counterparties | Live Geography cards/chart/table | Attribute counterparty city by direction and aggregate: `milk-company/src/lib/analytics/ai-engine.ts:622-657`; render: `milk-company/src/components/analytics/tabs/geography-tab.tsx:37-150` | CORRECT | Metric attribution is direction-aware. The click-through filter is not: it matches either invoice side (`milk-company/src/lib/analytics/filters.ts:47-67`). |
| Invoice net/IVA/total and line count | Live Explorer | Direct invoice fields; associated line-array length: `milk-company/src/components/analytics/tabs/explorer-tab.tsx:45-57,120-159` | CORRECT | Invoice money is not multiplied by line count. |
| Explorer line category | Live Explorer detail | Unsafe effective category/fallback prediction: `milk-company/src/components/analytics/tabs/explorer-tab.tsx:240-278` | WRONG | Review-gate violation. |
| Explorer line quantity/unit price/discount/amount | Live Explorer detail | Direct normalized line fields: `milk-company/src/components/analytics/tabs/explorer-tab.tsx:279-297` | CORRECT | No derived cross-unit sum; CLP formatting is zero-decimal. |
| Model average confidence, reviewed count, correction rate, model version, confidence histogram | Disabled Model tab | `mean(score)`, reviewed count, corrected/reviewed, mode version, fixed bins: `milk-company/src/components/analytics/tabs/model-tab.tsx:56-115`; `milk-company/src/lib/analytics/aggregate.ts:317-345` | CORRECT | Correction rate is explicitly not claimed as full accuracy. Tab is not mounted (`milk-company/src/app/[locale]/dashboard/dashboard-view.tsx:266-276`). |
| Prediction-source counts/averages/auto rate | Disabled Model tab; orphaned legacy chart | Group by raw `prediction_source`: `milk-company/src/lib/analytics/aggregate.ts:261-301`; legacy: `milk-company/src/lib/dashboard/aggregate.ts:492-514` | MISLEADING | D-042 says raw provenance labels are not authoritative, especially `client_evidence_backfill` (`ML-model/docs/DECISIONS.md:928-949`). |
| Model review queue predictions/alternatives/confidence/margin/entropy | Disabled Model tab | `needs_review`, uncertainty sort, top 30: `milk-company/src/lib/analytics/aggregate.ts:353-368`; render: `milk-company/src/components/analytics/tabs/model-tab.tsx:160-243` | CORRECT | Explicitly a review queue and explicitly labels predictions as predictions. |
| Risk total/critical/warning/info and anomaly table | Disabled Risk tab | Counts detector output by severity: `milk-company/src/components/analytics/tabs/risk-tab.tsx:31-57,102-170` | UNVERIFIABLE | Formula is internally consistent, but the tab is commented out and threshold usefulness cannot be validated against live data (`milk-company/src/app/[locale]/dashboard/dashboard-view.tsx:414-425`). |
| Invoice-driven KPI totals under a line-level filter | All live KPI/fiscal/payment panels after category/source/review filter | Keep invoices that contain a surviving line, then sum each whole invoice: `milk-company/src/lib/analytics/filters.ts:119-152`; `milk-company/src/lib/analytics/aggregate.ts:76-128` | MISLEADING | A category/review/source filter does not produce matching-line spend; it produces totals of invoices containing at least one match, without that framing. |
| Line-dependent metrics after a line fetch failure | Live category/items/concentration/explorer and KPI hints | Catch sets `linesError` **and** `linesReady=true`: `milk-company/src/app/[locale]/dashboard/dashboard-view.tsx:132-154`; tabs render real components when ready: `milk-company/src/app/[locale]/dashboard/dashboard-view.tsx:391-455` | WRONG | Failure is converted to an empty successful array, so zeros/empty states replace the available error component (`milk-company/src/components/analytics/pending-lines.tsx:16-37`). |
| Total spend, invoice count, suppliers, items, review count/rate, average invoice | Orphaned legacy Overview KPIs | Line amount sum; distinct sets; `Σline amount/distinct invoice`: `milk-company/src/lib/dashboard/aggregate.ts:61-86`; render tree: `milk-company/src/components/dashboard/tabs/overview-tab.tsx:31-42` | CORRECT | Internally consistent for its line-based scope; component is not mounted by the live route. |
| Credit-note amount/count | Orphaned legacy Overview/Tax KPIs | Document-type substring heuristic then sum/count: `milk-company/src/lib/dashboard/invoices.ts:67-93` | UNVERIFIABLE | Code itself says the heuristic was never checked against real document types. |
| Spend-over-time and invoice-volume charts | Orphaned legacy Overview | Line amount / distinct invoices by period: `milk-company/src/lib/dashboard/aggregate.ts:118-143`; charts receive all occurrences: `milk-company/src/components/dashboard/tabs/overview-tab.tsx:43-53` | WRONG | Headline KPIs remove guessed credit notes but both charts retain them, so totals can disagree (`milk-company/src/components/dashboard/tabs/overview-tab.tsx:31-53`). |
| Legacy line-table category | Orphaned legacy Overview | Unsafe mapped category: `milk-company/src/app/[locale]/dashboard/columns.tsx:58-70` | WRONG | Review-gate violation. |
| Category spend | Orphaned legacy Spend Analysis | `Σline amount` by unsafe category: `milk-company/src/lib/dashboard/aggregate.ts:149-193` | WRONG | Review-gate violation. |
| Top suppliers/items/industry/geography spend and counts | Orphaned legacy Spend Analysis | Group line amounts; fold tail into Other: `milk-company/src/lib/dashboard/aggregate.ts:198-238,272-399` | CORRECT | Correct for line-spend scope; legacy components are dead. |
| Total payables, overdue, due soon, AP aging, payment forms | Orphaned legacy Accounts Payable | COMPRAS totals partitioned by due date/form: `milk-company/src/components/dashboard/ap-kpi-tiles.tsx:19-35`; `milk-company/src/lib/dashboard/invoices.ts:96-177` | MISLEADING | No paid flag means these are invoice totals by due date, not outstanding payables; the legacy caller does scope to purchases (`milk-company/src/lib/dashboard/invoices.ts:116-120`). |
| “Discount captured”, surcharges, discount/recargo time and supplier charts | Orphaned legacy Savings | Sum line discounts/recargos: `milk-company/src/components/dashboard/savings-kpi-tiles.tsx:17-48`; `milk-company/src/lib/dashboard/aggregate.ts:401-472` | MISLEADING | Arithmetic is right, but document discount is not evidence that procurement “captured savings.” |
| Auto accepted, needs review, reviewed manually; average margin/entropy; confidence histogram | Orphaned legacy Data Quality | Decision/generated-state counts, arithmetic means, score bins: `milk-company/src/lib/dashboard/aggregate.ts:476-490,519-540`; `milk-company/src/components/dashboard/data-quality-kpi-tiles.tsx:18-81` | CORRECT | These are pipeline diagnostics, not accuracy. Components are dead. |
| Lowest-margin ambiguity queue | Orphaned legacy Data Quality | All `!reviewed`, sorted by margin: `milk-company/src/lib/dashboard/aggregate.ts:543-552` | MISLEADING | `!reviewed` includes auto-accepted lines, so it is not specifically the review-required queue; its category display also violates the gate (`milk-company/src/components/dashboard/tabs/data-quality-tab.tsx:43-50`). |
| Net, IVA, exempt, grand total, invoice count, credit-note total/count, document-type split | Orphaned legacy Tax | Invoice-level sums excluding heuristic credit notes; raw doc-type grouping: `milk-company/src/lib/dashboard/invoices.ts:179-223`; render: `milk-company/src/components/dashboard/tax-kpi-tiles.tsx:17-72` | UNVERIFIABLE | Invoice arithmetic is correct, but the unverified credit-note heuristic changes every headline total. |
| Category-company matrix, coverage, cells/tooltips | Orphaned legacy Comparison | Top-12×top-10 crosstab and covered/grand totals: `milk-company/src/lib/dashboard/entities.ts:403-457`; `milk-company/src/components/dashboard/category-company-matrix.tsx:39-129` | WRONG | Review-gate violation in row dimension. |
| Largest invoices, largest lines, widest price spreads | Orphaned legacy Comparison | Sort descending and top 10; unit spread: `milk-company/src/lib/dashboard/entities.ts:462-475`; `milk-company/src/components/dashboard/outliers-panel.tsx:74-129` | CORRECT | Descriptive maxima, not statistical claims; component is dead. |
| Company profile totals/counts/averages/due days/review rate | Orphaned legacy Explorer | Separate invoice- and line-level accumulators: `milk-company/src/lib/dashboard/entities.ts:83-224` | CORRECT | Avoids invoice multiplication; component is dead. |
| Category profile total/share/invoices/lines/companies/items/price/max/review | Orphaned legacy Explorer | Unsafe category groups: `milk-company/src/lib/dashboard/entities.ts:229-302` | WRONG | Every derived category number inherits the review-gate violation. |
| Item total/quantity/category/suppliers/occurrences/latest price | Orphaned legacy Explorer | Group by catalog ID, add quantities, keep first category: `milk-company/src/lib/dashboard/entities.ts:305-366` | WRONG | Quantity can mix units and first unsafe category can be a pending prediction. |
| Item weighted average/min/max/spread and price trend | Orphaned legacy Explorer | `Σamount/Σquantity`, extrema and dated prices: `milk-company/src/lib/dashboard/entities.ts:24-80,369-400` | WRONG | Spread is suppressed for mixed units, but the weighted average is still calculated and exposed across mixed units. |
| Prototype dashboard KPIs/charts | Excluded `project/` Vite app | Imports generated fixtures: `milk-company/project/src/App.tsx:10-25`; seeded generator: `milk-company/project/src/data/mockData.ts:3-13` | MOCK | Separate excluded prototype, not Next production (`milk-company/tsconfig.json:33-38`). |

---

## 5. Mock and dead code

### `project/` and the legacy dashboard tree

`project/` is a standalone Vite app with its own scripts (`milk-company/project/package.json:1-10`), its app imports `@/data/mockData` (`milk-company/project/src/App.tsx:10-25`), and that data is generated from a deterministic pseudo-random fixture (`milk-company/project/src/data/mockData.ts:3-13`). The Next TypeScript config maps `@/*` to `src/*` and explicitly excludes `project` (`milk-company/tsconfig.json:21-38`). No live `src/` file imports `project/`; the import direction stays inside the prototype (`milk-company/project/src/hooks/useAnalytics.ts:1-2`; `milk-company/project/src/hooks/useAIEngine.ts:1-2`). It is dead with respect to the deployed Next app.

The `src/components/dashboard/**` tree is also orphaned: its tabs import one another internally (`milk-company/src/components/dashboard/tabs/overview-tab.tsx:5-13`; `milk-company/src/components/dashboard/tabs/spend-analysis-tab.tsx:3-7`), while the actual route imports only `components/analytics/**` (`milk-company/src/app/[locale]/dashboard/dashboard-view.tsx:21-36`). It should not be described as a second live dashboard surface.

### Real product routes vs unfinished stubs

| Route | Status | Evidence |
|---|---|---|
| `/dashboard` | **Real Supabase product** | Server fetches categories/companies/catalog/invoices; browser fetches dated lines (`milk-company/src/app/[locale]/dashboard/page.tsx:47-76`; `milk-company/src/app/[locale]/dashboard/dashboard-view.tsx:132-156`). |
| `/productos`, `/productos/[id]/historial` | **Real Supabase product** | Server queries live tables and sends occurrences/catalog item to views (`milk-company/src/app/[locale]/productos/page.tsx:24-50`; `milk-company/src/lib/items/queries.ts:212-268,439-462`). |
| `/extractor` | **Real local utility, not a Supabase product** | Decodes and parses selected files, then exports parsed rows to Excel (`milk-company/src/app/[locale]/extractor/page.tsx:41-109,128-147`). |
| `/aprobacion` | **Unfinished static stub** | All request, amount and budget values come from translation fixtures; action buttons have no handlers (`milk-company/src/app/[locale]/aprobacion/page.tsx:33-119,122-135`). |
| `/cotizacion` | **Unfinished static stub** | One hardcoded quote and `$750.000 CLP`; Add has no handler and Send is disabled (`milk-company/src/app/[locale]/cotizacion/page.tsx:19-27,52-71,89-114`). |
| `/documentos` | **Unfinished static stub** | Hardcoded receipt array and PO `OC-2026-042`; Preview/Download have no handlers (`milk-company/src/app/[locale]/documentos/page.tsx:25-44,63-133`). |
| `/inventario` | **Unfinished mock route** | Six in-file inventory fixtures, derived low-stock count, hardcoded pending-orders `2` and value `$4.2M` (`milk-company/src/app/[locale]/inventario/page.tsx:30-122,124-131,150-205`). |
| `/levantamiento` | **Unfinished form shell** | Uncontrolled fields; Save/Next buttons have no handlers or submit form (`milk-company/src/app/[locale]/levantamiento/page.tsx:52-177`). |
| `/orden-compra` | **Unfinished static stub** | Static translated PO; Download/Edit do nothing and email actions only call `alert` (`milk-company/src/app/[locale]/orden-compra/page.tsx:31-102`). |
| `/pago` | **Unfinished static stub** | Static three-way-match values; Authorize does nothing and Complete only alerts (`milk-company/src/app/[locale]/pago/page.tsx:39-88,90-166`). |
| `/recepcion` | **Unfinished static stub** | UI claims a connected/validated state, but upload/update/validate controls have no handlers (`milk-company/src/app/[locale]/recepcion/page.tsx:39-81,85-144`). |
| `/union` | **Unfinished navigation stub** | Static explanatory content with only a link to the next stub (`milk-company/src/app/[locale]/union/page.tsx:10-57`). |

The sidebar exposes only Products, Dashboard and Extractor; the workflow routes are commented out but remain URL-reachable to any signed-in user (`milk-company/src/components/app-sidebar.tsx:50-67`; `milk-company/src/middleware.ts:42-58`).

### Hardcoded/mock values and placeholders that still render from `src/`

- The reachable order-detail URL uses `MOCK_PRODUCTS`, computes a mock total, and renders raw English controls/table labels (`milk-company/src/app/[locale]/productos/[id]/ordenes/[orderId]/page.tsx:37-65,78-82,94-150`); the fixture lives at `milk-company/src/lib/products-data.ts:38-109`.
- The inventory, quote and document fixtures—and hardcoded `2`, `$4.2M`, `$750.000 CLP`, and `OC-2026-042`—render exactly as listed above (`milk-company/src/app/[locale]/inventario/page.tsx:30-122,150-205`; `milk-company/src/app/[locale]/cotizacion/page.tsx:19-27,52-64`; `milk-company/src/app/[locale]/documentos/page.tsx:25-44,118-123`).
- `Math.random()` still renders random sidebar skeleton width, but no business metric (`milk-company/src/components/ui/sidebar.tsx:602-612`).
- Shared table search falls back to raw `Search...`; column controls render `View`/`Toggle columns` (`milk-company/src/components/ui/data-table.tsx:93-112`; `milk-company/src/components/ui/data-table-column-toggle.tsx:21-55`).
- Every shared DataTable renders raw English selection, page-size, page count and navigation accessibility text (`milk-company/src/components/ui/data-table-pagination.tsx:26-94`; the component is mounted at `milk-company/src/components/ui/data-table.tsx:64-87`).
- Mobile sidebar accessibility text and the dashboard loading announcement are raw English (`milk-company/src/components/ui/sidebar.tsx:198-200`; `milk-company/src/app/[locale]/dashboard/loading.tsx:13-16`).

---

## 6. Correctness risks below the metrics

### Confirmed broken

**Authorization is cosmetic beyond “has a session.”** Middleware checks only whether a session exists; it never checks `ROLE_PERMISSIONS` (`milk-company/src/middleware.ts:35-58`). Roles default to ADMIN, are changed by a header labelled demo, and only filter sidebar links in client state (`milk-company/src/components/header.tsx:30-38,89-109`; `milk-company/src/components/app-sidebar.tsx:37-67`). Therefore any authenticated user can request any localized route regardless of the simulated role (`milk-company/src/lib/roles.ts:18-87`; `milk-company/src/middleware.ts:61-64`).

**The dashboard hides line-fetch failures as zeros/empty data.** The catch branch stores an error but sets `linesReady=true`, which bypasses `PendingLines` and renders the line-dependent components over `items=[]` (`milk-company/src/app/[locale]/dashboard/dashboard-view.tsx:132-154,391-455`; `milk-company/src/components/analytics/pending-lines.tsx:16-37`).

**Schema typing has drifted from production.** `PredictionSource` says the database permits exactly three values, while backend ground truth says all eight are live (`milk-company/src/lib/analytics/types.ts:11-12`; `ML-model/CLAUDE.md:10-14`). The runtime cast does not validate the value (`milk-company/src/lib/analytics/queries.ts:350-364`).

**City drill semantics are inconsistent.** Geography attributes each invoice to the direction-aware counterparty city, but clicking that city activates a filter matching either seller or buyer city; the drill can therefore include invoices not counted in the clicked bar (`milk-company/src/lib/analytics/ai-engine.ts:622-657`; `milk-company/src/lib/analytics/filters.ts:47-67`).

### Might be broken; checks required

**RLS cannot be verified from this repository.** Browser and server clients use the normal session/anon-key helpers; no service-role key is embedded in application code (`milk-company/src/lib/supabase/client.ts:1-5`; `milk-company/src/lib/supabase/server.ts:1-18`). That is the correct architecture for user-scoped reads—service role must never be put in the browser—but it is safe only if production has appropriate authenticated SELECT policies. The checked-in backend DDL enables RLS and grants CRUD only to `service_role`, with no authenticated/anon policy in that file (`ML-model/Temp_Inference/normalized_company_item_schema.sql:198-222`). Check production with a read-only policy inventory such as `pg_policies` plus table grants; do not infer protection from middleware, because direct PostgREST access is governed by RLS, not Next routing.

**Middleware trusts `getSession()` for route gating.** It reads a cookie-backed session rather than asking Supabase Auth to verify the user (`milk-company/src/middleware.ts:35-40`). Production should verify whether the library version cryptographically validates/refreshed tokens here; use `getUser()` for an authoritative server check if it does not. Even a route-gate bypass must still be stopped by RLS.

**JavaScript numeric range.** Analytics defensively converts numeric/string values and rejects non-finite results before summing (`milk-company/src/lib/analytics/queries.ts:228-239,267-270,327-365`). It still uses IEEE-754 `number`; values beyond `Number.MAX_SAFE_INTEGER` would lose CLP pesos, though no evidence in the repository shows totals that large. The product query path relies on typed PostgREST values without the same runtime conversion (`milk-company/src/lib/items/queries.ts:52-89,153-197`). Check maximum line/invoice totals and aggregate magnitudes in SQL.

### Money

- Live analytics sums unrounded numeric values and rounds only in formatting; CLP output explicitly has zero fractional digits (`milk-company/src/lib/analytics/aggregate.ts:76-128`; `milk-company/src/components/analytics/primitives.tsx:15-22`). No pre-sum rounding or average-of-averages was found in the live metrics.
- Weighted averages divide summed amount by summed quantity after accumulation (`milk-company/src/components/analytics/tabs/items-tab.tsx:82-108`). Its ordering is correct, but the result is wrong when units are mixed, as recorded in the metric inventory.
- Product/history pages use locale-unspecified `$${value.toLocaleString()}` rather than CLP currency formatting (`milk-company/src/app/[locale]/productos/items-view.tsx:39-50`; `milk-company/src/app/[locale]/productos/columns.tsx:12-23`; `milk-company/src/app/[locale]/productos/[id]/historial/columns.tsx:10-21`). This can imply another dollar currency and can show decimals; it should use the existing zero-decimal CLP formatter (`milk-company/src/lib/dashboard/format.ts:1-11`).

### i18n

No missing dictionary path was found: a recursive key comparison produced 949 scalar paths in each of `messages/es.json` and `messages/en.json`, with empty `es_only` and `en_only` sets (`milk-company/messages/es.json:1`; `milk-company/messages/en.json:1`). Literal `t("...")` calls also resolved in the static check. The raw/untranslated strings that do render are the DataTable, sidebar, loading and mock order strings listed in section 5 (`milk-company/src/components/ui/data-table-pagination.tsx:26-94`; `milk-company/src/app/[locale]/productos/[id]/ordenes/[orderId]/page.tsx:54-60,78-82,94-150`).

### `any`, assertions and user-visible undefined/NaN risk

- Locale validation uses `as any` in both request config and layout, weakening compile-time checking but not directly creating a user-visible undefined value (`milk-company/src/i18n/request.ts:4-15`; `milk-company/src/app/[locale]/layout.tsx:25-41`).
- The demo role event accepts `e:any` and writes an unchecked role, after which `ROLE_PERMISSIONS[role].includes(...)` can throw if any script dispatches a malformed event (`milk-company/src/components/app-sidebar.tsx:37-67`). The current header dispatches only known select values, so this is a risk rather than a demonstrated failure (`milk-company/src/components/header.tsx:32-38,92-102`).
- Product mapper non-null assertions are preceded by an explicit filter for catalog, invoice and company joins, so those assertions are locally safe (`milk-company/src/lib/items/queries.ts:137-177`). Map assertions in payment aging are also initialized for every legal bucket before access (`milk-company/src/lib/analytics/ai-engine.ts:505-533,556-584`).
- DataTable suppresses the type error for `row.children`; for rows without children this resolves to undefined and is accepted by TanStack, but the unchecked extension can mask a future row-shape error (`milk-company/src/components/ui/data-table.tsx:64-79`).

---

## The spec asks two wrong questions

1. The audited package is **Next 16.1.1**, not Next 15 (`milk-company/package.json:20-35`). That matters because the server Supabase adapter contains a Next-16-specific async-cookie compatibility cast (`milk-company/src/lib/supabase/server.ts:4-18`).
2. There are not two live dashboard surfaces. `src/components/analytics/**` is live, `src/components/dashboard/**` is orphaned, and `project/` is an excluded mock prototype (`milk-company/src/app/[locale]/dashboard/dashboard-view.tsx:21-36`; `milk-company/tsconfig.json:21-38`; `milk-company/project/src/App.tsx:10-25`). Treating findings in all three as equally client-facing would overstate production impact.

## Recommended order of repair (no repairs made)

1. Replace both unsafe category fallbacks with one decision-aware resolver and use it before every render/filter/aggregate (`milk-company/src/lib/items/queries.ts:153-180`; `milk-company/src/lib/analytics/types.ts:133-144`).
2. Split **catalog total (4,002)** from **active items in current filters**, suppress mixed-unit quantity/price, preserve line-fetch error state, and scope payment aging by direction/status semantics (`milk-company/src/components/analytics/tabs/items-tab.tsx:62-215`; `milk-company/src/app/[locale]/dashboard/dashboard-view.tsx:132-154`; `milk-company/src/lib/analytics/ai-engine.ts:526-608`).
3. Replace `/productos`' full history scan with paged catalog summaries (`milk-company/src/lib/items/queries.ts:201-246`; `milk-company/src/lib/analytics/queries.ts:129-135`).
4. Enforce real roles server-side, verify production RLS, remove or quarantine stub/dead surfaces, and localize shared controls (`milk-company/src/middleware.ts:35-58`; `milk-company/src/components/app-sidebar.tsx:37-67`; `ML-model/Temp_Inference/normalized_company_item_schema.sql:198-222`; `milk-company/src/components/ui/data-table-pagination.tsx:26-94`).
