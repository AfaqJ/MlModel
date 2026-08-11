from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.inference.normalize import normalize_text


OUT = ROOT / "app" / "data" / "product_lookup.csv"

# User-resolved authority conflict: row-level product labels beat the invoice's
# category-folder placement. The client labels the L/M/S members of this Shoof
# nitrile-glove family as work clothing/EPP, so XL follows the same product
# family instead of the unrelated lines in its folder invoice.
PRODUCT_FAMILY_RESOLUTIONS = [
    {
        "item_text": "GUANTE LARGO NITRILO XL SHOOF 204630",
        "provider": "",
        "category_code": "EXP-16.1",
        "rule_source": "client_product_family_resolution",
    },
]


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
        (ROOT / "Data" / "current_context_2026_06_30" / "example_line_rules.csv", "direct_client_example"),
        (ROOT / "Data" / "current_context_2026_06_30" / "product_rules.csv", "client_product_rule"),
    ]
    authority = {
        "direct_client_example": 10,
        "client_service_rule": 20,
        "client_product_rule": 30,
        "direct_client_family_resolution": 40,
        "client_product_family_resolution": 50,
    }
    rows_by_key: dict[tuple[str, str], dict[str, str]] = {}

    def add(row: dict[str, str]) -> None:
        key = (normalize_text(row["item_text"]), normalize_text(row["provider"]))
        existing = rows_by_key.get(key)
        if not existing or authority.get(row["rule_source"], 0) > authority.get(existing["rule_source"], 0):
            rows_by_key[key] = row
        elif (
            authority.get(row["rule_source"], 0) == authority.get(existing["rule_source"], 0)
            and row["category_code"] != existing["category_code"]
        ):
            raise RuntimeError(f"equal-authority lookup conflict for {key}: {existing} versus {row}")

    for path, source in sources:
        for row in rows_from_csv(path, source):
            add(row)

    # The audited recovery candidate also contains trustworthy exact mappings
    # from the client's newest product/example workbooks that were missing from
    # the older lookup build inputs. Do not import silver or manual ML labels.
    candidate = ROOT / "Data/candidates/recovery_v1_3_1/master_gold.csv"
    trusted_sources = {
        "client_product_rule", "direct_client_example", "client_service_rule",
        "direct_client_family_resolution", "client_product_family_resolution",
    }
    if candidate.exists():
        with candidate.open(encoding="utf-8-sig", newline="") as handle:
            for source_row in csv.DictReader(handle):
                if source_row.get("source") not in trusted_sources:
                    continue
                row = {
                    "item_text": source_row["item_text"].strip(),
                    "provider": source_row.get("provider", "").strip(),
                    "category_code": source_row["category_code"].strip(),
                    "rule_source": source_row["source"],
                }
                add(row)

    for row in PRODUCT_FAMILY_RESOLUTIONS:
        add(row)

    rows = [rows_by_key[key] for key in sorted(rows_by_key)]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["item_text", "provider", "category_code", "rule_source"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
