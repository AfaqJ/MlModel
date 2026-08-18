"""Apply only the corrections Afaq explicitly confirmed on 2026-08-17.

This is a local payload correction. It does not contact Supabase; script 82 is
the separate, explicitly-confirmed uploader.

The recovered audit incorrectly called 103 DTE-43 auction rows animal sales.
They are COMPRAS rows and remain AF-1.1 Purchases of Animals. This script does
not touch them.

Every target below is an exact invoice-line identifier, not a supplier or
keyword sweep. That is deliberate: client conventions beat audit guesses, and
the rows moved to review are unresolved rather than silently relabelled.

Run with no flags for a dry run; --write to save.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
UPLOAD = ROOT / "reports/recovery_v1_3_3/supabase_upload"
REPORT = ROOT / "reports/client_reply_2026_08_17"
SUFFIX = ".bak_pre_confirmedtriage"

FOOD, FOOD_NAME = "EXP-1.1", "Otros Gastos RRHH"
MEALS, MEALS_NAME = "ADM-1.5", "Colacion y Alojamiento"

# Client rule: supermarket food and drink belong in Other HR Costs.
FOOD_IDS = {
    "COMPRAS|81201000K|24168223|4",
    "COMPRAS|81201000K|25771159|12",
    "COMPRAS|815376005|41329900|9",
    "COMPRAS|815376005|41329900|15",
    "COMPRAS|815376005|42598882|3",
    "COMPRAS|815376005|42715690|7",
    "COMPRAS|815376005|43024983|2",
    "COMPRAS|815376005|43024983|9",
    "COMPRAS|815376005|43287292|5",
    "COMPRAS|815376005|43287292|6",
    "COMPRAS|815376005|43287292|9",
    "COMPRAS|815376005|43287292|11",
    "COMPRAS|815376005|43287292|14",
}

# Client-labelled restaurant, hotel, and cafe meals belong in Meals & Lodging.
MEAL_IDS = {
    "COMPRAS|54232675|2866|1",      # Dinner for 41 people
    "COMPRAS|780852186|21|1",       # Empanadas from hotel/cafe supplier
}

# The client did not establish the correct category for these. They cannot
# remain final answers merely because a word looked like food.
NON_FOOD_REVIEW_IDS = {
    "COMPRAS|98124942|352|1",       # Baked empanadas; client filing conflicts
    "COMPRAS|66554732|243355|1",    # Dark-brown acrylic grout
    "COMPRAS|810941006|29936574|4", # Apple-scented windscreen washer
    "COMPRAS|810941006|29936592|1", # Apple-scented windscreen washer
}

# Raw <Patente> values that are neither a client-confirmed vehicle plate nor
# the client-confirmed BIDON spelling. The recovered audit's 13-row total is
# reproducible only when ENV000 is included.
CONTAINER_REVIEW_IDS = {
    "COMPRAS|777854402|500978|1",
    "COMPRAS|777854402|514430|1",
    "COMPRAS|777854402|522162|1",
    "COMPRAS|777854402|528303|1",
    "COMPRAS|777854402|528303|2",
    "COMPRAS|777854402|530452|1",
    "COMPRAS|777854402|532402|1",
    "COMPRAS|777854402|535126|1",
    "COMPRAS|777854402|538712|1",
    "COMPRAS|777854402|541166|1",
    "COMPRAS|777854402|545398|1",
    "COMPRAS|777854402|546958|1",
    "COMPRAS|777854402|553773|1",
}

# The recovered note said 28 rows. Raw XML proves only these 11 exact rows
# have the named junk values from Patricio Santiago Carey Briones; do not invent
# the other 17 targets.
JUNK_PLATE_REVIEW_IDS = {
    "COMPRAS|57884150|242147|1",
    "COMPRAS|57884150|242570|1",
    "COMPRAS|57884150|242572|1",
    "COMPRAS|57884150|264733|1",
    "COMPRAS|57884150|265356|1",
    "COMPRAS|57884150|276017|1",
    "COMPRAS|57884150|277437|1",
    "COMPRAS|57884150|277518|1",
    "COMPRAS|57884150|280476|1",
    "COMPRAS|57884150|282857|1",
    "COMPRAS|57884150|283966|1",
}


def input_id(row: dict) -> str:
    """Natural key used in the evidence reports for this COMPRAS-only set."""
    return f"COMPRAS|{row['_seller_rut']}|{row['_invoice_folio']}|{row['invoice_line_number']}"


def assign(row: dict, code: str, name: str) -> None:
    row["predicted_code"] = code
    row["predicted_name"] = name
    row["predicted_categories_id"] = None  # remapped from live when script 82 uploads
    row["prediction_source"] = "business_rule"
    row["decision"] = "auto_accept"
    row["final_code"] = code
    row["final_categories_id"] = None


def require_review(row: dict) -> None:
    # Keep the existing predicted category as a reviewer hint, but never expose
    # it as a settled answer.
    row["decision"] = "review_required"
    row["final_code"] = None
    row["final_categories_id"] = None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="save; otherwise dry run")
    args = ap.parse_args()

    path = UPLOAD / "invoice_items.jsonl"
    items = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    by_id = {input_id(row): row for row in items}
    if len(by_id) != len(items):
        raise AssertionError("invoice-item natural keys are not unique")

    groups = {
        "client supermarket-food rule": (FOOD_IDS, lambda row: assign(row, FOOD, FOOD_NAME)),
        "client restaurant-meal rule": (MEAL_IDS, lambda row: assign(row, MEALS, MEALS_NAME)),
        "not food; category unresolved": (NON_FOOD_REVIEW_IDS, require_review),
        "unrecognised container/plate value": (CONTAINER_REVIEW_IDS, require_review),
        "unrecognised plate value": (JUNK_PLATE_REVIEW_IDS, require_review),
    }
    all_ids = set().union(*(ids for ids, _ in groups.values()))
    assert sum(len(ids) for ids, _ in groups.values()) == len(all_ids), "overlapping target groups"
    missing = all_ids - set(by_id)
    assert not missing, f"targets no longer exist in payload: {sorted(missing)}"

    changes = []
    for reason, (ids, operation) in groups.items():
        for key in sorted(ids):
            row = by_id[key]
            was = (row["predicted_code"], row["decision"], row["final_code"])
            operation(row)
            changes.append({
                "input_id": key,
                "item": row["item_text"],
                "was_code": was[0],
                "was_decision": was[1],
                "was_final_code": was[2],
                "now_code": row["predicted_code"],
                "now_decision": row["decision"],
                "now_final_code": row["final_code"],
                "why": reason,
                "amount": row["amount"],
            })

    review_changes = [change for change in changes if change["now_decision"] == "review_required"]
    accepted_changes = [change for change in changes if change["now_decision"] == "auto_accept"]
    print(f"{len(changes)} confirmed corrections  CLP {sum(c['amount'] for c in changes):,.0f}")
    print(f"  {len(accepted_changes)} auto_accept, {len(review_changes)} review_required")
    for reason, (ids, _) in groups.items():
        selected = [change for change in changes if change["why"] == reason]
        print(f"  {reason:36} {len(selected):2} rows  CLP {sum(c['amount'] for c in selected):>12,.0f}")

    assert len(changes) == 43, f"expected 43 confirmed corrections, matched {len(changes)}"
    assert len(accepted_changes) == 15, "expected 15 client-rule auto-accepts"
    assert len(review_changes) == 28, "expected 28 rows moved to review"
    assert all((row["decision"] == "auto_accept") == bool(row["final_code"]) for row in items), \
        "a row shows a label while awaiting review"

    if not args.write:
        print("\n(dry run — re-run with --write)")
        return

    backup = path.with_suffix(path.suffix + SUFFIX)
    if not backup.exists():
        backup.write_bytes(path.read_bytes())
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in items))

    REPORT.mkdir(parents=True, exist_ok=True)
    with (REPORT / "confirmed_triage_corrections.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(changes[0]))
        writer.writeheader()
        writer.writerows(changes)
    print(f"\nwritten. backup at *{SUFFIX}, changelog at "
          f"{REPORT.relative_to(ROOT)}/confirmed_triage_corrections.csv")


if __name__ == "__main__":
    main()
