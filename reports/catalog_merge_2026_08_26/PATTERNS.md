# Catalog composition patterns — running ledger

Started 2026-08-26. Two things live here, and they are different:

1. **The row mappings** (`*_merge_map.jsonl`) — exactly which catalog rows merge
   into which, for *this* batch. One-shot, reviewable, applied once.
2. **The generalizing patterns** below — the rule each batch teaches, so future
   ingestion does not re-create the mess. These outlive the batch.

The patterns feed **step 4** of the resolver in `docs/CATALOG_MATCHING_PROPOSAL.md`
("an approved, narrow pattern that removes only known volatile data and retains
the actual identity"). They are **not** aliases: D-044 forbids storing
quantities, dimensions, months and instalment strings as aliases, and these
strings never recur anyway, so there is nothing to alias.

Nothing here is implemented. There is no online Supabase ingestion writer in
this repository yet (D-044, `docs/STATE.md` item 3) — that is the blocker, not
the matcher. This file exists so the rules are not re-derived from a catalog
that has since been cleaned.

## The constraint that governs every pattern

From `docs/CATALOG_MATCHING_PROPOSAL.md`:

> Do not create a generic rule that strips all numbers. `93`, `95`, `97`, vehicle
> plates, contract IDs, models and grades can define identity.

Every pattern below is therefore **scoped** — to a supplier, a category, or a
product family. A global rule is always wrong here.

---

## P-01 — Livestock auction lots

**Status:** APPLIED to production 2026-08-26 (`scripts/95_apply_livestock_merge.py`)
· **Mapping:** `livestock_merge_map.jsonl`
· **Effect:** 35 catalog rows → 8 · CLP 128,763,985

**Scope guard:** bovine purchase lines only — item name matches
`^\d{1,4}\s+(Vaca|Vac|Vaq|Vacuno|Torete|Ternera|Novillo|Buey)`, category `AF-1.1`,
livestock auction suppliers (Feria Ganaderos Osorno, Tattersall Ganado).
Do not apply outside `AF-1.1`.

**Name structure:**

```
<head count> <animal type>(s) <grade> <breed/colour> <brand mark> <brand location>
   006          Vaq(s)        EXPORT.      Cab            .           Lomo
```

**Strip** (specification, not identity): head count, breed/colour
(`Jer`/`Jers`/`Jersey`/`Neg`/`Bay`/`Cla`), brand mark (`.` `/\` `/\/\` `%` `O`
`T` `X` `H` `39` — any symbol or short token), brand location (`Lomo` = back,
`Anca` = rump, `Cab` = head).

**Keep** (identity): animal type **and grade**. D-044: *"Different grades …
remain separate."* `EXPORT.`, `CARN. EXPORT.`, `S/G`, `ENG.` and `Gorda` are
distinct grades and must not collapse into each other.

**Canonical targets:** Vacas Export · Vaquillas Export · Vacas Carne Export ·
Vacunos S/G · Vaquillas Engorda · Vaquillas Gordas · Toretes · Terneras

**Why it is safe:** every one of the 35 rows had exactly **one** invoice line.
The names are unrepeatable by construction — a specific lot of specifically
branded animals is bought once — so no price history is ever obtainable under
them. Head count confirmed as a count, not a code, by arithmetic: kg ÷ count
gives 153 kg/calf, 360 kg/heifer, 445 kg/young bull, ~390 kg/cow.

```json
{"id":"P-01","scope":{"category":"AF-1.1","name_regex":"^\\d{1,4}\\s+(Vaca|Vac|Vaq|Vacuno|Torete|Ternera|Novillo|Buey)"},
 "strip":["leading_head_count","breed_colour","brand_mark","brand_location"],
 "keep":["animal_type","grade"],"confidence":"exact","requires_review":false}
```

---

## P-02 — Instalment and advance payments

**Status:** PENDING Afaq's confirmation (proposed 2026-08-26). Not applied — P-01
shipped alone on 2026-08-26. **Remove `abono` from the strip list before applying:**
it means fertilizer in `Traslado De Abono` / `Traslado Abono 2 Vueltas` (EXP-15.5,
seller 779509370) and appears in none of the 9 in-scope rows.
· **Effect if confirmed:** 9 catalog rows → 4 · CLP 136,575,692

**Scope guard:** the payment marker must be a *prefix or suffix* on a name that
still contains an equipment, contract or project identity. If stripping the
marker leaves a generic residue (`Material Nacional` alone, `ANTICIPO` alone),
**do not merge** — qualify the canonical name with its project instead.

**Strip** (payment schedule, not identity): `NN% Anticipo`, `Anticipo del NN%`,
`Cuota N-M`, `Estado de pago Nº N`, `saldo`, `abono`, `parcial`.

**Keep** (identity): the equipment, contract or project. `docs/CATALOG_MATCHING_PROPOSAL.md`
says it directly — *"installment/month patterns must retain the contract or
equipment identity."*

**Worked evidence — HGS Dairy Solutions (RUT 761757865), milking parlour:**
`20% Anticipo` (folio 26366, 2026-01-22) and `Cuota 1-4` (folio 26576,
2026-02-24) carry **identical amounts** on the same three components. Not a
duplicate: 20% deposit + 80% split into 4 instalments means every payment is 20%
of the total, so equality is arithmetic, not error. Implied contract value
CLP 42,875,425 net over five payments.

**Worked evidence — Constructora Raúl Ernesto Palma, shed at Fundo El Maitén:**
`35% de anticipo de` → `Estado de pago Nº1` → `saldo presupueso inicial`,
CLP 119,425,522 for one barn under three names, none of which says "barn". The
third row carries no description and is joined by supplier + sequence +
category only — weaker evidence, flagged for Afaq.

**Why it matters more than it looks:** cuotas 2, 3 and 4 have not arrived. Each
will spawn three more catalog rows for the same three components — 6 rows would
become 15 for one purchase. Merging makes the schedule accumulate under one name.

```json
{"id":"P-02","scope":{"requires_residual_identity":true},
 "strip":["percent_anticipo","cuota_n_of_m","estado_de_pago_n","saldo","abono","parcial"],
 "keep":["equipment_or_contract_identity"],
 "reject_if":"residue_is_generic","confidence":"pattern","requires_review":true}
```

---

## Rejected — do not turn these into patterns

- **Stripping all leading digits.** Would eat `93`/`95`/`97` in petrol grades.
  P-01 is scoped to `AF-1.1` bovine lines precisely to avoid this.
- **Merging on provider alone.** `Material Nacional` (2025-04-29, CLP 45,900)
  shares a supplier and an exact name with a parlour component nine months
  later, and is an unrelated purchase.
- **Collapsing grades.** `EXPORT.` vs `CARN. EXPORT.` vs `S/G` are the client's
  own distinctions and are load-bearing.
