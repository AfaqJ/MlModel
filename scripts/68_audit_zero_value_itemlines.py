#!/usr/bin/env python3
"""Inventory zero-value XML detail lines without deleting or relabelling them.

This scans only the authoritative COMPRAS and VENTAS source trees. A line is a
candidate when the XML explicitly says PrcItem=0 or MontoItem=0. Missing price
fields are deliberately not treated as zero. The output exists for a human
audit; zero value by itself is never a junk verdict.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.inference.line_filters import zero_value_junk_reason
RAW_ROOTS = {
    "COMPRAS": ROOT / "Data/Raw_Data/dte_96685810_COMPRAS",
    "VENTAS": ROOT / "Data/Raw_Data/dte_96685810_VENTAS",
}
OUTPUT = ROOT / "reports/recovery_v1_3_1/zero_value_audit"


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


def text(element: ET.Element | None) -> str:
    return re.sub(r"\s+", " ", (element.text or "")).strip() if element is not None else ""


def number(value: str) -> Decimal | None:
    value = value.strip().replace(",", ".")
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_local_xml(path: Path) -> ET.Element:
    """Decode the mixed UTF-8/Latin-1 source collection before XML parsing."""
    raw = path.read_bytes()
    try:
        xml_text = raw.decode("utf-8")
    except UnicodeDecodeError:
        xml_text = raw.decode("latin-1")
    return ET.fromstring(xml_text.encode("utf-8"))


def scan() -> tuple[list[dict], dict]:
    rows: list[dict] = []
    stats = Counter()
    parse_errors: list[str] = []
    for direction, source_root in RAW_ROOTS.items():
        for path in sorted(source_root.rglob("*.xml")):
            stats["xml_files"] += 1
            try:
                root = parse_local_xml(path)
            except ET.ParseError as exc:
                parse_errors.append(f"{path.relative_to(ROOT)}: {exc}")
                continue
            for dte in iter_named(root, "DTE"):
                doc = find_deep_named(dte, "Documento")
                if doc is None:
                    continue
                encab = find_named(doc, "Encabezado")
                id_doc = find_named(encab, "IdDoc")
                emisor = find_named(encab, "Emisor")
                folio = text(find_named(id_doc, "Folio"))
                provider = text(find_named(emisor, "RznSoc"))
                provider_rut = text(find_named(emisor, "RUTEmisor"))
                for detail in iter_named(doc, "Detalle"):
                    stats["detail_lines"] += 1
                    raw_price = text(find_named(detail, "PrcItem"))
                    raw_amount = text(find_named(detail, "MontoItem"))
                    unit_price = number(raw_price)
                    amount = number(raw_amount)
                    explicit_zero_price = unit_price == 0 if unit_price is not None else False
                    explicit_zero_amount = amount == 0 if amount is not None else False
                    if not (explicit_zero_price or explicit_zero_amount):
                        continue
                    item = text(find_named(detail, "NmbItem"))
                    description = text(find_named(detail, "DscItem"))
                    stats["zero_candidates"] += 1
                    if explicit_zero_price:
                        stats["explicit_zero_price"] += 1
                    if explicit_zero_amount:
                        stats["explicit_zero_amount"] += 1
                    rows.append({
                        "direction": direction,
                        "source_file": path.name,
                        "source_path": str(path.relative_to(ROOT)),
                        "folio": folio,
                        "line_number": text(find_named(detail, "NroLinDet")),
                        "provider_rut": provider_rut,
                        "provider": provider,
                        "item_text": item,
                        "description": description,
                        "quantity": text(find_named(detail, "QtyItem")),
                        "unit": text(find_named(detail, "UnmdItem")),
                        "unit_price": raw_price,
                        "amount": raw_amount,
                        "discount_pct": text(find_named(detail, "DescuentoPct")),
                        "discount_amount": text(find_named(detail, "DescuentoMonto")),
                        "normalized_text": normalize(" ".join(part for part in (item, description) if part)),
                        "zero_reason": ";".join(
                            reason for reason, present in (
                                ("price_zero", explicit_zero_price),
                                ("amount_zero", explicit_zero_amount),
                            ) if present
                        ),
                    })
                    reason = zero_value_junk_reason(
                        item,
                        description,
                        amount=raw_amount,
                        unit_price=raw_price,
                    )
                    rows[-1]["audit_verdict"] = "EXCLUDE_JUNK" if reason else "KEEP_GENUINE_OR_UNCERTAIN"
                    rows[-1]["audit_rationale"] = reason or (
                        "zero-value text may describe a real/free/bundled good, service, or correction; retain safely"
                    )
    return rows, {**stats, "parse_error_count": len(parse_errors), "parse_errors": parse_errors}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    rows, stats = scan()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    fields = [
        "direction", "source_file", "source_path", "folio", "line_number",
        "provider_rut", "provider", "item_text", "description", "quantity", "unit",
        "unit_price", "amount", "discount_pct", "discount_amount", "normalized_text",
        "zero_reason",
        "audit_verdict", "audit_rationale",
    ]
    write_csv(args.output_dir / "all_zero_value_lines.csv", rows, fields)

    groups: defaultdict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        groups[(row["direction"], row["normalized_text"])].append(row)
    grouped_rows = []
    for (direction, normalized_text), group in groups.items():
        verdicts = {row["audit_verdict"] for row in group}
        rationales = {row["audit_rationale"] for row in group}
        if len(verdicts) != 1 or len(rationales) != 1:
            raise RuntimeError(f"inconsistent audit decision for {direction}/{normalized_text}")
        grouped_rows.append({
            "rows": len(group),
            "direction": direction,
            "normalized_text": normalized_text,
            "example_item": group[0]["item_text"],
            "example_description": group[0]["description"],
            "providers": " | ".join(sorted({row["provider"] for row in group})),
            "zero_reasons": ";".join(sorted({row["zero_reason"] for row in group})),
            "verdict": next(iter(verdicts)),
            "rationale": next(iter(rationales)),
        })
    grouped_rows.sort(key=lambda row: (-row["rows"], row["direction"], row["normalized_text"]))
    write_csv(args.output_dir / "distinct_zero_value_groups.csv", grouped_rows, [
        "rows", "direction", "normalized_text", "example_item", "example_description",
        "providers", "zero_reasons", "verdict", "rationale",
    ])
    summary = {
        **stats,
        "distinct_zero_value_groups": len(grouped_rows),
        "direction_counts": dict(sorted(Counter(row["direction"] for row in rows).items())),
        "zero_reason_counts": dict(sorted(Counter(row["zero_reason"] for row in rows).items())),
        "audit_verdict_counts": dict(sorted(Counter(row["audit_verdict"] for row in rows).items())),
        "audit_rationale_counts": dict(sorted(Counter(row["audit_rationale"] for row in rows).items())),
        "safety_rule": "zero value alone never implies junk; every distinct group requires an audited verdict",
    }
    (args.output_dir / "inventory_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
