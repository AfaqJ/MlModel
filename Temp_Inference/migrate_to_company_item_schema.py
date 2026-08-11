#!/usr/bin/env python3
"""Backfill the company + item catalog schema from a safe local snapshot.

This script does not run ML inference. It reads the already-labeled normalized
tables from a local snapshot, parses raw XML again for the extra invoice and
line-item fields, then writes the new production shape:

  categories, companies, item_catalog, invoices, invoice_items
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent

RAW_DIRS = {
    "COMPRAS": ROOT / "data" / "Raw_Data" / "dte_96685810_COMPRAS",
    "VENTAS": ROOT / "data" / "Raw_Data" / "dte_96685810_VENTAS",
}

DEFAULT_SNAPSHOT_DIR = HERE / "snapshots" / "normalized_before_company_item_split"

CATEGORIES_TABLE = "categories"
COMPANIES_TABLE = "companies"
ITEM_CATALOG_TABLE = "item_catalog"
INVOICES_TABLE = "invoices"
INVOICE_ITEMS_TABLE = "invoice_items"

GENERIC_ITEM_NAMES = {
    "DETALLE",
    "FECHA-GUÍA",
    "FECHA-GUIA",
    "ITEM",
    "PRODUCTO",
    "SERVICIO",
    "SERVICIOS",
    "TOTAL",
}


@dataclass(frozen=True)
class XmlInvoice:
    invoice_key: str
    transaction_type: str
    invoice_folio: str
    document_type: str
    invoice_date: str
    seller_rut: str
    seller_name: str
    seller_giro: str | None
    seller_address: str | None
    seller_commune: str | None
    seller_city: str | None
    buyer_rut: str
    buyer_name: str
    buyer_giro: str | None
    buyer_address: str | None
    buyer_commune: str | None
    buyer_city: str | None
    receiver_internal_code: str | None
    net_amount: int | float | None
    iva_amount: int | float | None
    exempt_amount: int | float | None
    total_amount: int | float | None
    due_date: str | None
    payment_form: str | None
    source_file: str


@dataclass(frozen=True)
class XmlLine:
    line_key: str
    invoice_key: str
    invoice_line_number: int
    item_text: str
    description: str | None
    item_codes: list[dict[str, str]]
    meter_code: str | None
    quantity: int | float | None
    unit: str | None
    unit_price: int | float | None
    amount: int | float | None
    discount_pct: int | float | None
    discount_amount: int | float | None
    recargo_amount: int | float | None
    tax_exempt: bool
    additional_tax_code: str | None


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def env_value(key: str, file_values: dict[str, str], default: str | None = None) -> str | None:
    return os.environ.get(key) or file_values.get(key) or default


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def iter_named(element: ET.Element, name: str):
    for child in element.iter():
        if local_name(child.tag) == name:
            yield child


def find_named(element: ET.Element | None, name: str) -> ET.Element | None:
    if element is None:
        return None
    for child in list(element):
        if local_name(child.tag) == name:
            return child
    return None


def find_deep_named(element: ET.Element | None, name: str) -> ET.Element | None:
    if element is None:
        return None
    for child in element.iter():
        if local_name(child.tag) == name:
            return child
    return None


def clean_text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return re.sub(r"\s+", " ", (element.text or "")).strip()


def clean_value(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def none_if_blank(value: str | None) -> str | None:
    value = clean_value(value)
    return value or None


def normalize_rut(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())


def parse_number(value: str | None) -> int | float | None:
    value = clean_value(value).replace(",", ".")
    if not value:
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    if number.is_integer():
        return int(number)
    return number


def parse_date(value: str | None) -> str | None:
    value = clean_value(value)
    if not value:
        return None
    return value if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) else None


def invoice_key(seller_rut: str, document_type: str, invoice_folio: str) -> str:
    return f"{seller_rut}|{document_type}|{invoice_folio}"


def line_key(invoice_key_value: str, invoice_line_number: int) -> str:
    return f"{invoice_key_value}|{invoice_line_number}"


def most_common_nonblank(values: Counter[str]) -> str | None:
    for value, _count in values.most_common():
        if clean_value(value):
            return value
    return None


def is_generic_item_name(item_name: str) -> bool:
    return clean_value(item_name).upper() in GENERIC_ITEM_NAMES


def catalog_description(item_name: str, description: str | None) -> str:
    if is_generic_item_name(item_name):
        return clean_value(description)
    return ""


def remap_top3_categories(top3: list[dict[str, Any]], category_id_by_code: dict[str, str]) -> list[dict[str, Any]]:
    remapped: list[dict[str, Any]] = []
    for candidate in top3:
        code = clean_value(candidate.get("code"))
        remapped.append(
            {
                "categories_id": category_id_by_code.get(code),
                "code": code,
                "name": candidate.get("name"),
                "score": candidate.get("score"),
            }
        )
    return remapped


def extract_item_codes(detalle: ET.Element) -> list[dict[str, str]]:
    codes: list[dict[str, str]] = []
    for child in list(detalle):
        if local_name(child.tag) != "CdgItem":
            continue
        code_type = clean_text(find_named(child, "TpoCodigo"))
        code_value = clean_text(find_named(child, "VlrCodigo"))
        if code_type or code_value:
            codes.append({"type": code_type, "value": code_value})
    return codes


def parse_raw_xml() -> tuple[dict[str, XmlInvoice], dict[str, XmlLine], dict[str, int], list[dict[str, Any]]]:
    invoices_by_key: dict[str, XmlInvoice] = {}
    lines_by_key: dict[str, XmlLine] = {}
    stats = {
        "raw_xml_documents": 0,
        "raw_detail_lines": 0,
        "duplicate_invoice_keys": 0,
        "duplicate_line_keys": 0,
    }
    errors: list[dict[str, Any]] = []

    for transaction_type, raw_dir in RAW_DIRS.items():
        if not raw_dir.exists():
            errors.append({"path": str(raw_dir), "error": "raw_dir_missing"})
            continue
        for path in sorted(raw_dir.rglob("*.xml")):
            raw = path.read_bytes()
            try:
                xml_text = raw.decode("utf-8")
            except UnicodeDecodeError:
                xml_text = raw.decode("latin-1", errors="replace")
            try:
                root = ET.fromstring(xml_text.encode("utf-8"))
            except ET.ParseError as exc:
                errors.append({"path": str(path), "error": f"parse_error: {exc}"})
                continue

            for dte in iter_named(root, "DTE"):
                doc = find_deep_named(dte, "Documento")
                if doc is None:
                    continue
                stats["raw_xml_documents"] += 1

                encab = find_named(doc, "Encabezado")
                id_doc = find_named(encab, "IdDoc")
                emisor = find_named(encab, "Emisor")
                receptor = find_named(encab, "Receptor")
                totales = find_named(encab, "Totales")

                document_type = clean_text(find_named(id_doc, "TipoDTE"))
                folio = clean_text(find_named(id_doc, "Folio"))
                invoice_date = clean_text(find_named(id_doc, "FchEmis"))
                seller_rut = normalize_rut(clean_text(find_named(emisor, "RUTEmisor")))
                buyer_rut = normalize_rut(clean_text(find_named(receptor, "RUTRecep")))

                required = {
                    "document_type": document_type,
                    "invoice_folio": folio,
                    "invoice_date": invoice_date,
                    "seller_rut": seller_rut,
                    "buyer_rut": buyer_rut,
                }
                missing = [name for name, value in required.items() if not value]
                if missing:
                    errors.append(
                        {
                            "path": str(path),
                            "error": f"missing_invoice_fields: {','.join(missing)}",
                        }
                    )
                    continue

                key = invoice_key(seller_rut, document_type, folio)
                xml_invoice = XmlInvoice(
                    invoice_key=key,
                    transaction_type=transaction_type,
                    invoice_folio=folio,
                    document_type=document_type,
                    invoice_date=invoice_date,
                    seller_rut=seller_rut,
                    seller_name=clean_text(find_named(emisor, "RznSoc")),
                    seller_giro=none_if_blank(clean_text(find_named(emisor, "GiroEmis"))),
                    seller_address=none_if_blank(clean_text(find_named(emisor, "DirOrigen"))),
                    seller_commune=none_if_blank(clean_text(find_named(emisor, "CmnaOrigen"))),
                    seller_city=none_if_blank(clean_text(find_named(emisor, "CiudadOrigen"))),
                    buyer_rut=buyer_rut,
                    buyer_name=clean_text(find_named(receptor, "RznSocRecep")),
                    buyer_giro=none_if_blank(clean_text(find_named(receptor, "GiroRecep"))),
                    buyer_address=none_if_blank(clean_text(find_named(receptor, "DirRecep"))),
                    buyer_commune=none_if_blank(clean_text(find_named(receptor, "CmnaRecep"))),
                    buyer_city=none_if_blank(clean_text(find_named(receptor, "CiudadRecep"))),
                    receiver_internal_code=none_if_blank(clean_text(find_named(receptor, "CdgIntRecep"))),
                    net_amount=parse_number(clean_text(find_named(totales, "MntNeto"))),
                    iva_amount=parse_number(clean_text(find_named(totales, "IVA"))),
                    exempt_amount=parse_number(clean_text(find_named(totales, "MntExe"))),
                    total_amount=parse_number(clean_text(find_named(totales, "MntTotal"))),
                    due_date=parse_date(clean_text(find_named(id_doc, "FchVenc"))),
                    payment_form=none_if_blank(clean_text(find_named(id_doc, "FmaPago"))),
                    source_file=str(path.relative_to(ROOT)),
                )
                if key in invoices_by_key:
                    stats["duplicate_invoice_keys"] += 1
                else:
                    invoices_by_key[key] = xml_invoice

                for detalle in iter_named(doc, "Detalle"):
                    stats["raw_detail_lines"] += 1
                    line_number_text = clean_text(find_named(detalle, "NroLinDet"))
                    try:
                        invoice_line_number = int(line_number_text)
                    except ValueError:
                        errors.append(
                            {
                                "path": str(path),
                                "invoice_key": key,
                                "line_number": line_number_text,
                                "error": "invalid_or_missing_line_number",
                            }
                        )
                        continue
                    key_line = line_key(key, invoice_line_number)
                    xml_line = XmlLine(
                        line_key=key_line,
                        invoice_key=key,
                        invoice_line_number=invoice_line_number,
                        item_text=clean_text(find_named(detalle, "NmbItem")),
                        description=none_if_blank(clean_text(find_named(detalle, "DscItem"))),
                        item_codes=extract_item_codes(detalle),
                        meter_code=xml_invoice.receiver_internal_code,
                        quantity=parse_number(clean_text(find_named(detalle, "QtyItem"))),
                        unit=none_if_blank(clean_text(find_named(detalle, "UnmdItem"))),
                        unit_price=parse_number(clean_text(find_named(detalle, "PrcItem"))),
                        amount=parse_number(clean_text(find_named(detalle, "MontoItem"))),
                        discount_pct=parse_number(clean_text(find_named(detalle, "DescuentoPct"))),
                        discount_amount=parse_number(clean_text(find_named(detalle, "DescuentoMonto"))),
                        recargo_amount=parse_number(clean_text(find_named(detalle, "RecargoMonto"))),
                        tax_exempt=bool(parse_number(clean_text(find_named(detalle, "IndExe"))) or 0),
                        additional_tax_code=none_if_blank(clean_text(find_named(detalle, "CodImpAdic"))),
                    )
                    if key_line in lines_by_key:
                        stats["duplicate_line_keys"] += 1
                    else:
                        lines_by_key[key_line] = xml_line

    return invoices_by_key, lines_by_key, stats, errors


def load_snapshot(snapshot_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    required_files = {
        "categories": snapshot_dir / "taxonomy_categories.json",
        "invoices": snapshot_dir / "invoices.json",
        "invoice_items": snapshot_dir / "invoice_items.json",
    }
    missing = [str(path) for path in required_files.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing snapshot files: " + ", ".join(missing))

    old_category_snapshot_rows = json.loads(required_files["categories"].read_text(encoding="utf-8"))
    category_rows = [{"code": row["code"], "name": row["name"]} for row in old_category_snapshot_rows]
    invoice_rows = json.loads(required_files["invoices"].read_text(encoding="utf-8"))
    item_rows = json.loads(required_files["invoice_items"].read_text(encoding="utf-8"))
    return category_rows, invoice_rows, item_rows


def source_invoice_key(invoice: dict[str, Any]) -> str:
    return invoice_key(
        clean_value(invoice["seller_rut"]),
        clean_value(invoice["document_type"]),
        clean_value(invoice["invoice_folio"]),
    )


def build_companies(
    source_invoices: list[dict[str, Any]],
    xml_invoices_by_key: dict[str, XmlInvoice],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, Any]] = []

    for source_invoice in source_invoices:
        key = source_invoice_key(source_invoice)
        xml_invoice = xml_invoices_by_key.get(key)
        if xml_invoice is None:
            errors.append({"invoice_key": key, "error": "missing_xml_invoice"})
            continue

        if xml_invoice.transaction_type == "COMPRAS":
            rut = xml_invoice.seller_rut
            name = xml_invoice.seller_name
            giro = xml_invoice.seller_giro
            address = xml_invoice.seller_address
            commune = xml_invoice.seller_commune
            city = xml_invoice.seller_city
            seller_seen = True
            buyer_seen = False
        else:
            rut = xml_invoice.buyer_rut
            name = xml_invoice.buyer_name
            giro = xml_invoice.buyer_giro
            address = xml_invoice.buyer_address
            commune = xml_invoice.buyer_commune
            city = xml_invoice.buyer_city
            seller_seen = False
            buyer_seen = True

        if not rut:
            errors.append({"invoice_key": key, "error": "missing_other_party_rut"})
            continue
        group = grouped.setdefault(
            rut,
            {
                "rut": rut,
                "names": Counter(),
                "giros": Counter(),
                "addresses": Counter(),
                "communes": Counter(),
                "cities": Counter(),
                "is_seller": False,
                "is_buyer": False,
            },
        )
        group["names"][name] += 1
        if giro:
            group["giros"][giro] += 1
        if address:
            group["addresses"][address] += 1
        if commune:
            group["communes"][commune] += 1
        if city:
            group["cities"][city] += 1
        group["is_seller"] = group["is_seller"] or seller_seen
        group["is_buyer"] = group["is_buyer"] or buyer_seen

    company_rows = []
    for rut, group in sorted(grouped.items()):
        company_rows.append(
            {
                "rut": rut,
                "company_name": most_common_nonblank(group["names"]) or rut,
                "is_seller": group["is_seller"],
                "is_buyer": group["is_buyer"],
                "giro": most_common_nonblank(group["giros"]),
                "address": most_common_nonblank(group["addresses"]),
                "commune": most_common_nonblank(group["communes"]),
                "city": most_common_nonblank(group["cities"]),
            }
        )

    return company_rows, errors


def build_item_catalog_rows(
    source_items: list[dict[str, Any]],
) -> list[dict[str, str]]:
    rows_by_identity: dict[tuple[str, str], dict[str, str]] = {}
    for item in source_items:
        item_name = clean_value(item["item_text"])
        description = catalog_description(item_name, item.get("description"))
        if not item_name:
            continue
        rows_by_identity.setdefault(
            (item_name, description),
            {
                "item_name": item_name,
                "description": description,
            },
        )
    return [rows_by_identity[key] for key in sorted(rows_by_identity)]


def build_invoice_rows(
    source_invoices: list[dict[str, Any]],
    xml_invoices_by_key: dict[str, XmlInvoice],
    company_id_by_rut: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for source_invoice in sorted(source_invoices, key=source_invoice_key):
        key = source_invoice_key(source_invoice)
        xml_invoice = xml_invoices_by_key.get(key)
        if xml_invoice is None:
            errors.append({"invoice_key": key, "error": "missing_xml_invoice"})
            continue

        other_party_rut = xml_invoice.seller_rut if xml_invoice.transaction_type == "COMPRAS" else xml_invoice.buyer_rut
        company_id = company_id_by_rut.get(other_party_rut)
        if not company_id:
            errors.append({"invoice_key": key, "rut": other_party_rut, "error": "missing_company_id"})
            continue

        rows.append(
            {
                "invoice_id": source_invoice["invoice_id"],
                "company_id": company_id,
                "transaction_type": xml_invoice.transaction_type,
                "invoice_folio": xml_invoice.invoice_folio,
                "document_type": xml_invoice.document_type,
                "invoice_date": xml_invoice.invoice_date,
                "seller_rut": xml_invoice.seller_rut,
                "seller_name": xml_invoice.seller_name,
                "seller_giro": xml_invoice.seller_giro,
                "seller_address": xml_invoice.seller_address,
                "seller_commune": xml_invoice.seller_commune,
                "seller_city": xml_invoice.seller_city,
                "buyer_rut": xml_invoice.buyer_rut,
                "buyer_name": xml_invoice.buyer_name,
                "buyer_giro": xml_invoice.buyer_giro,
                "buyer_address": xml_invoice.buyer_address,
                "buyer_commune": xml_invoice.buyer_commune,
                "buyer_city": xml_invoice.buyer_city,
                "receiver_internal_code": xml_invoice.receiver_internal_code,
                "net_amount": xml_invoice.net_amount,
                "iva_amount": xml_invoice.iva_amount,
                "exempt_amount": xml_invoice.exempt_amount,
                "total_amount": xml_invoice.total_amount,
                "due_date": xml_invoice.due_date,
                "payment_form": xml_invoice.payment_form,
            }
        )

    return rows, errors


def build_invoice_item_rows(
    source_items: list[dict[str, Any]],
    source_invoice_by_id: dict[str, dict[str, Any]],
    xml_lines_by_key: dict[str, XmlLine],
    catalog_id_by_identity: dict[tuple[str, str], str],
    category_id_by_code: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for item in sorted(source_items, key=lambda row: (row["invoice_id"], row["invoice_line_number"])):
        source_invoice = source_invoice_by_id.get(item["invoice_id"])
        if source_invoice is None:
            errors.append({"item_id": item.get("item_id"), "invoice_id": item.get("invoice_id"), "error": "missing_source_invoice"})
            continue

        inv_key = source_invoice_key(source_invoice)
        key_line = line_key(inv_key, int(item["invoice_line_number"]))
        xml_line = xml_lines_by_key.get(key_line)
        if xml_line is None:
            errors.append({"item_id": item.get("item_id"), "line_key": key_line, "error": "missing_xml_line"})
            continue

        item_name = clean_value(item["item_text"])
        item_description = item.get("description")
        catalog_identity = (item_name, catalog_description(item_name, item_description))
        catalog_item_id = catalog_id_by_identity.get(catalog_identity)
        if not catalog_item_id:
            errors.append(
                {
                    "item_id": item.get("item_id"),
                    "catalog_identity": list(catalog_identity),
                    "error": "missing_catalog_item_id",
                }
            )
            continue

        predicted_code = clean_value(item["predicted_code"])
        predicted_categories_id = category_id_by_code.get(predicted_code)
        if not predicted_categories_id:
            errors.append(
                {
                    "item_id": item.get("item_id"),
                    "code": predicted_code,
                    "error": "missing_predicted_categories_id",
                }
            )
            continue

        final_code = none_if_blank(item.get("final_code"))
        final_categories_id = category_id_by_code.get(final_code) if final_code else None
        if final_code and not final_categories_id:
            errors.append(
                {
                    "item_id": item.get("item_id"),
                    "code": final_code,
                    "error": "missing_final_categories_id",
                }
            )
            continue

        rows.append(
            {
                "item_id": item["item_id"],
                "invoice_id": item["invoice_id"],
                "catalog_item_id": catalog_item_id,
                "invoice_line_number": item["invoice_line_number"],
                "item_text": item["item_text"],
                "description": item.get("description"),
                "item_codes": xml_line.item_codes,
                "meter_code": item.get("meter_code") or xml_line.meter_code,
                "quantity": xml_line.quantity,
                "unit": xml_line.unit,
                "unit_price": xml_line.unit_price,
                "amount": item.get("amount") if item.get("amount") is not None else xml_line.amount,
                "discount_pct": xml_line.discount_pct,
                "discount_amount": xml_line.discount_amount,
                "recargo_amount": xml_line.recargo_amount,
                "tax_exempt": xml_line.tax_exempt,
                "additional_tax_code": xml_line.additional_tax_code,
                "model_version": item["model_version"],
                "prediction_source": item["prediction_source"],
                "predicted_categories_id": predicted_categories_id,
                "predicted_code": item["predicted_code"],
                "predicted_name": item.get("predicted_name"),
                "top1_score": item["top1_score"],
                "margin": item["margin"],
                "entropy": item["entropy"],
                "top3": remap_top3_categories(item.get("top3") or [], category_id_by_code),
                "decision": item["decision"],
                "reviewed": item["reviewed"],
                "final_categories_id": final_categories_id,
                "final_code": final_code,
            }
        )

    return rows, errors


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    if not rows:
        return
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def request_with_retries(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    retries: int,
    **kwargs: Any,
) -> httpx.Response:
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = client.request(method, url, **kwargs)
            if response.status_code < 500:
                response.raise_for_status()
                return response
            response.raise_for_status()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_exc = exc
            if attempt >= retries:
                break
            time.sleep(min(2**attempt, 8))
    assert last_exc is not None
    raise last_exc


def rest_headers(secret_key: str, *, count: bool = False) -> dict[str, str]:
    headers = {
        "apikey": secret_key,
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
    }
    if count:
        headers["Prefer"] = "count=exact"
    return headers


def fetch_all(
    client: httpx.Client,
    base_url: str,
    secret_key: str,
    table: str,
    *,
    select: str,
    order: str | None = None,
    page_size: int = 1000,
    retries: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    order_clause = f"&order={order}" if order else ""
    while True:
        url = f"{base_url}/rest/v1/{table}?select={select}{order_clause}"
        headers = rest_headers(secret_key)
        headers["Range"] = f"{offset}-{offset + page_size - 1}"
        response = request_with_retries(client, "GET", url, retries=retries, headers=headers)
        batch = response.json()
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return rows


def upsert_rows(
    client: httpx.Client,
    base_url: str,
    secret_key: str,
    table: str,
    rows: list[dict[str, Any]],
    *,
    on_conflict: str,
    retries: int,
    batch_size: int,
) -> None:
    if not rows:
        return
    url = f"{base_url}/rest/v1/{table}?on_conflict={on_conflict}"
    headers = rest_headers(secret_key)
    headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
    for index in range(0, len(rows), batch_size):
        batch = rows[index : index + batch_size]
        request_with_retries(client, "POST", url, retries=retries, headers=headers, json=batch)


def count_rows(
    client: httpx.Client,
    base_url: str,
    secret_key: str,
    table: str,
    *,
    query: str = "",
    retries: int,
) -> int:
    url = f"{base_url}/rest/v1/{table}?select=*&limit=1{query}"
    headers = rest_headers(secret_key, count=True)
    headers["Range"] = "0-0"
    response = request_with_retries(client, "GET", url, retries=retries, headers=headers)
    content_range = response.headers.get("content-range", "")
    if "/" not in content_range:
        return len(response.json())
    return int(content_range.split("/")[-1])


def require_tables(client: httpx.Client, base_url: str, secret_key: str, *, retries: int) -> None:
    missing: list[str] = []
    for table in [CATEGORIES_TABLE, COMPANIES_TABLE, ITEM_CATALOG_TABLE, INVOICES_TABLE, INVOICE_ITEMS_TABLE]:
        url = f"{base_url}/rest/v1/{table}?select=*&limit=1"
        response = client.get(url, headers=rest_headers(secret_key), timeout=30)
        if response.status_code == 404:
            missing.append(table)
        elif response.status_code >= 400:
            response.raise_for_status()
    if missing:
        raise RuntimeError(
            "Missing tables: "
            + ", ".join(missing)
            + ". Run Temp_Inference/normalized_company_item_schema.sql in Supabase SQL Editor first."
        )


def build_local_rows(
    snapshot_dir: Path,
    output_dir: Path,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, int], list[dict[str, Any]]]:
    category_rows, source_invoices, source_items = load_snapshot(snapshot_dir)
    source_invoice_by_id = {row["invoice_id"]: row for row in source_invoices}

    xml_invoices_by_key, xml_lines_by_key, xml_stats, xml_errors = parse_raw_xml()
    errors: list[dict[str, Any]] = []
    errors.extend(xml_errors)

    company_rows, company_errors = build_companies(source_invoices, xml_invoices_by_key)
    errors.extend(company_errors)

    catalog_rows = build_item_catalog_rows(source_items)

    # Dry-run uses synthetic IDs for mapping. Real writes fetch DB-generated IDs.
    synthetic_company_ids = {row["rut"]: f"dry-company-{index}" for index, row in enumerate(company_rows, start=1)}
    invoice_rows, invoice_errors = build_invoice_rows(source_invoices, xml_invoices_by_key, synthetic_company_ids)
    errors.extend(invoice_errors)

    synthetic_catalog_ids = {
        (row["item_name"], row["description"]): f"dry-catalog-{index}"
        for index, row in enumerate(catalog_rows, start=1)
    }
    synthetic_category_ids = {
        row["code"]: f"dry-category-{index}"
        for index, row in enumerate(category_rows, start=1)
    }
    item_rows, item_errors = build_invoice_item_rows(
        source_items,
        source_invoice_by_id,
        xml_lines_by_key,
        synthetic_catalog_ids,
        synthetic_category_ids,
    )
    errors.extend(item_errors)

    stats = {
        **xml_stats,
        "snapshot_categories": len(category_rows),
        "snapshot_invoices": len(source_invoices),
        "snapshot_invoice_items": len(source_items),
        "companies_to_write": len(company_rows),
        "item_catalog_rows_to_write": len(catalog_rows),
        "invoices_to_write": len(invoice_rows),
        "invoice_items_to_write": len(item_rows),
        "auto_accept_items": sum(1 for row in source_items if row.get("decision") == "auto_accept"),
        "review_required_items": sum(1 for row in source_items if row.get("decision") == "review_required"),
        "item_rows_with_quantity": sum(1 for row in item_rows if row.get("quantity") is not None),
        "item_rows_with_unit": sum(1 for row in item_rows if row.get("unit")),
        "item_rows_with_unit_price": sum(1 for row in item_rows if row.get("unit_price") is not None),
        "item_rows_with_discount_pct": sum(1 for row in item_rows if row.get("discount_pct") is not None),
        "item_rows_with_discount_amount": sum(1 for row in item_rows if row.get("discount_amount") is not None),
        "item_rows_with_recargo_amount": sum(1 for row in item_rows if row.get("recargo_amount") is not None),
        "item_rows_tax_exempt": sum(1 for row in item_rows if row.get("tax_exempt")),
        "item_rows_with_additional_tax_code": sum(1 for row in item_rows if row.get("additional_tax_code")),
        "item_rows_with_item_codes": sum(1 for row in item_rows if row.get("item_codes")),
        "raw_detail_lines_not_in_snapshot": xml_stats["raw_detail_lines"] - len(source_items),
    }

    write_jsonl(output_dir / "company_item_migration_errors.jsonl", errors)
    return (
        {
            "category_rows": category_rows,
            "source_invoices": source_invoices,
            "source_items": source_items,
            "company_rows": company_rows,
            "catalog_rows": catalog_rows,
            "invoice_rows": invoice_rows,
            "item_rows": item_rows,
        },
        stats,
        errors,
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=HERE / ".env.loader")
    parser.add_argument("--snapshot-dir", type=Path, default=DEFAULT_SNAPSHOT_DIR)
    parser.add_argument("--write", action="store_true", help="Actually write to Supabase. Without this, only validates locally.")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--output-dir", type=Path, default=HERE)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.batch_size < 1:
        print("ERROR: --batch-size must be positive", file=sys.stderr)
        return 2
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print("Building rows from local snapshot and raw XML...")
    rows, stats, errors = build_local_rows(args.snapshot_dir, args.output_dir)
    for name, value in stats.items():
        print(f"{name}: {value:,}")

    if errors:
        print(f"ERROR: {len(errors):,} migration mapping errors captured in company_item_migration_errors.jsonl")
        return 1

    expected_items = stats["snapshot_invoice_items"]
    if stats["invoice_items_to_write"] != expected_items:
        print(
            f"ERROR: item row mismatch. Expected {expected_items:,}, built {stats['invoice_items_to_write']:,}.",
            file=sys.stderr,
        )
        return 1

    if not args.write:
        print("Dry run only. No Supabase writes performed.")
        return 0

    env_values = load_env_file(args.env_file)
    supabase_url = env_value("SUPABASE_URL", env_values)
    supabase_key = env_value("SUPABASE_SECRET_KEY", env_values) or env_value("SUPABASE_SERVICE_ROLE_KEY", env_values)
    if not supabase_url or not supabase_key:
        print("ERROR: SUPABASE_URL and SUPABASE_SECRET_KEY are required", file=sys.stderr)
        return 2
    base_url = supabase_url.rstrip().rstrip("/")

    with httpx.Client(timeout=args.timeout) as client:
        require_tables(client, base_url, supabase_key, retries=args.retries)

        print("Upserting categories...")
        upsert_rows(
            client,
            base_url,
            supabase_key,
            CATEGORIES_TABLE,
            rows["category_rows"],
            on_conflict="code",
            retries=args.retries,
            batch_size=args.batch_size,
        )
        category_db_rows = fetch_all(
            client,
            base_url,
            supabase_key,
            CATEGORIES_TABLE,
            select="categories_id,code",
            order="code.asc",
            retries=args.retries,
        )
        category_id_by_code = {row["code"]: row["categories_id"] for row in category_db_rows}

        print("Upserting companies...")
        upsert_rows(
            client,
            base_url,
            supabase_key,
            COMPANIES_TABLE,
            rows["company_rows"],
            on_conflict="rut",
            retries=args.retries,
            batch_size=args.batch_size,
        )
        company_db_rows = fetch_all(
            client,
            base_url,
            supabase_key,
            COMPANIES_TABLE,
            select="company_id,rut",
            order="rut.asc",
            retries=args.retries,
        )
        company_id_by_rut = {row["rut"]: row["company_id"] for row in company_db_rows}

        print("Preparing invoices with DB company UUIDs...")
        xml_invoices_by_key, xml_lines_by_key, _xml_stats, _xml_errors = parse_raw_xml()
        invoice_rows, invoice_errors = build_invoice_rows(
            rows["source_invoices"],
            xml_invoices_by_key,
            company_id_by_rut,
        )
        if invoice_errors:
            write_jsonl(args.output_dir / "company_item_migration_errors.jsonl", invoice_errors)
            print(f"ERROR: {len(invoice_errors):,} invoice rows failed DB company mapping.")
            return 1

        print("Upserting invoices...")
        upsert_rows(
            client,
            base_url,
            supabase_key,
            INVOICES_TABLE,
            invoice_rows,
            on_conflict="seller_rut,document_type,invoice_folio",
            retries=args.retries,
            batch_size=args.batch_size,
        )

        print("Upserting item catalog...")
        upsert_rows(
            client,
            base_url,
            supabase_key,
            ITEM_CATALOG_TABLE,
            rows["catalog_rows"],
            on_conflict="item_name,description",
            retries=args.retries,
            batch_size=args.batch_size,
        )
        catalog_db_rows = fetch_all(
            client,
            base_url,
            supabase_key,
            ITEM_CATALOG_TABLE,
            select="catalog_item_id,item_name,description",
            order="item_name.asc",
            retries=args.retries,
        )
        catalog_id_by_identity = {
            (row["item_name"], row["description"]): row["catalog_item_id"]
            for row in catalog_db_rows
        }

        print("Preparing invoice items with DB catalog UUIDs...")
        source_invoice_by_id = {row["invoice_id"]: row for row in rows["source_invoices"]}
        item_rows, item_errors = build_invoice_item_rows(
            rows["source_items"],
            source_invoice_by_id,
            xml_lines_by_key,
            catalog_id_by_identity,
            category_id_by_code,
        )
        if item_errors:
            write_jsonl(args.output_dir / "company_item_migration_errors.jsonl", item_errors)
            print(f"ERROR: {len(item_errors):,} invoice item rows failed DB catalog mapping.")
            return 1

        print("Upserting invoice items...")
        upsert_rows(
            client,
            base_url,
            supabase_key,
            INVOICE_ITEMS_TABLE,
            item_rows,
            on_conflict="invoice_id,invoice_line_number",
            retries=args.retries,
            batch_size=args.batch_size,
        )

        print("Verifying final counts...")
        final_counts = {
            "categories": count_rows(client, base_url, supabase_key, CATEGORIES_TABLE, retries=args.retries),
            "companies": count_rows(client, base_url, supabase_key, COMPANIES_TABLE, retries=args.retries),
            "item_catalog": count_rows(client, base_url, supabase_key, ITEM_CATALOG_TABLE, retries=args.retries),
            "invoices": count_rows(client, base_url, supabase_key, INVOICES_TABLE, retries=args.retries),
            "invoice_items": count_rows(client, base_url, supabase_key, INVOICE_ITEMS_TABLE, retries=args.retries),
            "invoice_items_auto_accept": count_rows(
                client,
                base_url,
                supabase_key,
                INVOICE_ITEMS_TABLE,
                query="&decision=eq.auto_accept",
                retries=args.retries,
            ),
            "invoice_items_review_required": count_rows(
                client,
                base_url,
                supabase_key,
                INVOICE_ITEMS_TABLE,
                query="&decision=eq.review_required",
                retries=args.retries,
            ),
        }
        for name, value in final_counts.items():
            print(f"{name}: {value:,}")

    print("Company/item schema migration completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
