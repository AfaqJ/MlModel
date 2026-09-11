# The Test 1 archive

`yunt_test_6.zip` — 6 documents, 7 lines, 4,330 bytes. Supplier RUT 77123456-7, folios 999101-999106, all COMPRAS.

Undo with `python scripts/90_yunt_live_test_undo.py --apply`, which is anchored on that RUT alone.

## Folio 999101 — 2 line(s)

- `Petroleo Diesel Ultra` — 500 x 753 = stated 376,500
- `Petroleo Diesel Ultra` — 300 x 753 = stated 225,900

Control. product_lookup settles both lines at EXP-11.3 and auto-accepts. Nothing should be said about this document at all.

## Folio 999102 — 1 line(s)

- `Pago Arriendo Operacion:` — 1 x 2,500,000 = stated 2,500,000

Proposal A. 17 human-confirmed lines say EXP-15.8 and the classifier disagrees, so the line lands in review with a real answer waiting for it. This is the proposal to approve, then undo, in steps 5-7.

## Folio 999103 — 1 line(s)

- `Asesoria Contable` — 1 x 450,000 = stated 450,000

Proposal B. 14 human-confirmed lines say ADM-1.8 and the classifier disagrees. A second proposal, so a partial approval can be tested: approve A only, and B must be left exactly as it was.

## Folio 999104 — 1 line(s)

- `Control De Roedores` — 1 x 120,000 = stated 120,000

Proposal C, and the clearest one. 80 human-confirmed lines say EXP-7.0, with no second opinion anywhere in the corpus. If the Yunt gets this one wrong the precedent search is not working, whatever the other two say.

## Folio 999105 — 1 line(s)

- `Nitrogeno liquido` — 40 x 9,000 = stated 412,000

line_arithmetic. 40 x 9,000 is 360,000 and the line charges 412,000. Expect a data-quality finding that REPORTS it. Under D-070 the Yunt must never offer to correct the amount; it may still propose the category, which 9 human-confirmed lines put at EXP-3.1.

## Folio 999106 — 1 line(s)

- `DETALLE` — 1 x 89,000 = stated 89,000

junk_item_name, and the only wording here that is deliberately NOT in item_catalog. The line is flagged, and being flagged it cannot auto-accept. Expect the Yunt to ask what it is rather than guess.
