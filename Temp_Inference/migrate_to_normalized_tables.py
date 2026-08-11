#!/usr/bin/env python3
"""Backfill normalized Supabase tables from line_item_predictions.

This does not run inference. It reads the already-labeled wide table, parses
local raw XML for invoice buyer/seller metadata, and writes the normalized
taxonomy_categories, invoices, and invoice_items tables.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
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

SOURCE_TABLE = "line_item_predictions"
TAXONOMY_TABLE = "taxonomy_categories"
INVOICES_TABLE = "invoices"
ITEMS_TABLE = "invoice_items"


@dataclass(frozen=True)
class InvoiceMeta:
    invoice_key: str
    invoice_folio: str
    document_type: str
    transaction_type: str
    seller_rut: str
    buyer_rut: str
    seller_name: str | None
    buyer_name: str | None
    invoice_date: str


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


def none_if_blank(value: str) -> str | None:
    value = value.strip()
    return value or None


def normalize_rut(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())


def parse_raw_invoice_metadata() -> tuple[dict[str, InvoiceMeta], dict[str, str], list[dict[str, Any]]]:
    """Return input_id -> invoice metadata and invoice_key -> source file maps."""
    item_to_invoice: dict[str, InvoiceMeta] = {}
    invoice_sources: dict[str, str] = {}
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
                encab = find_named(doc, "Encabezado")
                id_doc = find_named(encab, "IdDoc")
                emisor = find_named(encab, "Emisor")
                receptor = find_named(encab, "Receptor")

                document_type = clean_text(find_named(id_doc, "TipoDTE"))
                invoice_folio = clean_text(find_named(id_doc, "Folio"))
                invoice_date = clean_text(find_named(id_doc, "FchEmis"))
                seller_rut = normalize_rut(clean_text(find_named(emisor, "RUTEmisor")))
                buyer_rut = normalize_rut(clean_text(find_named(receptor, "RUTRecep")))
                seller_name = none_if_blank(clean_text(find_named(emisor, "RznSoc")))
                buyer_name = none_if_blank(clean_text(find_named(receptor, "RznSocRecep")))

                required = {
                    "document_type": document_type,
                    "invoice_folio": invoice_folio,
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

                invoice_key = f"{seller_rut}|{document_type}|{invoice_folio}"
                meta = InvoiceMeta(
                    invoice_key=invoice_key,
                    invoice_folio=invoice_folio,
                    document_type=document_type,
                    transaction_type=transaction_type,
                    seller_rut=seller_rut,
                    buyer_rut=buyer_rut,
                    seller_name=seller_name,
                    buyer_name=buyer_name,
                    invoice_date=invoice_date,
                )
                invoice_sources.setdefault(invoice_key, str(path.relative_to(ROOT)))

                for detalle in iter_named(doc, "Detalle"):
                    line_number = clean_text(find_named(detalle, "NroLinDet"))
                    if not line_number:
                        continue
                    input_id = f"{transaction_type}|{seller_rut}|{invoice_folio}|{line_number}"
                    item_to_invoice[input_id] = meta

    return item_to_invoice, invoice_sources, errors


def load_taxonomy_rows() -> list[dict[str, str]]:
    labels = json.loads((ROOT / "artifacts" / "v1.1.0" / "labels.json").read_text(encoding="utf-8"))["labels"]
    return [{"code": row["code"], "name": row["name"]} for row in labels]


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
    total = content_range.split("/")[-1]
    return int(total)


def require_tables(
    client: httpx.Client,
    base_url: str,
    secret_key: str,
    *,
    retries: int,
) -> None:
    missing: list[str] = []
    for table in [TAXONOMY_TABLE, INVOICES_TABLE, ITEMS_TABLE]:
        url = f"{base_url}/rest/v1/{table}?select=*&limit=1"
        response = client.get(url, headers=rest_headers(secret_key), timeout=30)
        if response.status_code == 404:
            missing.append(table)
        elif response.status_code >= 400:
            response.raise_for_status()
    if missing:
        raise RuntimeError(
            "Missing normalized tables: "
            + ", ".join(missing)
            + ". Run Temp_Inference/normalized_schema.sql in Supabase SQL Editor first."
        )


def build_invoice_rows(metas: dict[str, InvoiceMeta]) -> list[dict[str, Any]]:
    return [
        {
            "invoice_folio": meta.invoice_folio,
            "document_type": meta.document_type,
            "transaction_type": meta.transaction_type,
            "seller_rut": meta.seller_rut,
            "buyer_rut": meta.buyer_rut,
            "seller_name": meta.seller_name,
            "buyer_name": meta.buyer_name,
            "invoice_date": meta.invoice_date,
        }
        for meta in sorted(metas.values(), key=lambda meta: meta.invoice_key)
    ]


def enrich_top3(top3: list[dict[str, Any]], taxonomy_by_code: dict[str, str]) -> list[dict[str, Any]]:
    enriched = []
    for row in top3:
        code = row.get("code")
        enriched.append(
            {
                "taxonomy_id": taxonomy_by_code.get(code),
                "code": code,
                "name": row.get("name"),
                "score": row.get("score"),
            }
        )
    return enriched


def build_item_rows(
    source_rows: list[dict[str, Any]],
    item_to_invoice: dict[str, InvoiceMeta],
    invoice_id_by_key: dict[str, str],
    taxonomy_id_by_code: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    item_rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for row in source_rows:
        input_id = row["input_id"]
        meta = item_to_invoice.get(input_id)
        if meta is None:
            errors.append({"input_id": input_id, "error": "missing_xml_invoice_metadata"})
            continue
        invoice_id = invoice_id_by_key.get(meta.invoice_key)
        if not invoice_id:
            errors.append({"input_id": input_id, "invoice_key": meta.invoice_key, "error": "missing_invoice_id"})
            continue
        predicted_code = row["predicted_code"]
        predicted_taxonomy_id = taxonomy_id_by_code.get(predicted_code)
        if not predicted_taxonomy_id:
            errors.append({"input_id": input_id, "code": predicted_code, "error": "missing_predicted_taxonomy_id"})
            continue
        final_code = row.get("final_code")
        final_taxonomy_id = taxonomy_id_by_code.get(final_code) if final_code else None
        if final_code and not final_taxonomy_id:
            errors.append({"input_id": input_id, "code": final_code, "error": "missing_final_taxonomy_id"})
            continue
        item_rows.append(
            {
                "invoice_id": invoice_id,
                "invoice_line_number": row["invoice_line_number"],
                "item_text": row["item_text"],
                "description": row.get("description"),
                "meter_code": row.get("meter_code"),
                "amount": row.get("amount"),
                "model_version": row["model_version"],
                "prediction_source": row["prediction_source"],
                "predicted_taxonomy_id": predicted_taxonomy_id,
                "predicted_code": predicted_code,
                "predicted_name": row.get("predicted_name"),
                "top1_score": row["top1_score"],
                "margin": row["margin"],
                "entropy": row["entropy"],
                "top3": enrich_top3(row.get("top3") or [], taxonomy_id_by_code),
                "decision": row["decision"],
                "reviewed": row["reviewed"],
                "final_taxonomy_id": final_taxonomy_id,
                "final_code": final_code,
            }
        )
    return item_rows, errors


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


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=HERE / ".env.loader")
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

    env_values = load_env_file(args.env_file)
    supabase_url = env_value("SUPABASE_URL", env_values)
    supabase_key = env_value("SUPABASE_SECRET_KEY", env_values) or env_value("SUPABASE_SERVICE_ROLE_KEY", env_values)
    if not supabase_url or not supabase_key:
        print("ERROR: SUPABASE_URL and SUPABASE_SECRET_KEY are required", file=sys.stderr)
        return 2
    base_url = supabase_url.rstrip().rstrip("/")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    print("Parsing local XML invoice metadata...")
    item_to_invoice, _invoice_sources, xml_errors = parse_raw_invoice_metadata()
    if xml_errors:
        write_jsonl(args.output_dir / "normalized_migration_xml_errors.jsonl", xml_errors)
        print(f"Captured {len(xml_errors):,} XML metadata errors.")

    taxonomy_rows = load_taxonomy_rows()
    print(f"Local taxonomy rows: {len(taxonomy_rows):,}")
    print(f"Local invoice metadata rows: {len({meta.invoice_key for meta in item_to_invoice.values()}):,}")
    print(f"Local item metadata rows: {len(item_to_invoice):,}")

    with httpx.Client(timeout=args.timeout) as client:
        source_select = ",".join(
            [
                "input_id",
                "invoice_line_number",
                "item_text",
                "description",
                "meter_code",
                "amount",
                "model_version",
                "prediction_source",
                "predicted_code",
                "predicted_name",
                "top1_score",
                "margin",
                "entropy",
                "top3",
                "decision",
                "reviewed",
                "final_code",
            ]
        )
        source_rows = fetch_all(
            client,
            base_url,
            supabase_key,
            SOURCE_TABLE,
            select=source_select,
            order="input_id.asc",
            retries=args.retries,
        )
        print(f"Source prediction rows: {len(source_rows):,}")

        missing_xml = [row["input_id"] for row in source_rows if row["input_id"] not in item_to_invoice]
        if missing_xml:
            write_jsonl(
                args.output_dir / "normalized_migration_missing_xml.jsonl",
                [{"input_id": input_id} for input_id in missing_xml],
            )
            print(f"ERROR: {len(missing_xml):,} source rows have no matching local XML metadata.")
            return 1

        invoice_metas = {
            item_to_invoice[row["input_id"]].invoice_key: item_to_invoice[row["input_id"]]
            for row in source_rows
        }
        print(f"Invoice rows to migrate: {len(invoice_metas):,}")

        if not args.write:
            print("Dry run only. No normalized tables were written.")
            print("Next: run Temp_Inference/normalized_schema.sql in Supabase SQL Editor, then rerun with --write.")
            return 0

        require_tables(client, base_url, supabase_key, retries=args.retries)

        print("Upserting taxonomy categories...")
        upsert_rows(
            client,
            base_url,
            supabase_key,
            TAXONOMY_TABLE,
            taxonomy_rows,
            on_conflict="code",
            retries=args.retries,
            batch_size=args.batch_size,
        )
        taxonomy_db_rows = fetch_all(
            client,
            base_url,
            supabase_key,
            TAXONOMY_TABLE,
            select="taxonomy_id,code,name",
            order="code.asc",
            retries=args.retries,
        )
        taxonomy_id_by_code = {row["code"]: row["taxonomy_id"] for row in taxonomy_db_rows}

        print("Upserting invoices...")
        invoice_rows = build_invoice_rows(invoice_metas)
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
        invoice_db_rows = fetch_all(
            client,
            base_url,
            supabase_key,
            INVOICES_TABLE,
            select="invoice_id,seller_rut,document_type,invoice_folio",
            order="seller_rut.asc",
            retries=args.retries,
        )
        invoice_id_by_key = {
            f"{row['seller_rut']}|{row['document_type']}|{row['invoice_folio']}": row["invoice_id"]
            for row in invoice_db_rows
        }

        print("Preparing invoice items...")
        item_rows, item_errors = build_item_rows(source_rows, item_to_invoice, invoice_id_by_key, taxonomy_id_by_code)
        if item_errors:
            write_jsonl(args.output_dir / "normalized_migration_item_errors.jsonl", item_errors)
            print(f"ERROR: {len(item_errors):,} item rows failed mapping. No invoice_items write performed.")
            return 1

        print("Upserting invoice items...")
        upsert_rows(
            client,
            base_url,
            supabase_key,
            ITEMS_TABLE,
            item_rows,
            on_conflict="invoice_id,invoice_line_number",
            retries=args.retries,
            batch_size=args.batch_size,
        )

        print("Verifying normalized counts...")
        counts = {
            "taxonomy_categories": count_rows(client, base_url, supabase_key, TAXONOMY_TABLE, retries=args.retries),
            "invoices": count_rows(client, base_url, supabase_key, INVOICES_TABLE, retries=args.retries),
            "invoice_items": count_rows(client, base_url, supabase_key, ITEMS_TABLE, retries=args.retries),
            "invoice_items_auto_accept": count_rows(
                client,
                base_url,
                supabase_key,
                ITEMS_TABLE,
                query="&decision=eq.auto_accept",
                retries=args.retries,
            ),
            "invoice_items_review_required": count_rows(
                client,
                base_url,
                supabase_key,
                ITEMS_TABLE,
                query="&decision=eq.review_required",
                retries=args.retries,
            ),
        }
        for name, value in counts.items():
            print(f"{name}: {value:,}")

        expected = {
            "taxonomy_categories": len(taxonomy_rows),
            "invoices": len(invoice_metas),
            "invoice_items": len(source_rows),
        }
        failures = [name for name, expected_count in expected.items() if counts[name] != expected_count]
        if failures:
            print(f"ERROR: verification count mismatch for: {', '.join(failures)}", file=sys.stderr)
            return 1

    print("Normalized migration completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
