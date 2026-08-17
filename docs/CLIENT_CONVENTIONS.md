# CLIENT CONVENTIONS — how Antillanca wants things labelled

Rules the **client** gave us, in their own words or from their own labelled rows.
These beat our judgement, our keyword audits, and anything the model learned.

> **The rule about the rules.** When our data disagrees with something on this
> page, our data is wrong. Twice now a keyword audit or a supplier-level
> generalisation quietly overwrote a client answer, and both times the client's
> version turned out to be the right one. Count authority, not row volume — a
> label sourced `client_product_rule` or `direct_client_example` outranks fifty
> rows sourced `silver_audit`.

Provenance lives in the `source` column of `Data/gold/_master_gold.csv`:

| `source` | Trust | What it means |
|---|---|---|
| `direct_client_example` | **Highest** | Client labelled this exact row |
| `client_product_rule` | **Highest** | Client mapped this product to this category |
| `client_new_category` | **Highest** | Client created the category (2026-08-14) |
| `client_convention` | **Highest** | Client stated the rule in writing (2026-08-14) |
| `plate_rule_audit` | High | Deterministic, read off the invoice |
| `file_audit` | Medium | Inferred from the folder the client filed it in |
| `silver_audit`, `silver_audit_v2` | **Low** | Our keyword matching. Never overrides the rows above. |

---

## 1. Petrol — the plate tells you what it was for

Chilean invoices carry a `<Transporte><Patente>` field. At a service station the
cashier types **either the vehicle's plate, or the word "bidón"** (jerrycan).

| Field contains | Label | English |
|---|---|---|
| A plate (`TBZL91`, `PKSR82` …) | `ADM-1.4` | Vehicle travel |
| `BIDON` / `BIDO93` / `BIOD45` … | `EXP-11.4` | Petrol, farm |
| Empty, **but this supplier does fill it elsewhere** | `EXP-11.4` | Petrol, farm |
| Empty, and this supplier **never** fills it | **Unresolved — ask** | |

Two traps:

- **The typos are the same word.** `BIDON`, `BIDO93`, `BIDO45`, `BIOD45`,
  `VIDO93`, `IBDO96` are all a person typing "bidón". Match loosely.
- **Absence only means something if the supplier uses the field.** ENEX, Ferosor,
  Entretecho and Pilauco never emit it, so a blank there carries no information.
  COPEC, Steuer, Daniel Villar and the rest always emit it.

**The co-op is not a special case — this was checked and the exception was
wrong.** `<Transporte>` is legally the goods-dispatch section, so a plate on a
bulk supplier's invoice *looks* like it should be their delivery truck. It
isn't: **41 of the co-op's 47 plate lines carry the same plates that appear at
the service stations** (`TBZL91`, `PKSR82`, `TJXC63`, `TJXC64`) — Antillanca's
own vehicles. A delivery fleet would be a disjoint set. The co-op's block also
carries no `<Chofer>`, while the service stations' do. All 47 resolved as
vehicle travel.

Method worth reusing: when a field might mean two different things depending on
the supplier, check whether the *values* overlap across suppliers. Shared values
mean one meaning.

This rule is **petrol only.** Diesel is `EXP-11.3` regardless of plate — settled
by the product name, and the client's own filing has been 100% consistent.

## 2. Gas — size decides, not the word "gas"

| Product | Label | English |
|---|---|---|
| Refillable cylinders — 15 kg, 45 kg | `EXP-11.5` | Gas |
| Small butane cartridges — 190 g, 227 g, 230 g, 450 g | `EXP-16.2` | Other farm expenses |
| Gas hoses (`FLEXIBLE GAS …`) | `EXP-16.2` | Other farm expenses — a plumbing part |

A big cylinder is a fuel cost. A little cartridge is a consumable, like a tool.
Our keyword audit had swept all of them into Gas on the strength of the word
alone; the client's `client_product_rule` rows said otherwise and won.

## 3. Food and supplies — three separate buckets

