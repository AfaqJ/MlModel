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

**`file_audit` is more trustworthy than "Medium" suggests — measured 2026-08-19.**
The fear was noise: an invoice dropped in the wrong folder by accident. It was
tested. Across all 392 `file_audit` rows, **363 of 369 distinct item-kinds went
into exactly one category (98%)**. The only 6 that split are electricity lines
from the Paillaco co-op, where the account genuinely depends on which meter it
is — already handled by `meter_lookup`, not client error.

Consistent placement is intentional placement. So **where the client filed the
same kind of item the same way every time, his folder beats our model**, which
is undertrained on most of these classes. Worked example: he files
`Revision Tecnica Automovil particular camioneta` under `EXP-13.3` (4 of 4) and
`Revision Tecnica Maquinaria automotriz` under `EXP-13.1` (1 of 1) — the
inspection follows what the asset is. The model predicts `EXP-13.3` for both,
because exactly one machinery example exists in gold.

Two limits. A `file_audit` convention backed by a single gold row is still one
data point — relabel on it, but only promote to auto-accept when the model
independently agrees (D-037). And a placeholder item name (`Item`, `DETALLE`,
`MATERIALES`) must never be used as the match key: it identifies no product and
collides with every other placeholder from the same supplier.

**`client_evidence_backfill` is a misleading tag name.** Of its 612 rows, none
trace to a highest-trust client label: 243 rest on `file_audit` and 367 on
`silver_audit_v2`, which is our own keyword matching. Read the backing gold
source, never the tag.

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

1. **Do the three lease buyouts belong in `AF-2.1`?** CLP 26,580,084, in review.
   See §7.
2. **Does work *around* a new build join the asset or stay an expense?** 4 lines,
   CLP 5,442,100 (A&C Electricidad lighting CLP 3,212,100; Magdiel Montecinos
   `Muro galpón` + `Galpón y taller Maitén` CLP 2,230,000), all `review_required`
   at 0.39–0.51. Recurs on every future build; worth asking once a bigger batch
   is behind it.
3. **Bank commissions — does he want his "Impuestos, comisiones, multas" account?**
   56 lines, CLP 5,193,633, all from Banco BICE: `Comisión por Nóminas en Línea`,
   `COMISION DE USO MENSUAL`, `Comisión por Transferencia Electrónica`,
   `Comisión por Pagos de Nominas`, `Administracion de Contratos`. **26 of them
   are auto-accepted** under `ADM-1.7` Otros Gastos Administracion, which is a
   defensible home — this is not a data error like Pelleco was. But his chart of
   accounts has a real account for commissions, and it was dropped at intake on
   the claim *"normalmente no tienen xml"* — which these 56 invoices disprove.
   Ask before creating a code: it is his chart, not ours. See the exclusion-list
   trap below.

### Convention questions — measured 2026-08-18, not yet sent

> **These thirteen entries overlap and their row counts must not be summed.**
> The hardware-store question contains the fastener, fitting, welding and
> building-paint questions; several product families appear under two headings.
> An **exclusive** partition of the review rows (4,461 when measured; 4,411
> after the 2026-08-19 promotions) — every row in exactly one
> group, summing to the total — is in the 2026-08-18 sixth-pass entry of
> `docs/STATE.md` and in the published client brief. It reduces to **eight**
> questions covering 2,110 rows (47% of the queue, 12% of the money). Use that
> grouping when talking to the client; use the detail below when working a
> specific family.


These are different from #1–3 above. Those are one-off rulings on specific
invoices; these are **recurring product families where one answer settles
hundreds of rows at once**, now and forever. Every count below is from the
staged payload after `scripts/86_disperse_misfiled_hardware.py`.

**Why these exist: the review queue is not 4,613 independent problems.**
55% of it comes from 15 suppliers, and one hardware store dominates:

| supplier | giro | review rows | spread over |
|---|---|---:|---:|
| DORIS IVONNE CASTILLO KANTER | Ferretería | 868 | **26 categories** |
| COMERCIAL CLIMENT SPA | building materials | 302 | 15 |
| GEA Farm Technologies Osorno | milking-plant service | 244 | 6 |
| SODIMAC S.A. | building materials | 236 | 23 |
| ADMIN. DE SUPERMERCADOS HIPER | supermarket | 139 | 14 |
| COMERCIAL HARCHA SPA | Ferretería | 127 | 17 |

