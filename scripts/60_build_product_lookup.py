from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "app" / "data" / "product_lookup.csv"


def rows_from_csv(path: Path, source: str):
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            item = (row.get("item_text") or row.get("SERVICIO") or "").strip()
            provider = (row.get("provider") or row.get("PROVEEDOR") or "").strip()
            code = (row.get("category_code") or "").strip()
            if not code and row.get("SUBCUENTA"):
                code = leaf_to_code().get(row["SUBCUENTA"].strip(), "")
            if item and code:
                yield {
                    "item_text": item,
                    "provider": provider,
                    "category_code": code,
                    "rule_source": source,
                }


def leaf_to_code() -> dict[str, str]:
    path = ROOT / "Data" / "current_context_2026_06_30" / "taxonomy_from_plan.csv"
    with open(path, newline="") as handle:
        return {row["leaf"].strip(): row["new_code"].strip() for row in csv.DictReader(handle)}


def main() -> None:
    sources = [
        (ROOT / "Data" / "current_context_2026_06_30" / "product_rules.csv", "client_product_rule"),
        (ROOT / "Data" / "current_context_2026_06_30" / "example_line_rules.csv", "direct_client_example"),
        (ROOT / "Data" / "examples_categories" / "Products list Antillanca(Servicios).csv", "client_service_rule"),
    ]
    seen = set()
    rows = []
    for path, source in sources:
        for row in rows_from_csv(path, source):
            key = (row["item_text"].upper(), row["provider"].upper(), row["category_code"])
            if key not in seen:
                seen.add(key)
                rows.append(row)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["item_text", "provider", "category_code", "rule_source"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
