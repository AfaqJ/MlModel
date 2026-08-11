"""Conservative, audited invoice-line filters.

An explicit zero amount/price is necessary but never sufficient for removal.
Only known document scaffolding and note patterns observed in the local client
XML audit are filtered. Free, bonified, warranty, correction, and uncertain
goods/services are retained.
"""
from __future__ import annotations

import html
import re
import unicodedata
from decimal import Decimal, InvalidOperation


SEPARATOR_RE = re.compile(r"^[-_=\.\s]{4,}$")
NUMERIC_ONLY_RE = re.compile(r"^[\d\s.,/\-]+$")
VEHICLE_WORK_ORDER_RE = re.compile(r"^ford\b.*\b\d{1,2}\s+\d{2}\s+\d{4}\b")
VEHICLE_METADATA_RE = re.compile(
    r"^(?:ano|capacidad de carga|chasis|cilindrada|color|condicion vehiculo|"
    r"marca|modelo|motor|patente|peso bruto vehicular|tipo combustible|"
    r"traccion|transmision)\b"
)


def _normalize(value: str | None) -> str:
    # Some supplier XML double-escapes HTML entities (for example `&#45;`).
    value = html.unescape(html.unescape((value or "").lower()))
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _number(value: int | float | str | Decimal | None) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value).strip().replace(",", "."))
    except InvalidOperation:
        return None


def has_explicit_zero_value(
    *,
    amount: int | float | str | Decimal | None,
    unit_price: int | float | str | Decimal | None,
) -> bool:
    parsed_amount = _number(amount)
    parsed_price = _number(unit_price)
    return (parsed_amount is not None and parsed_amount == 0) or (
        parsed_price is not None and parsed_price == 0
    )


def zero_value_junk_reason(
    item_text: str | None,
    description: str | None,
    *,
    amount: int | float | str | Decimal | None,
    unit_price: int | float | str | Decimal | None = None,
) -> str | None:
    """Return an audited removal reason, or None when the line must be kept.

    These patterns were manually checked against all 497 explicit-zero lines
    (254 distinct text groups) in the authoritative local XML folders.
    """
    if not has_explicit_zero_value(amount=amount, unit_price=unit_price):
        return None

    raw_item = (item_text or "").strip()
    raw_description = (description or "").strip()
    item = _normalize(raw_item)
    description_norm = _normalize(raw_description)
    combined = _normalize(" ".join(part for part in (raw_item, raw_description) if part))

    if SEPARATOR_RE.fullmatch(raw_item) or SEPARATOR_RE.fullmatch(raw_description):
        return "separator"
    if not combined:
        return "empty_zero_line"
    if NUMERIC_ONLY_RE.fullmatch(raw_item):
        return "printed_numeric_summary"
    if item.startswith("codigo descripcion"):
        return "printed_column_header"
    if "valores netos con descto incluido" in item:
        return "printed_totals_header"
    if item.startswith("mo elec mec") or item == "repuestos servicios":
        return "printed_service_columns"
    if item.startswith("sco mo") and description_norm.startswith("a sco mo"):
        return "workshop_request_note"
    if VEHICLE_WORK_ORDER_RE.match(item):
        return "vehicle_work_order_metadata"
    if VEHICLE_METADATA_RE.match(item):
        return "vehicle_metadata"

    fixed_prefix_reasons = (
        ("recuerde programar su proxima visita", "workshop_reminder"),
        ("taller ford osorno", "workshop_footer"),
        ("vim undefined", "broken_template_field"),
        ("rutcobranza", "billing_reference"),
        ("comentarios", "comments_header"),
        ("observaciones", "observations_note"),
        ("entrega inmediata salvo venta previa", "delivery_payment_note"),
        ("fecha guia", "fuel_delivery_reference"),
        ("oc ", "purchase_order_reference"),
        ("segun guias", "delivery_reference"),
        ("leasing ", "duplicate_lease_installment_note"),
    )
    for prefix, reason in fixed_prefix_reasons:
        if item.startswith(prefix):
            return reason
    if item == "total" and description_norm.startswith("gasolina"):
        return "zero_fuel_summary"
    return None
