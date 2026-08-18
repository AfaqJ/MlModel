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
| Anything else (`ENVASE`, `EN0000`, or a garbled value) | **Review** | Not one of the client's confirmed signals |

Two traps:

- **The typos are the same word.** `BIDON`, `BIDO93`, `BIDO45`, `BIOD45`,
  `VIDO93`, `IBDO96` are all a person typing "bidón". Match loosely.
- **Absence only means something if the supplier uses the field.** ENEX, Ferosor,
  Entretecho and Pilauco never emit it, so a blank there carries no information.
  COPEC, Steuer, Daniel Villar and the rest always emit it.

**Applied 2026-08-17 by Afaq's instruction:** 13 Steuer rows whose field says
`EN0000`/`ENVA00`/`ENVA01`/`ENV000`/`ENC000`, plus 11 Patricio Santiago Carey
Briones rows with unrecognised plate-like values, moved to review. They are not
silently treated as either vehicle or farm fuel. Raw XML supports exactly these
24 rows; a recovered audit claimed 28 Patricio rows, but could not identify the
other 17 and they were not changed.

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

**Applied 2026-08-17:** 13 overlooked supermarket-food rows moved from Office
Supplies to `EXP-1.1`, and two restaurant/cafe meal rows moved to `ADM-1.5`.
One baked-empanada row and three obvious non-food rows that had been swept into
`EXP-1.1` were returned to review: their final categories are not established.

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
| `AF-2.1` | Compras de Activo Fijo | 19 auto-accepted purchases, CLP 339,658,011; plus 3 lease-buyout rows in review |
| `ING-0.7` | Ventas de Activo Fijo | Selling a vehicle, tank or machine — 6 lines, CLP 112,474,790 |

The client named `AF-1.1` and `ING-0.7`. **`AF-2.1` was ours** — naming only the
sale side left trucks, generators and barn contracts with nowhere to go. Told to
the client 2026-08-17, not asked; he replied "Perfecto", so it is now his.

Codes were ours, not the client's — they said the codes carry no meaning for
them. But **the prefix is load-bearing**: `app/inference/business_rules.py`
masks by prefix, so anything on a VENTAS invoice must start with `ING-`, and
anything on a COMPRAS invoice must not. That is why asset *sales* are `ING-0.7`
rather than an `AF-` code.

`AF-1.1` covers **animals only.** Everything else bought outright is `AF-2.1`.

**Auction settlements are purchases when their source folder says `COMPRAS`.**
The 103 DTE-43 rows from Tattersall Ganado and Feria Ganaderos Osorno (CLP
254,529,000) are `COMPRAS` in both their source folder and input identifiers.
They remain auto-accepted as `AF-1.1`. A recovered audit's claim that they were
sales was an unsupported inference and was rejected; do not reopen it without
client evidence that contradicts the source direction.

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

## 7. Rents and leases — four different categories

Answered by the client 2026-08-17, and applied the same day by
`scripts/83_apply_client_reply_2026_08_17.py`.

| What is rented | Code | Name |
|---|---|---|
| A bank lease contract (BICE, Santander) | `EXP-15.8` | Leasing |
| Farmland **with** a milking shed | `EXP-15.6` | Arriendo Predio Lecheria |
| Farmland for non-milking animals | `EXP-15.7` | Arriendo Otros Predios |
| Machinery, vehicles, meters, toll tags | `EXP-15.4` | Arriendo Maquinaria y Vehiculos |
| Office | `ADM-1.3` | Arriendo Oficina |

His words on the bank leases: *"Just put them in leasing account. I'm not sure
if its created, if not, you can create it — Leasing."* No split by what is being
leased; 141 BICE + 17 Santander lines, CLP 343,684,709, all `EXP-15.8`.

His words on farmland: *"Predio Lecheria are for leases that have a milk shed,
Arriendo otros predios for leases for younger animals that are not milking. Not
all farmland leases make invoices, in the case of Pelleco it must go to Arriendo
Otros Predios."* 14 Pelleco lines, CLP 33,432,633.

**Two things this rule cannot decide on its own:**

- **The invoice never says whether a farm has a milking shed.** `ARRIENDO FUNDO
  PELLECO / LOTE A ROL 2230-12` is the whole line. Pelleco is settled because he
  named it. Any *other* property needs him again — `EXP-15.6` exists but has zero
  rows, and will stay empty until a named answer arrives.
- **Ending a lease is not paying rent.** Three BICE lines buy the asset out —
  `Opcion de compra del contrato Nº16380-1` (×2: a 15,000 L milk cooling tank
  and a 50-station rotary parlour) and `Prepago Total del contrato Nº32799-1`
  (a 2024 John Deere 6115J tractor), CLP 26,580,084. They read as `AF-2.1`, but
  that is **our** reading, so they sit in review with `final_code` NULL. Only 3
  of BICE's 206 lines carry a description; those three are the only place the
  bank names the machine.

The other 62 BICE lines are commissions, payroll fees and FX — untouched, and
not leases.

## 8. Never display an unconfirmed label