Checked against the client's own row-level labels on 2026-08-14. **There is no
contradiction** — the three cases never overlapped, and the new instruction fills
a gap he had never ruled on.

| What | Label | English | Authority |
|---|---|---|---|
| Restaurant meals — `ALMUERZO`, hotel food & beverage | `ADM-1.5` | Meals & lodging | **Client**, 5 labelled rows |
| Non-food supplies — toilet paper, napkins | `ADM-1.6` | Office supplies | **Client**, 1 labelled row |
| Supermarket food & drink — biscuits, Coca-Cola, sugar, coffee | `EXP-1.1` | Other HR costs | **Client instruction**, 2026-08-14 |

The earlier belief that "the client files groceries under Office Expenses" was
**wrong**. His single labelled supermarket row was `PAPEL HIGIENICO … ELITE` —
toilet paper, which is not food. Every biscuit and sugar row sitting in Office
Supplies had been put there by *our* audit, not by him.

**Applied:** 204 food-and-drink rows moved to `EXP-1.1`, 175 of them out of
Office Supplies. Client to be **informed**, not asked.

Two traps in this bucket:

- **`CAFÉ` is usually the colour brown, not coffee.** `BOTIN NORSEG PRO CAFÉ 42`
  is a brown safety boot; `Silla … Ecocuero Cafe` is a brown chair. Only
  `CAFE NESCAFE …` is actually coffee.
- **Dairy shed sanitiser is not a cleaning supply.** `detergente`/`cloro` bought
  for the milking parlour stays in `EXP-10.3`, not Office Supplies.

## 4. Three categories created on 2026-08-14

Their chart of accounts is **expenses-only by design**. Buying a cow, a truck or
a tractor is a *fixed asset* to them, not an expense — which is why no expense
category ever fitted, and the model was forced to pick a wrong one.

| Code | Name | Covers |
|---|---|---|
| `AF-1.1` | Compras de Animales | Buying live animals — 113 lines, CLP 529,541,100 |
| `AF-2.1` | Compras de Activo Fijo | Buying a vehicle, machine, generator or building — 19 lines, CLP 339,658,011 |
| `ING-0.7` | Ventas de Activo Fijo | Selling a vehicle, tank or machine — 6 lines, CLP 112,474,790 |

The client named `AF-1.1` and `ING-0.7`. **`AF-2.1` was ours** — naming only the
sale side left trucks, generators and barn contracts with nowhere to go. Told to
the client 2026-08-17, not asked.

Codes were ours, not the client's — they said the codes carry no meaning for
them. But **the prefix is load-bearing**: `app/inference/business_rules.py`
masks by prefix, so anything on a VENTAS invoice must start with `ING-`, and
anything on a COMPRAS invoice must not. That is why asset *sales* are `ING-0.7`
rather than an `AF-` code.

`AF-1.1` covers **animals only.** Everything else bought outright is `AF-2.1`.

## 5. Fuel item names that mean the same thing

Petrol is written ten ways. Anything matching these is petrol:

```
GASOLINA 93 · Gasolina 93 · G93 · 93 S/P · Gasolina 93 octanos sin plomo
GASOLINA 95 · Gasolina 95 octanos · V-POWER 97 · Aramco Gasolina 93
DETALLE   ← COPEC only; the name says nothing, the description says "GASOLINA"
```

Careful — these contain a fuel word but are **not** fuel: `FILTRO COMBUSTIBLE`,
`ACEITE`/`Eurodiesel 15W40` (engine oil), `BIDON CERT. AMARILLO DIESEL 20 L` (an
empty jerrycan), `EST. DIESEL PORTATIL` (a tank), `UNIDAD MOTRIZ BENCINERA` (an
engine).

## 6. Meaningless item names — the user picks

Codes, template headers, payment references (`Item`, `DETALLE`, `Estado de pago
N1`, `35% de anticipo de`). The client's answer for v1: **let the user choose in
the UI.** Don't guess from the supplier.

