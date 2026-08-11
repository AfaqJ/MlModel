# LABELING RULES — MCT-37 Antillanca invoice classifier (READ FIRST, every session)

This file is the single source of truth for how gold/silver data is organized and what may
enter the gold set. Do not deviate. Do not invent new file layouts.

## What may enter GOLD (these sources)
1. **Client row examples** — `Data/examples_categories/xml examples list.xlsx` → source `direct_client_example`.
2. **Client product rules** (the labeled ones) — `Data/examples_categories/Products list Antillanca.xlsx`
   (+ dated deltas, e.g. `Products list Antillanca(Productos)New.csv`) → source `client_product_rule`.
3. **Client service rules** — the "servicios" sheet (e.g. `Products list Antillanca(Servicios).csv`):
   standardized FUTURE invoice-description templates the client will request from providers via
   purchase order (e.g. "SIEMBRA PRADERA PERENNE" → EXP-8.1). → source `client_service_rule`.
   Same trust tier as `client_product_rule`/`direct_client_example` (tier 1: direct client
   definition) since it comes straight from the client, not from our audit. These rows will not
   match historical raw data (verified: 0 hits against `Data/processed/line_items.csv`) — they are
   forward-looking only, imported per the literal-client-definition exception below.
4. **Folder items** — the 3 example trees in `Data/Raw_Data/old:new_polluted_examples`
   (GASTOS EXPLOTACION, GASTOS ADMINISTRACION, XML FACTURAS 2025). Every leaf folder is named
   after a category. Map folder → category, then audit each item against the client DESCRIPTION
   in `Data/examples_categories/New Categories.xlsx`. If it matches the description → gold
   (source `file_audit`). If it clearly belongs elsewhere, relabel it there if you have enough
   context; otherwise reject. Folder + client description is the DECIDING factor.
   - `file_audit_corrected`: a `file_audit` row whose category was overridden by a semantic
     re-audit against the taxonomy description + product research (brand/product identification),
     because the original folder placement was proven wrong — typically because a multi-item
     invoice was filed into several category folders and every line on it got mislabeled with
     every one of those folders' categories instead of its own true category. See "Conflict
     resolution" below.
5. **Ollama silver labels** — only after MANUAL audit (source `silver_audit`). Never promote
   unaudited silver.

## Conflict resolution (contradictory item_text+provider across categories)
Any two gold rows sharing the same `(item_text, provider)` but different `category_code` are a
direct contradiction for a text classifier (same input, different label) and must be resolved, not
left as-is or merely flagged. Resolution order:
1. **Trust hierarchy**: `client_product_rule` / `direct_client_example` / `client_service_rule`
   (tier 1) > `file_audit` (tier 2, "polluted" but still client-filed) > `silver_audit` (tier 3, our
   own guesses). If a unique tier-1 or tier-2 verdict exists, drop the disagreeing lower-tier rows.
2. **Semantic re-audit** when multiple rows sit at the same tier: identify the actual product/
   service (web research for unfamiliar Chilean brand names if needed) and match it against the
   official category description in `taxonomy_from_plan.csv`. Use sibling line-items on the same
   invoice and any existing tier-1 gold for the same/similar product as corroborating evidence. If
   the correct category isn't among the currently-conflicting options, drop all of them and add a
   fresh `file_audit_corrected` row with the right one.
3. **Non-discriminating text across ADJACENT categories → keep (top-3 resolves).** If the same
   text is split across categories that are genuinely semantically adjacent and all plausible for
   that text — e.g. the three electricity buckets EXP-9.1 (Riego) / EXP-11.1 (Lecheria) / EXP-11.2
   (Casas), where the only real discriminator is which physical meter (never in the text) — KEEP
   the rows. Production returns top-3 for the human to pick on these, so the ambiguity is resolved
   by the UX, not the text model. Do NOT force them into one category (that would make the model
   confidently mislabel the minority categories at inference) and do NOT flag them.
4. **Clearly-wrong placement → relabel.** Only "resolve" a same-text contradiction when the item
   clearly does NOT belong in one of the categories (e.g. work boots filed under Otros
   Medicamentos, an alarm-monitoring fee under Comunicaciones, a milk filter under teat-dip).
   Relabel the wrong row to the correct category (drop only if the relabel yields an exact
   `item_text+description+provider` duplicate). Prefer relabel over delete — the dataset is
   data-limited.

### Detecting contradictions
`scripts/55_contradiction_audit.py` (read-only) reports cross-category collisions at three keys
(item_text ; item_text+description ; item_text+description+provider) AND embedding near-duplicate
cross-category pairs (cosine, using the SetFit base model if cached, else the MiniLM proxy), writing
`Data/gold/_contradiction_report.csv`. Run it after ANY gold change before training. Note the report
still lists the intentionally-KEPT adjacency cases (electricity; client-authored dual-use like
"GASOLINA 93" in both Bencina and Movilizacion; FECCAS soil-vs-animal analysis) and legitimate hard
pairs the model should learn (e.g. "FLETE DE TERNERAS" vs "VENTA DE TERNERAS") — read those as
expected, not new bugs. Do NOT use `verify_flag=client_check` as a substitute for resolving a
clearly-wrong contradiction — that flag is for a short, genuinely-undecidable list the client
confirms manually.

