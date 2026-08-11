#!/usr/bin/env python3
"""Build a local, natural-key import bundle for the current five-table schema.

The script never contacts Supabase. It preserves all invoice headers, excludes
only lines approved by the zero-value junk audit, and emits an explicit stale
line reconciliation list so a later upload cannot leave old junk rows behind.
Database UUIDs are intentionally resolved at upload time from natural keys.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPLAY = ROOT / "reports/recovery_v1_3_1/local_replay/inference_rows_with_natural_keys.jsonl"
OUTPUT = ROOT / "reports/recovery_v1_3_1/supabase_five_table_bundle"
TAXONOMY = ROOT / "Data/current_context_2026_06_30/taxonomy_from_plan.csv"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_xml_helpers():
    path = ROOT / "Temp_Inference/migrate_to_company_item_schema.py"
    spec = importlib.util.spec_from_file_location("company_item_migration", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load XML helpers from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.RAW_DIRS = {
        "COMPRAS": ROOT / "Data/Raw_Data/dte_96685810_COMPRAS",
        "VENTAS": ROOT / "Data/Raw_Data/dte_96685810_VENTAS",
    }
    return module


def most_common(values: list[str | None]) -> str | None:
    counter = Counter(value for value in values if value)
    return counter.most_common(1)[0][0] if counter else None


def build_companies(invoices) -> list[dict[str, Any]]:
    appearances: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for invoice in invoices:
        appearances[invoice.seller_rut].append({
            "name": invoice.seller_name, "giro": invoice.seller_giro,
            "address": invoice.seller_address, "commune": invoice.seller_commune,
            "city": invoice.seller_city, "seller": True, "buyer": False,
        })
        appearances[invoice.buyer_rut].append({
            "name": invoice.buyer_name, "giro": invoice.buyer_giro,
            "address": invoice.buyer_address, "commune": invoice.buyer_commune,
            "city": invoice.buyer_city, "seller": False, "buyer": True,
        })
    rows = []
    for rut, seen in sorted(appearances.items()):
        name = most_common([row["name"] for row in seen])
        if not rut or not name:
            raise RuntimeError(f"company missing required rut/name: {rut!r}")
        rows.append({
            "rut": rut,
            "company_name": name,
            "is_seller": any(row["seller"] for row in seen),
            "is_buyer": any(row["buyer"] for row in seen),
            "giro": most_common([row["giro"] for row in seen]),
            "address": most_common([row["address"] for row in seen]),
            "commune": most_common([row["commune"] for row in seen]),
            "city": most_common([row["city"] for row in seen]),
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", type=Path, default=REPLAY)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()

    helpers = load_xml_helpers()
    from app.inference.line_filters import zero_value_junk_reason

    predictions = read_jsonl(args.replay)
    prediction_by_line = {}
    for row in predictions:
        key = helpers.line_key(
            helpers.invoice_key(row["provider_rut"], row["document_type"], row["invoice_folio"]),
            int(row["invoice_line_number"]),
        )
        if key in prediction_by_line:
            raise RuntimeError(f"duplicate replay line key: {key}")
        prediction_by_line[key] = row

    invoice_map, line_map, xml_stats, xml_errors = helpers.parse_raw_xml()
    if xml_errors:
        raise RuntimeError(f"raw XML errors: {xml_errors[:5]}")
    invoices = [invoice_map[key] for key in sorted(invoice_map)]

    with TAXONOMY.open(encoding="utf-8-sig", newline="") as handle:
        categories = [
            {"code": row["new_code"], "name": row["leaf"]}
            for row in csv.DictReader(handle)
        ]

    invoice_rows = []
    for invoice in invoices:
        row = asdict(invoice)
        row.pop("invoice_key")
        # Current invoices.company_id denotes the counterparty. Resolve this
        # natural key to companies.company_id during a future upload.
        row["company_rut"] = (
            invoice.seller_rut if invoice.transaction_type == "COMPRAS" else invoice.buyer_rut
        )
        invoice_rows.append(row)

    item_rows = []
    stale_junk_rows = []
    catalog_identities = set()
    invoice_retained_counts = Counter()
    for key in sorted(line_map):
        line = line_map[key]
        invoice = invoice_map[line.invoice_key]
        junk_reason = zero_value_junk_reason(
            line.item_text,
            line.description or "",
            amount=line.amount,
            unit_price=line.unit_price,
        )
        natural_key = {
            "seller_rut": invoice.seller_rut,
            "document_type": invoice.document_type,
            "invoice_folio": invoice.invoice_folio,
            "invoice_line_number": line.invoice_line_number,
        }
        if junk_reason:
            stale_junk_rows.append({
                **natural_key,
                "item_text": line.item_text,
                "description": line.description,
                "amount": line.amount,
                "unit_price": line.unit_price,
                "audit_rationale": junk_reason,
            })
            continue
        prediction = prediction_by_line.get(key)
        if prediction is None:
            raise RuntimeError(f"retained XML line missing ONNX replay prediction: {key}")
        catalog_description = helpers.catalog_description(line.item_text, line.description)
        catalog_identities.add((line.item_text, catalog_description))
        invoice_retained_counts[line.invoice_key] += 1
        item_rows.append({
            **natural_key,
            "catalog_item_name": line.item_text,
            "catalog_description": catalog_description,
            "item_text": line.item_text,
            "description": line.description,
            "item_codes": line.item_codes,
            "meter_code": line.meter_code,
            "quantity": line.quantity,
            "unit": line.unit,
            "unit_price": line.unit_price,
            "amount": line.amount,
            "discount_pct": line.discount_pct,
            "discount_amount": line.discount_amount,
            "recargo_amount": line.recargo_amount,
            "tax_exempt": line.tax_exempt,
            "additional_tax_code": line.additional_tax_code,
            "model_version": prediction["model_version"],
            "prediction_source": prediction["prediction_source"],
            "predicted_code": prediction["predicted_code"],
            "predicted_name": prediction["predicted_name"],
            "top1_score": prediction["top1_score"],
            "margin": prediction["margin"],
            "entropy": prediction["entropy"],
            "top3": prediction["top3"],
            "decision": prediction["decision"],
            "reviewed": False,
            "final_code": prediction["final_code"],
        })

    if len(prediction_by_line) != len(item_rows):
        extra = sorted(set(prediction_by_line) - {
            helpers.line_key(
                helpers.invoice_key(row["seller_rut"], row["document_type"], row["invoice_folio"]),
                row["invoice_line_number"],
            ) for row in item_rows
        })
        raise RuntimeError(f"replay/XML mismatch: {len(extra)} unmatched predictions; sample={extra[:5]}")

    catalog_rows = [
        {"item_name": item_name, "description": description}
        for item_name, description in sorted(catalog_identities)
    ]
    companies = build_companies(invoices)
    empty_invoices = [
        {
            "seller_rut": invoice.seller_rut,
            "document_type": invoice.document_type,
            "invoice_folio": invoice.invoice_folio,
            "source_file": invoice.source_file,
            "reason": "all_detail_lines_are_audited_zero_value_junk",
        }
        for invoice in invoices if invoice_retained_counts[invoice.invoice_key] == 0
    ]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "categories.jsonl": categories,
        "companies.jsonl": companies,
        "item_catalog.jsonl": catalog_rows,
        "invoices.jsonl": invoice_rows,
        "invoice_items.jsonl": item_rows,
        "reconcile_delete_junk_lines.jsonl": stale_junk_rows,
        "invoices_with_no_retained_items.jsonl": empty_invoices,
    }
    for name, rows in files.items():
        write_jsonl(args.output_dir / name, rows)

    manifest = {
        "release": "v1.3.1-local-only",
        "schema": "Temp_Inference/normalized_company_item_schema.sql",
        "network_calls": 0,
        "uuid_policy": "resolve from natural keys at upload time; no fabricated database UUIDs",
        "reconciliation_policy": (
            "backup affected invoice_items, upsert retained rows, then delete only the explicit "
            "invoice+line keys in reconcile_delete_junk_lines.jsonl inside one transaction"
        ),
        "raw_xml": xml_stats,
        "counts": {name.removesuffix(".jsonl"): len(rows) for name, rows in files.items()},
        "decision_counts": dict(sorted(Counter(row["decision"] for row in item_rows).items())),
        "source_counts": dict(sorted(Counter(row["prediction_source"] for row in item_rows).items())),
        "invariants": {
            "categories_are_71": len(categories) == 71,
            "all_5195_invoice_headers_preserved": len(invoice_rows) == 5195,
            "retained_invoice_items_are_11663": len(item_rows) == 11663,
            "audited_junk_lines_are_440": len(stale_junk_rows) == 440,
            "empty_invoice_headers_preserved_are_29": len(empty_invoices) == 29,
            "all_predictions_mapped_once": len(prediction_by_line) == len(item_rows),
        },
    }
    manifest["sha256"] = {
        name: sha256(args.output_dir / name) for name in sorted(files)
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.output_dir / "UPLOAD_README.md").write_text(
        "# v1.3.1 Supabase bundle (local only)\n\n"
        "This bundle matches the current five-table schema. It contains natural keys because local data "
        "cannot know Supabase-generated UUIDs. A future importer must resolve category code, company RUT, "
        "invoice `(seller_rut, document_type, invoice_folio)`, and catalog `(item_name, description)` keys.\n\n"
        "Before changing remote data, export/backup the five tables. In one transaction: upsert categories, "
        "companies, catalog and all 5,195 invoice headers; resolve UUIDs; upsert the 11,663 retained item lines; "
        "then delete only the explicit 440 keys in `reconcile_delete_junk_lines.jsonl`. Roll back the transaction "
        "if any count/hash/invariant differs from `manifest.json`. The 29 invoices with no retained lines remain "
        "valid invoice headers and must not be deleted.\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
