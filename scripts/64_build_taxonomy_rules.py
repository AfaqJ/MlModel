#!/usr/bin/env python3
"""Build the deterministic exact-name table from the active taxonomy.

Every one of the 71 active leaf names becomes an exact rule in its valid DTE
direction. Explicit aliases live in a separate reviewed CSV. Normalization is
used only to absorb case, accents, punctuation, spacing, and common unit forms;
no fuzzy or substring matching is performed.
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.inference.normalize import normalize_text


TAXONOMY = ROOT / "Data/current_context_2026_06_30/taxonomy_from_plan.csv"
ALIASES = ROOT / "app/data/taxonomy_aliases.csv"
OUTPUT = ROOT / "app/data/business_rules.csv"
RULE_VERSION = "2026.08.11-v2"
FIELDS = ["rule_version", "transaction_type", "item_text", "category_code", "action", "note"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def direction_for(code: str) -> str:
    return "VENTAS" if code.startswith("ING-") else "COMPRAS"


def build(taxonomy_path: Path, aliases_path: Path) -> list[dict[str, str]]:
    taxonomy = read_csv(taxonomy_path)
    aliases = read_csv(aliases_path)
    if len(taxonomy) != 71:
        raise RuntimeError(f"expected 71 active taxonomy rows, found {len(taxonomy)}")

    codes = {row["new_code"].strip() for row in taxonomy}
    rows: list[dict[str, str]] = []
    for row in taxonomy:
        code = row["new_code"].strip()
        rows.append({
            "rule_version": RULE_VERSION,
            "transaction_type": direction_for(code),
            "item_text": row["leaf"].strip(),
            "category_code": code,
            "action": "assign",
            "note": "Canonical active client taxonomy leaf; exact-name rule.",
        })

    for alias in aliases:
        code = alias["category_code"].strip()
        direction = alias["transaction_type"].strip().upper()
        if code not in codes:
            raise RuntimeError(f"alias references non-active category {code}")
        if direction != direction_for(code):
            raise RuntimeError(f"alias direction disagrees with taxonomy: {alias}")
        rows.append({
            "rule_version": RULE_VERSION,
            "transaction_type": direction,
            "item_text": alias["item_text"].strip(),
            "category_code": code,
            "action": "assign",
            "note": alias["note"].strip(),
        })

    seen: dict[tuple[str, str], str] = {}
    for row in rows:
        key = (row["transaction_type"], normalize_text(row["item_text"]))
        if key in seen:
            raise RuntimeError(
                f"duplicate normalized exact rule {key}: {seen[key]} and {row['item_text']}"
            )
        seen[key] = row["item_text"]
    return rows


def render(rows: list[dict[str, str]]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--taxonomy", type=Path, default=TAXONOMY)
    parser.add_argument("--aliases", type=Path, default=ALIASES)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    rows = build(args.taxonomy, args.aliases)
    rendered = render(rows)
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != rendered:
            raise SystemExit(f"generated rules are stale: {args.output}")
    else:
        args.output.write_text(rendered, encoding="utf-8")
    print({
        "active_taxonomy_rules": 71,
        "aliases": len(rows) - 71,
        "total_rules": len(rows),
        "ventas_labels": sum(row["new_code"].startswith("ING-") for row in read_csv(args.taxonomy)),
        "output": str(args.output),
    })


if __name__ == "__main__":
    main()
