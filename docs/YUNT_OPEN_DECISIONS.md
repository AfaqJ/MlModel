# Open decisions — things waiting on Afaq

Written as they came up during the build so nothing needs reconstructing.
Nothing here has been acted on. Nothing has been written to production.
Nothing has been pushed.

---

## 1. Three catalog rows for one service · a data flaw

```
a4cbc781…  'Confección de bolos'    3 lines
d85fbebd…  'Confeccion de Bolos'    9 lines
87fadaae…  'Confeccion Bolos'       2 lines
```

One service, 14 lines, three rows. They survived the canonical migration because
`catalog_normalize_label` lowercases and collapses whitespace but **does not
strip accents**, so `ó` and `o` read as different products. It is the only such
collision in all 4,002 rows — checked exhaustively.

**Two fixes, and the second is the one worth doing.**

- *Patch:* repoint the 5 stray lines onto `Confeccion de Bolos`, delete the two
  orphaned rows. Fixes today, prevents nothing.
- *Better:* also change `catalog_normalize_label` to fold accents, so the unique
  index refuses to create the pair again. Measured: exactly one collision, so the
  index will still build. This is the fix that stops it recurring.

**Not translation.** Nothing anywhere in this system normalises Spanish to
English. The data is Spanish, the client is Chilean, `LEÑA` and `ORDEÑA` are the
real words, and translation is lossy and non-deterministic — it would turn a
lookup into a guess. Accent folding is not translation: `Confección` and
`Confeccion` are the same Spanish word typed two ways.

**Needs:** a yes. Then backup, dry run, scoped write over PostgREST.

---

## 2. P-02, instalment payments · pending *your* confirmation

`reports/catalog_merge_2026_08_26/PATTERNS.md` marks it "PENDING Afaq's
confirmation (proposed 2026-08-26)". That is the only thing it is waiting for.

- **Effect if confirmed:** 9 catalog rows become 4, CLP 136,575,692.
- **It carries a known bug that must be fixed first:** `abono` is on its strip
  list, and in `Traslado De Abono` / `Traslado Abono 2 Vueltas` that word means
  *fertilizer*, not a payment. It appears in none of the 9 rows in scope, so it
  should simply be removed from the list.
- **Why it matters more than 9 rows:** cuotas 2, 3 and 4 have not arrived yet.
  Each will spawn three more catalog rows for the same three components — 6 rows
  become 15 for one purchase — unless the pattern is in place when they land.

P-01 (livestock lots) is already applied and is implemented in the resolver.

---

## 3. Harvesting the alias table from ground truth · the big one

**This changes the "how far can deterministic go" answer.**

2,314 lines fail to match automatically but **already carry a catalog row**,
assigned by the verified canonical migration. That assignment is not a guess —
it is ground truth for an alias, which is exactly what the earlier
supplier-plus-price hunt lacked.

```
distinct wordings                        1,579
  pointing at exactly one catalog item   1,576
  ambiguous, cannot be an alias              3

  RECURRING (seen 2+ times)                272 wordings covering 993 lines
  seen once, volatile (OT/folio/month)     728  -> pattern work, never aliases
  seen once, stable                        576  -> aliasable, 1 line each
```

The 272 recurring ones are the prize. They are bounded, they recur, and each has
a confirmed parent:

```
28x  'toalla papel interfoliada 320 un'   ->  Toalla Papel Interfoliada
20x  'aguja desechable 16g x 1/2"'        ->  Agujas desechables
17x  'cloro organico 5 kg'                ->  Cloro Organico
15x  'tordon 101 x 4 lt'                  ->  Tordon 101
13x  'liquamicina la 250 cc.'             ->  Liquamicina la
```

**Effect on automatic resolution: 78.8% -> about 87.3%.**

**DONE — the harvest is built and measured.** Full list, with the excluded ones
and the reasoning, at `reports/alias_harvest_2026_09_08/README.md`.

| | resolved automatically | disagreeing with today |
|---|---|---|
| live aliases only (8 rows) | 9,255 (78.8%) | 7 |
| + 222 harvested | 10,125 (86.2%) | 7 |

870 lines gained, **zero new disagreements**.

- **222 proposed** — recurring wordings, each already assigned to its catalog
  item by the verified migration. Not an inference: a fact being written down.
- **781 excluded** — unbounded wordings (`SEGUN OT 107`, `108`, `109`…). One
  alias row each, forever, is exactly what D-044 forbids. These need a pattern.
- **585 not proposed** — seen once in fifteen months. Memorising noise.

**Needs, in order:**

1. `milk-company/supabase/006_alias_provenance.sql` run in the SQL editor. It
   adds `source` / `confirmed_by` / `evidence_lines` to `item_aliases`, which
   must exist **before** any bulk insert or an alias you approved becomes
   indistinguishable from one the machine proposed.
2. Your yes on the 222.
3. Then: backup, dry run, scoped PostgREST write. The write script is
   deliberately not written yet — D-046's lesson is that a one-shot script
   written against a database state rots, so it gets written when it is run.

**Why `%LIKE%` in the database is not needed.** You asked. The catalog is 4,002
rows; the Yunt loads it once per batch and does the narrowing in memory, which
is faster than a round trip and needs no extension. A `pg_trgm` index would
matter if the resolver ever ran without the catalog to hand — it does not.

---

## 4. How far deterministic goes, and where reasoning actually starts

Your question, answered with measured numbers rather than an opinion.

| | share of all 11,746 lines |
|---|---|
| resolved automatically today | **78.8%** |
| + the 272 harvested aliases (item 3) | **~87.3%** |
| + the 576 single-occurrence stable wordings | ~92.2% |
| volatile wordings — OT numbers, folios, months, kWh | 6.2% |
| placeholder names (`Item`, `Detalle`, `Mano de obra`) | 1.5% |
| wording genuinely pointing at two items | 0.03% |

**The reasoning frontier is roughly 8%, not 100%.** Everything above it is a
lookup, and lookups do not hallucinate.

**And the Yunt never sees the catalog.** Your token concern is right and the
answer is the same shape as the category proposals: **retrieval narrows, the
model picks.** For an unmatched wording, code produces a shortlist — the items
sharing a meaningful word, typically a handful, never more than a few dozen —
and the model is asked to choose one of those or answer "new item". 4,002 names
never enter a prompt. The model's answer is then checked against the shortlist,
so an id it invents cannot be written.

Where the model genuinely earns its cost:

- the 728 volatile wordings, deciding whether the varying part is a *quantity*
  (strip it) or an *identity* (keep it) — `SEGUN OT 107` versus `GASOLINA 93`;
- the 177 placeholder names, where only free-text description carries meaning
  and no lookup can help;
- proposing a *new* catalog name when nothing fits, which is a naming judgement.

Where it must not be used: anywhere a lookup already answers. 87% of this
problem is a dictionary.

---

## 5. Smaller ones

- **`/predict-batch` is invokable by `allUsers`.** No data exposure (the service
  is stateless), but anyone with the URL spends the Cloud Run budget. Settled as
  D6: lock it to a service account when the Yunt first calls it.
- **The classifier encodes one line at a time.** Measured 127 ms/line against the
  live service, so a 900-line month takes about 114 seconds. Fine for a
  background job. Batching the ONNX encode is the fix if it ever matters.
- **`milk-company/supabase/005_purchase_orders.sql` has not been run.** Until it
  is, the purchasing pages load and error. Idempotent, safe to re-run.
- **Purchasing screens are Spanish-only**, not routed through next-intl. Marked
  with a `ponytail:` comment in `levantamiento/page.tsx`.
