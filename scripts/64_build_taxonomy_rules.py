#!/usr/bin/env python3
"""Build the deterministic exact-name table from the active taxonomy.

SALES ONLY, AND WHY
-------------------
Only the six income (`ING-*`) leaves become exact rules. On the sales side the
client issues the invoice, so a line reading `VENTA DE LECHE` is the client
naming their own category — the strongest evidence there is, and the reason
`ING-0.5` and `ING-0.6` (zero training examples, absent from the head's 67
classes) are reachable at all.

The expense side is the opposite situation: the supplier writes the line, so a
purchase line that happens to match a client category name proves nothing about
how the client files it. Worse, 15 expense leaves are a single common word
(`BOLOS`, `GAS`, `BENCINA`, `PETROLEO`, `MOVILIZACION`, `CAL`, ...), so an exact
rule on them silently pre-empts real ambiguity: three leaves contain "Bolos",
and Bencina-vs-Movilizacion is still an open client question. Those 67 COMPRAS
rules fired on 19 of 12,103 real lines; they are not worth the risk and are no
longer emitted.

Normalization is used only to absorb case, accents, punctuation, spacing, and
common unit forms; no fuzzy or substring matching is performed.
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
RULE_VERSION = "2026.08.12-v3"
FIELDS = ["rule_version", "transaction_type", "item_text", "category_code", "action", "note"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def direction_for(code: str) -> str:
    return "VENTAS" if code.startswith("ING-") else "COMPRAS"


def is_sales(code: str) -> bool:
    return code.startswith("ING-")


def build(taxonomy_path: Path, aliases_path: Path) -> list[dict[str, str]]:
    taxonomy = read_csv(taxonomy_path)
    aliases = read_csv(aliases_path)
    if len(taxonomy) != 71:
        raise RuntimeError(f"expected 71 active taxonomy rows, found {len(taxonomy)}")

    codes = {row["new_code"].strip() for row in taxonomy}
    rows: list[dict[str, str]] = []
    for row in taxonomy:
        code = row["new_code"].strip()
        # Expense leaves are deliberately skipped; see the module docstring.
        if not is_sales(code):
            continue
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
        if not is_sales(code):
            raise RuntimeError(
                f"expense-side alias is no longer supported, remove it from the alias file: {alias}"
            )
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
    sales_leaves = sum(row["new_code"].strip().startswith("ING-") for row in read_csv(args.taxonomy))
    print({
        "active_taxonomy_leaves": 71,
        "sales_leaves_emitted": sales_leaves,
        "expense_leaves_skipped": 71 - sales_leaves,
        "aliases": len(rows) - sales_leaves,
        "total_rules": len(rows),
        "output": str(args.output),
    })


if __name__ == "__main__":
    main()