`predicted_code` is not an answer while `decision = review_required`. `final_code`
must be NULL for those rows. Showing a low-confidence guess as a final
classification is what caused the original incident.

---

## To tell the client — decided, not asked

- **Supermarket food and drink moved to Other HR costs.** 204 rows, CLP 620,072.
  Restaurant meals and toilet paper stay where his own labelled rows put them.

## Still open — needs the client

**The 2026-08-17 email has been answered and applied.** All four questions came
back; nothing from that round is still waiting on him. What his answers left
behind:

1. **Untagged petrol has no forward rule.** He answered the 77 lines (CLP
   4,497,441 — 52 ENEX, 9 Entretecho, 5 Pilauco Viejo, 4 Barca, 7 one-offs) with
   *"Our team to place."* That places these 77, but we asked for a **default
   rule** and did not get one, so every future fill-up at a station that omits
   `<Patente>` lands in review forever. Worth telling him that consequence — it
   is a growing queue, not a one-off.
2. **Which farms have a milking shed.** See §7 — `EXP-15.6` cannot be populated
   from an invoice. Only ask when a second farmland lease actually appears.
3. **Do the three lease buyouts belong in `AF-2.1`?** CLP 26,580,084, in review.
   See §7.
4. **Does work *around* a new build join the asset or stay an expense?** 4 lines,
   CLP 5,442,100 (A&C Electricidad lighting CLP 3,212,100; Magdiel Montecinos
   `Muro galpón` + `Galpón y taller Maitén` CLP 2,230,000), all `review_required`
   at 0.39–0.51. Recurs on every future build; worth asking once a bigger batch
   is behind it.
5. **Bank commissions — does he want his "Impuestos, comisiones, multas" account?**
   56 lines, CLP 5,193,633, all from Banco BICE: `Comisión por Nóminas en Línea`,
   `COMISION DE USO MENSUAL`, `Comisión por Transferencia Electrónica`,
   `Comisión por Pagos de Nominas`, `Administracion de Contratos`. **26 of them
   are auto-accepted** under `ADM-1.7` Otros Gastos Administracion, which is a
   defensible home — this is not a data error like Pelleco was. But his chart of
   accounts has a real account for commissions, and it was dropped at intake on
   the claim *"normalmente no tienen xml"* — which these 56 invoices disprove.
   Ask before creating a code: it is his chart, not ours. See the exclusion-list
   trap below.

**Answered 2026-08-17 and applied — do not re-ask:**

- ~~Bank leases~~ → `EXP-15.8` Leasing, §7.
- ~~Farmland rental has no category~~ → it did; see §7 and the exclusion-list
  trap below.
- ~~`AF-2.1` was ours, will he accept it~~ → *"Perfecto"*, see §4.
- ~~The barn / multi-invoice assets~~ → *"you identified this right…
  Constructora Raul Palma are from the last barn we built, fixed asset."*
- ~~Rename COPEC's `DETALLE` rows~~ → yes: *"All Gasolina should be standarized,
  they all correspond to item 510138 Bencina, its just a diferent name for
  gasoline, so yes, rewrite."* **Name only.** `510138` is his internal account
  number for `EXP-11.4 Bencina`; he was saying the products are the same
  gasoline under different names, **not** collapsing the plate split in §1. The
  renaming is deliberately not applied yet — it needs a strategy, not a
  one-supplier patch.

> **The exclusion-list trap — check this before ever declaring a category
> missing.** `Arriendo Predio Lecheria` and `Arriendo Otros Predios` were never
> absent from the taxonomy. Both sit in
> `Data/current_context_2026_06_30/excluded_categories.csv`, dropped at intake on
> the client's own reason: *"Do not have XML files."* Pelleco is **named in that
> row's notes**. The exclusion was a claim about what data exists, not a policy
> — and the claim was wrong. The other properties named there (Jimena,
> Bramadero, Raíces, Yutreco, Chapilcahuin) were checked: they appear on
> invoices only as *places* — freight to and from, lime applied there — never as
> rent, so the exclusion holds for them. **A second entry on that list has now
> also been falsified: `Impuestos, comisiones, multas`, marked "normalmente no
> tienen xml" — Banco BICE alone issues 56 commission invoices, CLP 5,193,633.**
> Two of the list's factual claims have now been checked and both were wrong.
> Treat the rest of that file as unverified. See "Still open" #5.

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
- ~~A CLP 22,507,092 contract prepayment booked as vehicle insurance; looks like
  a lease.~~ **Identified 2026-08-17.** It is `Prepago Total del contrato
  Nº32799-1`, and its description names a 2024 John Deere 6115J tractor — the
  early payoff of the BICE lease whose rent lines are now `EXP-15.8`. Moved to
  `AF-2.1`, still in review; see §7.
- Side work on the barn — now tracked in "Still open" #4 above.

**Still unasked, and the highest-value item available:**

- **July 2026 onward invoices.** They offered them as training data. Need volume,
  format, and whether the labels are client-confirmed or uncorrected model
  output. Dropped from the 2026-08-17 email twice; ~3,529 review rows are
  undertrained rather than ambiguous, so this is the single biggest lever.