**Secondary material only (never the decider):** product rules and the xml examples sheet help
disambiguate but do not override folder+description.

**FORBIDDEN:** adding to gold directly from raw data (`data/processed/line_items.csv`, raw
COMPRAS/VENTAS) via keyword/regex, or by extrapolating product rules onto raw lines. The only
exception is an item that is a 100% literal match to a client definition, and only with explicit
user permission.

## Folder structure (all under `Data/`; note `Data/` == `data/` on this Mac)
```
Data/gold/
  _master_gold.csv            SINGLE source of truth. Append audited rows HERE.
  _coverage.csv               generated summary (per-cat count + status)
  "<CODE> <leaf> (<count>).csv"  72 generated views — DO NOT hand-edit
Data/silver/
  _index.csv                  per-cat: total / audited / remaining / gold_now
  "<CODE> <leaf>.csv"         72 deduped silver working files (audited flag lives here)
Data/stale/                   superseded files, with README. Nothing deleted, just parked.
```
- **Gold: edit the master, then regenerate the 72 views with `scripts/50_build_gold_views.py`.**
  The count in each filename is regenerated, so it can never drift.
- Gold master columns: `gold_id, category_code, leaf, source, item_text, description, provider, farm, audit_reason`.
- Silver per-cat columns: `candidate_id, item_text, description, provider, giro, source_file, folio, siblings, top1_conf, audited, verdict, audit_reason`.

## Dedup rule
A row is a 100% duplicate ONLY if `item_text` + `description` + `provider` all match another row
in the same category. Same item / different seller is KEPT. Near-duplicates (e.g. different kWh
or amounts, different flete text) are KEPT. Reject a candidate only if it is a 100% duplicate or
genuine junk (invoice totals/headers, no-context fragments).

## Audit tracking
Every silver row carries `audited` (Y/N) + `verdict`. The authoritative list of audited
candidate_ids is `Data/silver_audit_2026_06_30/audit_ledger.csv`. When a silver row is audited,
set audited=Y and verdict (a category code, or REJECT) in its `Data/silver/<cat>.csv` file AND
append the candidate_id to the ledger. Confirmed rows are appended to `Data/gold/_master_gold.csv`.

## Coverage target
≥15 gold per category wherever the data allows. Categories that are data-limited here (need
client sales/payroll data): all ING-* (sales income — absent from purchase invoices) and
ADM-1.1 Remuneraciones (wages). These wait for client data; do not fabricate.

## Reporting & method rules (persisted user directives)
- **English-only:** when reporting labels, categories, or ambiguities to the user, always explain
  in plain English and translate any Spanish item/term. The user does not read Spanish.
- **Examine-data-first:** before choosing a matching/retrieval method, inspect the actual data and
  the category's meaning. Pure keyword matching causes false positives because the same item can
  belong to different categories by CONTEXT (e.g. corn = animal feed vs planting seed). Prefer
  SEMANTIC matching against the client description; use keyword only where the client vocabulary is
  genuinely unambiguous. Precision comes from the description-based audit, not from the retrieval.
- **Raw-prep before labeling:** before labeling raw invoice lines, remove any whose item is already
  in gold (never re-label client direct golds / product rules) and remove 100% duplicates
  (distinct = item_text + provider; same item / different provider is kept).
- **Viability-check first:** never start an Ollama labeling run for a category without a read-only
  premature check that real candidates exist. Do not label noise.
- **Audit everything; never trust model confidence.** Ollama only PROPOSES labels. Every label is
  audited by us against the client description before it can enter gold — a model can be
  confidently wrong, so confidence scores are never a gate. During our audit, if an item is only
  MINOR-ambiguous we keep it in gold with `verify_flag=client_check` (a short curated list the
  client confirms later) instead of rejecting it; clearly-wrong/junk/high-ambiguity is rejected.
- **Classify-then-decide:** do not pre-declare a category "noise" from a few samples. Route every
  candidate through the model, then decide from our audit.
- **Excluded categories (never label):** now **71 trainable** cats. **7 excluded** (orange/no-XML,
  accounting-only) in `Data/current_context_2026_06_30/excluded_categories.csv`: Contratados,
  Honorarios, Arriendo Predio Lecheria, Arriendo Otros Predios, Arriendo Casas, "Impuestos
  comisiones multas", and **ADM-1.1 Remuneraciones Administracion** (admin wages — payroll, not
  invoiced; removed 2026-07-01, had 0 gold, other codes unaffected since codes are literal).
  (ADM-1.3 Arriendo Oficina is a different, XML-backed category and IS in the 71.)

## Regenerate views
`python3 scripts/50_build_gold_views.py`   (gold master → 72 files + coverage)
`python3 scripts/51_build_silver_structure.py`   (silver → 72 files + index)
