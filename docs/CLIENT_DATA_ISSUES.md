# Data issues found in Antillanca's invoices

Things wrong in the source documents themselves, not in our processing. Logged
here so they can be raised with the client, and so a figure that looks wrong on
a screen can be traced to the invoice that caused it rather than blamed on the
system.

**Every entry needs:** what the document says, why it is wrong, how many are
affected, what it costs, and whether we compensate for it or only report it.

Written to be shown to the client: facts and figures, no internal process.

---

## 1. A meter reading recorded in the amount column

**What happens.** Some electricity invoices put a consumption reading in the
line amount field instead of a sum of money.

Invoice from CIA ELECTRICA OSORNO, folio 1417326:

| | |
|---|---|
| Invoice header | net CLP 1,060 · IVA CLP 201 · **total CLP 1,261** |
| Line: Administración del Servicio | CLP 1,060 |
| Line: Cargo mensual por demanda máxima de Potencia | **CLP 1,011,311** |

The invoice is worth CLP 1,261. One of its lines claims a million.

**Scale.** 387 of 4,449 purchase documents have line amounts that do not sum to
their own header total. Across the whole set the lines overstate the headers by
**CLP 21,189,814**, about 0.5%.

Concentrated in three issuers:

| Overstatement | Documents | Issuer |
|---|---|---|
| CLP 7,362,798 | 12 | Entel PCS Telecomunicaciones |
| CLP 6,531,297 | 26 | CIA Electrica Osorno |
| CLP 2,098,739 | 1 | Enrique Ricardo Schmidt Rojas |
| CLP 1,625,903 | 181 | Doris Ivonne Castillo Kanter |

**What it affects.** Invoice-level totals are unaffected — those come from the
header, which is correct. Spend broken down **by category** is computed from the
lines, so it is currently overstated by that amount.

**What we do.** The header is authoritative, so nothing is lost. Going forward
each document carries a reconciliation result, and one whose lines disagree with
its own header is marked rather than silently trusted. The 387 already stored
need a decision.

**To ask the client:** whether these issuers can be asked to correct it, or
whether we should treat the header as final and mark the lines.

---

## 2. Supermarket offer pricing, with no discount recorded

**What happens.** A promotional price is charged, but the discount is not
recorded in the discount field — the supplier simply writes the final amount.

From COMERCIAL AMAR HERMANOS:

| Item | Quantity x price | Amount charged |
|---|---|---|
| NESCAFE TRADICION TARRO | 2 x CLP 8,990 = 17,980 | **CLP 12,000** |
| GRETEL PIE DE LIMON | 2 x CLP 1,390 = 2,780 | **CLP 1,598** |
| AZUCAR IANSA 900GRS | 3 x CLP 1,390 = 4,170 | **CLP 3,000** |

**Scale.** 50 lines of 10,620, about 0.5%. Twenty-seven are offers of this kind;
the rest are unit prices rounded to whole pesos at hardware suppliers.

**What it affects.** Nothing financial — the amount charged is correct and is
what we store. It only means the unit price on those lines cannot be used to
work out what an item cost per unit.

**What we do.** Report it. There is nothing to correct: the supplier charged
what they charged.

---

## 3. A surcharge column filled with a copy of the line total

**What happens.** `RecargoMonto` is a surcharge field. On every line that
carries one, it holds the same number as the line total rather than a surcharge.

**Scale.** 30 lines, all from Salinas y Fabres.

**What it affects.** Nothing, now. Anything that added that column to the line
total would double those lines.

**What we do.** The column is stored but never added.

---

## 4. Quantity and unit price scaled by ten thousand

**What happens.** Some fuel invoice lines record quantity and unit price as
whole numbers scaled by 10,000, and other lines on the same invoice record them
plainly.

From COOPERATIVA AGRICOLA Y LECHERA DE LA UNION:

| Field | As written | Actual |
|---|---|---|
| Quantity | 400000.0 | 40 litres |
| Unit price | 7121500 | CLP 712.15 per litre |
| Amount | 28486 | CLP 28,486 |

The invoice's own totals confirm it: net 28,486 + IVA 5,412 + fuel tax 18,102 =
CLP 52,000, about CLP 1,300 per litre at the pump.

**Scale.** 158 lines.

**What it affects.** Read as written, fuel purchases totalled 62,648,532 litres.

**What we do.** Corrected automatically, and only where the line's own
arithmetic proves the correction is right. Amounts are never adjusted.

---

## 5. Credit notes recorded as positive amounts

**What happens.** 103 credit notes (document type 61) are stored with positive
amounts, so a purchase and its cancellation both count as spending.

**Scale.** 103 documents, CLP 87,885,532.

**What it affects.** Totals that include credit notes are overstated by up to
twice that figure, depending on the period.

**What we do.** Not yet resolved. The block naming which document each credit
note cancels is now captured for new invoices.

---

## 6. Liquidación facturas that may duplicate a sale

**What happens.** 29 documents of type 43 (liquidación factura), all from Feria
Ganaderos Osorno, CLP 292,085,987.

**What it affects.** If the underlying sale is also present as a type 33, these
are counted twice.

**To ask the client:** whether these represent separate transactions or the
settlement of sales already invoiced.
