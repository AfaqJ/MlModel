"""Reading SII DTE XML into invoice and line records.

This is the file that has to be right, so the reasoning is written down.

Encoding
--------
The DTE files carry NO `encoding=` declaration, and the XML spec says a parser
must then assume UTF-8. These files are ISO-8859-1. A standards-compliant
parser therefore reads every accented character wrong — `ORDEÑA` stores the enye
as the single byte 0xD1, which is Latin-1. So: try UTF-8, fall back to latin-1.

Numbers
-------
`QtyItem` and `PrcItem` use `.` as the DECIMAL point, not a thousands separator.
Measured over 9,647 lines of the real corpus: `qty * price == monto` holds for
89.4% reading `.` as a decimal point and only 35.3% reading it as a thousands
separator (and that 35.3% is just the integer quantities, where the reading
makes no difference). Never strip the dot.

Discounts
---------
`MontoItem = QtyItem * PrcItem - DescuentoMonto`.
`DescuentoPct` is informational and must NOT also be applied: over the 959
discounted lines, subtracting `DescuentoMonto` alone reconciles 99.5%, while
applying both the percentage and the amount reconciles 15%.

`RecargoMonto` is NOT in that formula, and leaving it out is a measurement, not
an oversight. It appears on exactly 30 lines in the whole corpus, all from one
supplier, and on every one of them it is a verbatim copy of `MontoItem` rather
than a surcharge. Adding it double-counts the line. It is still stored, because
a future supplier may fill it in correctly.

Supplier scaling
----------------
One supplier sometimes writes quantity and unit price as fixed-point integers
scaled by 10^4 — and sometimes writes them plainly, on lines of the same invoice.
So the scale is decided PER LINE by arithmetic, never per supplier: a line is
rescaled only when rescaling makes it reconcile, and the supplier table supplies
only the split between the two factors (which arithmetic cannot recover, since
only their product is determined). Anything that still fails to reconcile is
left exactly as the file had it and flagged for a person.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

# --- Supplier-specific numeric scaling -------------------------------------
#
# COOPERATIVA AGRICOLA Y LECHERA DE LA UNION emits `QtyItem` and `PrcItem`
# multiplied by 10,000. Arithmetic alone only pins the PRODUCT of the two
# scales (10^8); the split is settled by the invoice itself:
#
#     QtyItem 400000.0  PrcItem 7121500  MontoItem 28486  UnmdItem "L"
#     -> 40.0 litres at CLP 712.15/L net = CLP 28,486
#
# and that invoice's own Totales carry MntNeto 28,486 + IVA 5,412 + fuel tax
# 18,102 = MntTotal 52,000, i.e. about CLP 1,300 per litre at the pump, which is
# the right order for Chilean petrol. Reading the quantity raw is what produced
# the "62,648,532 litres of GASOLINA 93" figure.
SCALED_SUPPLIERS: dict[str, tuple[float, float]] = {
    # seller RUT, normalised (no hyphen): (quantity divisor, unit price divisor)
    "810941006": (10_000.0, 10_000.0),
}

TOLERANCE_FLOOR = 1.0
TOLERANCE_PCT = 0.01


def _reconciles(quantity: float, unit_price: float, discount: float, amount: float) -> bool:
    expected = quantity * unit_price - discount
    return abs(expected - amount) <= max(TOLERANCE_FLOOR, abs(amount) * TOLERANCE_PCT)


def _rescale(
    quantity: float | None,
    unit_price: float | None,
    discount: float,
    amount: float,
    seller_rut: str,
) -> tuple[float | None, float | None, bool, bool]:
    """Return (quantity, unit_price, was_rescaled, reconciles).

    The file's own arithmetic decides whether a line needs rescaling. We only
    apply the divisors when doing so turns a line that did not reconcile into
    one that does, so a wrong entry in SCALED_SUPPLIERS cannot quietly corrupt
    lines that were already correct.
    """
    if quantity is None or unit_price is None:
        return quantity, unit_price, False, True
    if _reconciles(quantity, unit_price, discount, amount):
        return quantity, unit_price, False, True

    split = SCALED_SUPPLIERS.get(seller_rut)
    if split:
        q, p = quantity / split[0], unit_price / split[1]
        if _reconciles(q, p, discount, amount):
            return q, p, True, True

    # Left exactly as the file had it. `amount` is the authoritative figure and
    # is never adjusted; the line is flagged so a person looks at it.
    return quantity, unit_price, False, False


@dataclass
class Line:
    line_number: int
    item_text: str
    description: str
    item_codes: str
    quantity: float | None
    unit: str
    unit_price: float | None
    amount: float
    discount_amount: float
    discount_pct: float
    recargo_amount: float
    tax_exempt: bool
    additional_tax_code: str
    reconciles: bool


@dataclass
class Reference:
    line_number: int
    document_type: str
    folio: str
    date: str
    code: str
    reason: str


@dataclass
class Document:
    document_type: str
    folio: str
    invoice_date: str
    due_date: str
    transaction_type: str
    seller_rut: str
    seller_name: str
    seller_giro: str
    seller_address: str
    seller_commune: str
    seller_city: str
    buyer_rut: str
    buyer_name: str
    buyer_giro: str
    buyer_address: str
    buyer_commune: str
    buyer_city: str
    net_amount: float
    exempt_amount: float
    iva_amount: float
    total_amount: float
    payment_form: str
    receiver_internal_code: str
    lines: list[Line] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)
    # Reconciliation: what the file held vs what we emit, with typed reasons.
    raw_detalle_count: int = 0
    rescaled_lines: int = 0
    dropped: list[dict] = field(default_factory=list)

    @property
    def key(self) -> tuple[str, str, str]:
        """Identity for duplicate detection: issuer, document type, folio."""
        return (self.seller_rut, self.document_type, self.folio)


def decode(raw: bytes) -> str:
    """UTF-8 first, latin-1 second. See the module docstring."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def normalise_rut(rut: str) -> str:
    """The shape Supabase stores: no hyphen, uppercase check digit.

    Measured across all three tables holding a RUT — invoices.seller_rut,
    invoices.buyer_rut and companies.rut — every one of 11,000+ values is stored
    this way. The DTE writes `11920610-3`; the database holds `119206103`.
    Getting this wrong makes every document look new, which is how a duplicate
    load starts.
    """
    return (rut or "").replace("-", "").replace(".", "").strip().upper()


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _child(node: ET.Element | None, name: str) -> ET.Element | None:
    if node is None:
        return None
    for kid in list(node):
        if _local(kid.tag) == name:
            return kid
    return None