One structural case is fixable without them: **DIFOR** (a vehicle garage) prints
a table whose column header parses as a line item and carries all the money,
while the real service name sits on a CLP 0 line. Merged on 20 invoices —
name moved onto the money line, zero line deleted.

## 7. Never display an unconfirmed label

`predicted_code` is not an answer while `decision = review_required`. `final_code`
must be NULL for those rows. Showing a low-confidence guess as a final
classification is what caused the original incident.

---

## To tell the client — decided, not asked

- **Supermarket food and drink moved to Other HR costs.** 204 rows, CLP 620,072.
  Restaurant meals and toilet paper stay where his own labelled rows put them.

## Still open — needs the client

**Asked by email 2026-08-17** (reply received, not yet processed):

1. **The bank leases. CLP 343,684,709 — the largest open item.** Banco BICE
   `Renta de Arrendamiento Nº_ del contrato Nº_`, 141 lines, CLP 310,427,389,
   across **16 distinct contract numbers**; 135 of the 141 carry that string and
   nothing else, description empty. Santander, 17 lines, CLP 33,257,320, every
   line the identical string `PAGO ARRIENDO OPERACION:`. **Neither invoice says
   what is being leased** — verified, not assumed. Asked: are these all
   machinery and vehicles (`EXP-15.4`), or split? Review cannot resolve this;
   a reviewer sees exactly what we see.
2. **Farmland rental has no category.** `ARRIENDO FUNDO PELLECO`, 14 lines,
   CLP 33,432,633, monthly, land roll in the description (`LOTE A ROL 2230-12`).
   Perfectly legible; the taxonomy has only `EXP-15.4` (machinery/vehicles) and
   `ADM-1.3` (office).
3. **77 petrol lines with no tag.** Verified against the raw XML: **all 77 have
   no `<Patente>` element at all.** 52 ENEX, 9 Entretecho, 5 Pilauco Viejo,
   4 Barca, 7 across six one-off suppliers. Asked for a *default rule* rather
   than a per-supplier answer, so future unseen stations are covered too.
4. **Rename COPEC's `DETALLE` rows** to `Gasolina 93`? 50 rows. Cosmetic only —
   all 50 carry a plate and are correctly `ADM-1.4`.

**Resolved, no longer open:**

- ~~Buying a non-animal fixed asset~~ — `AF-2.1` created and applied, see §4.
- ~~Multi-invoice assets / the barn~~ — the premise was wrong. The client feared
  a barn arrives as wood + nails across many invoices. It does not: one builder
  invoiced it in **contract stages** — 5 lines from Constructora Raul Ernesto
  Palma, CLP 152,521,235 (`35% de anticipo`, `Estado de pago Nº1`, `saldo
  presupuesto inicial`, `adicionales`, `portones`), all already in `AF-2.1` and
  auto-accepted. No project code needed.
- ~~The co-op's petrol~~ — see §1.

**Not asked, deliberately** — too small to spend client attention on; left in
review for their team:

- `OTROS INGRESOS`, CLP 750,000, road-maintenance income. Not an asset sale.
- A CLP 22,507,092 contract prepayment booked as vehicle insurance; looks like a
  lease.
- Side work on the barn billed by other contractors — 4 lines, CLP 5,442,100
  (A&C Electricidad lighting CLP 3,212,100; Magdiel Montecinos `Muro galpón` +
  `Galpón y taller Maitén` CLP 2,230,000). All already `review_required` at
  0.39–0.51 confidence. The underlying convention — does work *around* a new
  build join the asset or stay an expense? — recurs on every future build and is
  worth asking once a bigger batch is behind it.

**Still unasked, and the highest-value item available:**

- **July 2026 onward invoices.** They offered them as training data. Need volume,
  format, and whether the labels are client-confirmed or uncorrected model
  output. Dropped from the 2026-08-17 email twice; ~3,529 review rows are
  undertrained rather than ambiguous, so this is the single biggest lever.
