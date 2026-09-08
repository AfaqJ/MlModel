"""Checks for the DTE reader.

Each test pins one thing that was measured against the real corpus, so a later
"tidy-up" that reintroduces the bug fails here instead of in production.
"""

from __future__ import annotations

import glob

import pytest

from yunt import dte


def wrap(detalle: str, *, rut: str = "76000000-1", extra: str = "") -> bytes:
    xml = f"""<DTE xmlns="http://www.sii.cl/SiiDte" version="1.0"><Documento ID="T33F1">
      <Encabezado>
        <IdDoc><TipoDTE>33</TipoDTE><Folio>1</Folio><FchEmis>2026-08-01</FchEmis></IdDoc>
        <Emisor><RUTEmisor>{rut}</RUTEmisor><RznSoc>PRUEBA</RznSoc>
                <GiroEmis>COM. EQ.ORDEÑA</GiroEmis></Emisor>
        <Receptor><RUTRecep>96685810-9</RUTRecep><RznSocRecep>ANTILLANCA SPA</RznSocRecep></Receptor>
        <Totales><MntNeto>100</MntNeto><IVA>19</IVA><MntTotal>119</MntTotal></Totales>
      </Encabezado>
      <Detalle>{detalle}</Detalle>{extra}
    </Documento></DTE>"""
    # The real files are ISO-8859-1 and carry no encoding declaration.
    return xml.encode("latin-1")


def one(detalle: str, **kw):
    return dte.parse(wrap(detalle, **kw), "COMPRAS")[0].lines[0]


def test_latin1_without_a_declaration_is_decoded_not_mangled():
    doc = dte.parse(wrap("<NmbItem>X</NmbItem><MontoItem>1</MontoItem>"), "COMPRAS")[0]
    assert "ORDEÑA" in doc.seller_giro          # the enye survived


def test_dot_is_the_decimal_point_not_a_thousands_separator():
    line = one("<NmbItem>X</NmbItem><QtyItem>1.046</QtyItem>"
               "<PrcItem>7160</PrcItem><MontoItem>7489</MontoItem>")
    assert line.quantity == pytest.approx(1.046)     # not 1046
    assert line.reconciles


def test_discount_amount_is_subtracted_and_the_percentage_is_not():
    # 100 x 7 = 700, less 5% would be 665; the file's own MontoItem says 760 is
    # wrong and 700 is right, so the percentage must not be applied twice.
    line = one("<NmbItem>X</NmbItem><QtyItem>100</QtyItem><PrcItem>7</PrcItem>"
               "<DescuentoPct>5</DescuentoPct><MontoItem>700</MontoItem>")
    assert line.discount_pct == 5.0 and line.reconciles


def test_recargo_is_stored_but_never_added_to_the_line():
    # The real shape: RecargoMonto is a verbatim copy of MontoItem on all 30
    # lines that carry it. Adding it would double the line.
    line = one("<NmbItem>X</NmbItem><QtyItem>1</QtyItem><PrcItem>151034</PrcItem>"
               "<DescuentoMonto>9</DescuentoMonto><RecargoMonto>151025</RecargoMonto>"
               "<MontoItem>151025</MontoItem>")
    assert line.recargo_amount == 151025.0
    assert line.reconciles


FUEL = "81094100-6"   # written with the hyphen; the parser normalises it


def test_a_scaled_line_is_rescaled():
    line = one("<NmbItem>GASOLINA 93</NmbItem><QtyItem>400000.0</QtyItem>"
               "<PrcItem>7121500</PrcItem><UnmdItem>L</UnmdItem><MontoItem>28486</MontoItem>",
               rut=FUEL)
    assert line.quantity == pytest.approx(40.0)      # litres, not 400,000
    assert line.unit_price == pytest.approx(712.15)
    assert line.reconciles


def test_an_unscaled_line_from_the_same_supplier_is_left_alone():
    # The same supplier writes plain values on other lines. Scaling per supplier
    # rather than per line broke 2,196 of these.
    line = one("<NmbItem>GASOLINA 93</NmbItem><QtyItem>60</QtyItem>"
               "<PrcItem>788.80</PrcItem><MontoItem>47328</MontoItem>", rut=FUEL)
    assert line.quantity == pytest.approx(60.0)
    assert line.reconciles


def test_a_line_that_cannot_be_reconciled_is_flagged_and_left_untouched():
    line = one("<NmbItem>X</NmbItem><QtyItem>1</QtyItem>"
               "<PrcItem>840000</PrcItem><MontoItem>798889</MontoItem>")
    assert not line.reconciles
    assert line.quantity == 1.0 and line.amount == 798889.0   # never adjusted


def test_references_are_captured():
    ref = ("<Referencia><NroLinRef>1</NroLinRef><TpoDocRef>33</TpoDocRef>"
           "<FolioRef>555</FolioRef><CodRef>1</CodRef>"
           "<RazonRef>ANULA</RazonRef></Referencia>")
    doc = dte.parse(wrap("<NmbItem>X</NmbItem><MontoItem>1</MontoItem>", extra=ref), "COMPRAS")[0]
    assert doc.references[0].folio == "555" and doc.references[0].code == "1"


def test_every_detalle_becomes_a_line_or_a_recorded_drop():
    """No silent loss. 357 lines went missing in the original load unexplained."""
    files = sorted(glob.glob("Data/Raw_Data/dte_96685810_COMPRAS/202508/*.xml"))
    if not files:
        pytest.skip("raw corpus not present")
    raw = emitted = dropped = bad = 0
    for path in files:
        for doc in dte.parse(open(path, "rb").read(), "COMPRAS"):
            raw += doc.raw_detalle_count
            emitted += len(doc.lines)
            dropped += len(doc.dropped)
            bad += sum(1 for line in doc.lines if not line.reconciles)
    assert raw == emitted + dropped
    # Regression guard on the flag rate. It was 10.9% before the decimal,
    # discount, recargo and scaling fixes; anything near that means one regressed.
    assert bad / emitted < 0.02, f"{bad}/{emitted} lines fail to reconcile"