One hardware store's screws and fittings are spread across 26 accounts. That is
a missing convention, not 868 judgement calls. Ranked by rows settled per
question asked:

1. **Water and irrigation fittings — confirm the default.** **240 lines still
   in review**, CLP 3.52M, spread over 6 accounts: `EXP-14.3 Mantencion Agua y
   Purines` (156), `EXP-13.1 Mantencion Maquinaria` (27), `EXP-10.1 Mantencion
   Sala` (26), plus stragglers in Otros Gastos Campo, Utiles de oficina and
   Otros Gastos RRHH. Threaded nipples, bushings, PVC elbows and tees, ball
   valves. **Propose: any plumbing fitting defaults to `Mantencion Agua y
   Purines` unless the invoice names another system.**

   **HDPE is already settled and must not be re-asked** — the client filed
   `TUBERIA HDPE 63MM` under `EXP-14.3`, so 87 HDPE compression fittings were
   auto-accepted there on 2026-08-18. 16 HDPE rows remain in review only because
   the model predicts `Mantencion Sala` for them; 16 rows is not worth his time
   and they stay in review. The open question is the **non-HDPE** fittings.

   One thing his answer must settle: the lookup files `HI PLANZA 1"` and
   `K-L ASPERSOR NELSON` under `EXP-9.2 Otros Gastos Riego`, so fittings already
   split between water/slurry and irrigation depending on use. Ask which wins
   when the invoice does not say.
2. **Nails, screws and fasteners — which account?** 217 lines, CLP 1.46M, 191
   in review, spread over 15 categories. Currently split `Mantencion
   Instalaciones` (80) vs `Mantencion Cercos` (75) — and nothing on the invoice
   says which. **Ask: is there a default account for building fasteners, or
   should they follow the job they were bought for?** If it is the job, we
   cannot infer it and these stay in review permanently — worth him knowing.

3. **The hardware-store default.** Behind #1 and #2: 868 review lines from one
   ferretería. **Ask: when a hardware-store line names only an object and no
   job — a bolt, a hinge, a metre of hose — is there a default account, or does
   his team place every one?** This is the single highest-leverage answer
   available; it decides whether ~800 lines are automatable at all.

4. **Bale making: `Bolos Silo` vs `Bolos Heno`.** 72 lines, **CLP 208.7M** —
   by far the largest money in this list. `Confección de bolos`, `Diferencia de
   bolos`, `Bolos bramadero` from Héctor Adrián Valenzuela. 50 currently
   `Bolos Silo`, 18 `Bolos Heno`, and **the invoice text never says which**.
   **Ask: how does his team tell silage bales from hay bales on these invoices
   — by season, by property, or does the contractor say?** Highest value per
   question of anything open.

5. **Fire-extinguisher servicing.** 52 lines, CLP 2.06M, all in review, split
   across `Mantencion Instalaciones` (18), `Mantencion Maquinaria` (17) and
   `Utiles de oficina` (12). **Propose one home for extinguisher inspection and
   recharge regardless of where the extinguisher hangs.**

6. **Road tolls and TAG.** 66 lines, CLP 642K, all in review, across 6
   accounts including `Mantencion Caminos` (23) — which is road *maintenance*,
   not tolls. `ARRIENDO TELEVIA`, `VIAJES TAG`, `TRANSITO`. **Propose:
   `ADM-1.4 Movilizacion`, matching vehicle fuel.**

7. **Paint — two kinds, one word.** 160 lines, CLP 11.6M. 98 are already
   correctly in `Otros Gastos Salud Animal`: `PINTURA CELO TELL TAIL` is
   livestock heat-detection paint, not decoration. The other ~60 are ordinary
   enamel and brushes, now parked in `Mantencion Instalaciones`. **Ask: where
   does ordinary building paint go?** Confirm we keep tail paint under animal
   health.

8. **Welding rod, discs and abrasives.** 52 lines, CLP 603K, all in review,
   across 13 accounts. Same shape as #2 — consumables with no named job.
   **Ask: one default, or per job?**