def _deep(node: ET.Element | None, name: str) -> ET.Element | None:
    if node is None:
        return None
    for kid in node.iter():
        if _local(kid.tag) == name:
            return kid
    return None


def _all(node: ET.Element | None, name: str) -> list[ET.Element]:
    return [k for k in node.iter() if _local(k.tag) == name] if node is not None else []


def _text(node: ET.Element | None) -> str:
    return re.sub(r"\s+", " ", (node.text or "")).strip() if node is not None else ""


def _field(node: ET.Element | None, name: str) -> str:
    return _text(_child(node, name))


def _number(value: str) -> float | None:
    """Parse a DTE numeric field. `.` is the decimal point; never a separator."""
    value = (value or "").strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse(raw: bytes, transaction_type: str) -> list[Document]:
    """Parse one file. Returns every DTE it contains — an envelope may hold many."""
    try:
        root = ET.fromstring(decode(raw).encode("utf-8"))
    except ET.ParseError as exc:
        raise ValueError(f"not parseable as XML: {exc}") from exc

    dtes = _all(root, "DTE") or ([root] if _local(root.tag) == "DTE" else [])
    if not dtes:
        # Some files are a bare <Documento> with no <DTE> wrapper.
        dtes = [root] if _body(root) is not None else []

    documents = []
    for dte in dtes:
        doc = _parse_documento(dte, transaction_type)
        if doc is not None:
            documents.append(doc)
    return documents


def _body(dte: ET.Element) -> ET.Element | None:
    """The document body. Type 43 (liquidacion factura) names it <Liquidacion>;
    everything else names it <Documento>. Same structure inside, and the 29 of
    these in the corpus are worth CLP 292 million, so they must not be skipped.
    """
    for tag in ("Documento", "Liquidacion", "Exportaciones"):
        found = _deep(dte, tag)
        if found is not None:
            return found
    return None


def _parse_documento(dte: ET.Element, transaction_type: str) -> Document | None:
    documento = _body(dte)
    if documento is None:
        return None
    head = _child(documento, "Encabezado")
    if head is None:
        return None

    id_doc = _child(head, "IdDoc")
    emisor = _child(head, "Emisor")
    receptor = _child(head, "Receptor")
    totales = _child(head, "Totales")

    seller_rut = normalise_rut(_field(emisor, "RUTEmisor"))
    doc = Document(
        document_type=_field(id_doc, "TipoDTE"),
        folio=_field(id_doc, "Folio"),
        invoice_date=_field(id_doc, "FchEmis"),
        due_date=_field(id_doc, "FchVenc"),
        transaction_type=transaction_type,
        seller_rut=seller_rut,
        seller_name=_field(emisor, "RznSoc"),
        seller_giro=_field(emisor, "GiroEmis"),
        seller_address=_field(emisor, "DirOrigen"),
        seller_commune=_field(emisor, "CmnaOrigen"),
        seller_city=_field(emisor, "CiudadOrigen"),
        buyer_rut=normalise_rut(_field(receptor, "RUTRecep")),
        buyer_name=_field(receptor, "RznSocRecep"),
        buyer_giro=_field(receptor, "GiroRecep"),
        buyer_address=_field(receptor, "DirRecep"),
        buyer_commune=_field(receptor, "CmnaRecep"),
        buyer_city=_field(receptor, "CiudadRecep"),
        net_amount=_number(_field(totales, "MntNeto")) or 0.0,
        exempt_amount=_number(_field(totales, "MntExe")) or 0.0,
        iva_amount=_number(_field(totales, "IVA")) or 0.0,
        total_amount=_number(_field(totales, "MntTotal")) or 0.0,
        payment_form=_field(id_doc, "FmaPago"),
        receiver_internal_code=_field(receptor, "CdgIntRecep"),
    )

    detalles = _all(documento, "Detalle")
    doc.raw_detalle_count = len(detalles)

    for index, det in enumerate(detalles, start=1):
        item_text = _field(det, "NmbItem")
        amount = _number(_field(det, "MontoItem"))
        if amount is None and not item_text:
            # Neither a name nor a value: a filler row, not a line item. Recorded
            # rather than silently dropped — a silent drop is what left 357 lines
            # unaccounted for in the original load.
            doc.dropped.append({"line": index, "reason": "empty_detalle"})
            continue

        discount_amount = _number(_field(det, "DescuentoMonto")) or 0.0
        recargo_amount = _number(_field(det, "RecargoMonto")) or 0.0
        amount = amount or 0.0

        quantity, unit_price, rescaled, reconciles = _rescale(
            _number(_field(det, "QtyItem")),
            _number(_field(det, "PrcItem")),
            discount_amount,
            amount,
            seller_rut,
        )
        if rescaled:
            doc.rescaled_lines += 1

        codes = _child(det, "CdgItem")
        doc.lines.append(
            Line(
                line_number=int(_field(det, "NroLinDet") or index),
                item_text=item_text,
                description=_field(det, "DscItem"),
                item_codes=_field(codes, "VlrCodigo"),
                quantity=quantity,
                unit=_field(det, "UnmdItem"),
                unit_price=unit_price,
                amount=amount,
                discount_amount=discount_amount,
                discount_pct=_number(_field(det, "DescuentoPct")) or 0.0,
                recargo_amount=recargo_amount,
                tax_exempt=_field(det, "IndExe") == "1",
                additional_tax_code=_field(det, "CodImpAdic"),
                reconciles=reconciles,
            )
        )

    for ref in _all(documento, "Referencia"):
        doc.references.append(
            Reference(
                line_number=int(_field(ref, "NroLinRef") or 0),
                document_type=_field(ref, "TpoDocRef"),
                folio=_field(ref, "FolioRef"),
                date=_field(ref, "FchRef"),
                code=_field(ref, "CodRef"),
                reason=_field(ref, "RazonRef"),
            )
        )
    return doc