9. **Supermarket cleaning products.** 88 lines, CLP 2.19M, split `Utiles de
   oficina` (39) vs `Detergentes e higenizantes` (29). Detergent, chlorine,
   toilet paper. **Ask: does `Detergentes e higenizantes` mean milking-plant
   hygiene only, with household cleaning going to office supplies?** The name
   does not say, and the split is currently arbitrary.

10. **Oil, fuel and air filters.** 15 lines, CLP 650K, across 5 accounts.
    Small, but recurring forever. **Ask: does a filter follow the machine it
    fits, or is there one consumables account?**

11. **GEA technician hours — does the technician's initials change the account?**
    36 lines, CLP 12.8M, 27 in review. GEA Farm Technologies invoice
    `HORA TECNICA AM`, `JM`, `FA`, `CAL`, `LH` — the letters are the
    technician. The client labelled **`HORA TECNICA AM` → `EXP-10.1` Mantencion
    Sala** as a row-level example, and that is the only one he ever ruled on.
    Our own silver audit then labelled `LH` as `EXP-13.1` Mantencion Maquinaria
    and `JM` as `EXP-10.1`, so gold now contradicts itself on the same supplier.
    **Ask: do all GEA technician hours go to Mantencion Sala regardless of who
    attended, or does the work type vary?** Until he answers, all 27 stay in
    review — extending his single AM example to the other four initials was
    tried and reverted on 2026-08-18.

12. **Ryegrass variety — perennial or short rotation?** 9 lines, CLP 5.28M.
    `SEMILLA BALLICA TAMA` is auto-accepted into `EXP-8.1 Pradera Perenne`, but
    TAMA is an Italian/annual ryegrass, which is short-rotation — and
    `EXP-8.2 Pradera Rotacion Corta` exists and holds `BALLICA FORGE` and
    `PASTURE PACK KABUL`. The client's only seed rule is `SEMILLA BALLICA COLUN
    4*5*25 kg` → `EXP-8.1`; no rule distinguishes varieties. **Ask: which
    ryegrass varieties count as perennial and which as short rotation?** Found
    by the 2026-08-18 silver audit; not changed, because it is his agronomy.

13. **Copper sulphate — agrochemical, or field expense?** 6 lines, CLP 1.07M.
    The client's own rule files `SULFATO DE COBRE X 25 KL.` under `EXP-16.2
    Otros Gastos Campo` (3 lines auto-accepted). But the same product from
    another supplier reads as `EXP-7.0 AGROQUIMICOS` to the model, and copper
    sulphate really is a fungicide — and on a dairy it is also the standard hoof
    footbath. **Ask: where does copper sulphate go?** The 3 rows on his rule stay
    auto-accepted because only he can overturn his own decision (D-030); the
    other 3 are held in review until he answers. Raised by Afaq 2026-08-18.

**Chainsaw consumables are already answered and need no question** — the
product lookup files `LIMA MOTOSIERRA` under `EXP-16.2 Otros Gastos Campo`, so
its 11 siblings were moved to match. Recorded here so nobody re-asks.

**Settled policy from his reply — not open questions, do not re-ask:**

- **Untagged petrol goes to review, permanently.** Asked for a default rule for
  the 77 lines (CLP 4,497,441) on invoices carrying no `<Patente>`; he answered
  *"Our team to place."* That **is** the rule: no default exists, their team
  places them. Every future fill-up at a station that omits `<Patente>` lands in
  review by design. This is intended behaviour, not an unanswered question.
- **The milking-shed rule is given.** *"Predio Lecheria are for leases that have
  a milk shed, Arriendo otros predios for leases for younger animals that are not
  milking."* Pelleco → `EXP-15.7`. `EXP-15.6` stays empty until a lease that has
  a milking shed actually invoices; only then does the property need naming.

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
> Treat the rest of that file as unverified. See "Still open" #3.

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
- Side work on the barn — now tracked in "Still open" #2 above.

**Still unasked, and the highest-value item available:**

- **July 2026 onward invoices.** They offered them as training data. Need volume,
  format, and whether the labels are client-confirmed or uncorrected model
  output. Dropped from the 2026-08-17 email twice; ~3,529 review rows are
  undertrained rather than ambiguous, so this is the single biggest lever.
