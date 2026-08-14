"""Overwrite a Supabase that already holds v1.3.3 with the corrected payload.

`80_upload_to_supabase.py` is the first-load script: its pre-flight expects a
pre-v1.3.3 database and refuses once that upload has landed. This is the
re-load. It pushes every row of the current payload with all columns, then
removes live rows the payload no longer contains.

Schema is never touched — no table is created or dropped, so the frontend is
unaffected. Rows are replaced in place.

Full rows matter: PostgREST upsert is INSERT ... ON CONFLICT, so a partial
payload fails the insert arm on every NOT NULL column it omits.

Dry run by default. Writing needs --execute and --i-have-backed-up-the-database,
the same contract as script 80 — the backup is the only rollback.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from supabase_rest import Rest, load_env  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
UPLOAD = ROOT / "reports/recovery_v1_3_3/supabase_upload"


def read_jsonl(name: str) -> list[dict]:
    path = UPLOAD / name
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def strip_keys(row: dict) -> dict:
    """Drop the natural-key helpers; they are not columns."""
    return {k: v for k, v in row.items() if not k.startswith("_")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true", help="actually write")
    ap.add_argument("--i-have-backed-up-the-database", action="store_true",
                    help="required alongside --execute; the backup is the only rollback")
    args = ap.parse_args()
    if args.execute and not args.i_have_backed_up_the_database:
        sys.exit("--execute also needs --i-have-backed-up-the-database.")
    write = args.execute
    print("EXECUTING — writes are live\n" if write else "DRY RUN — nothing is written\n")

    rest = Rest(*load_env())
    categories = read_jsonl("categories.jsonl")
    companies = read_jsonl("companies.jsonl")
    catalog = read_jsonl("item_catalog.jsonl")
    invoices = read_jsonl("invoices.jsonl")
    items = read_jsonl("invoice_items.jsonl")

    # ---- 1-3: leaf tables, no foreign keys ------------------------------
    for name, rows, conflict in (("categories", categories, "code"),
                                 ("companies", companies, "rut"),
                                 ("item_catalog", catalog, "item_name,description")):
        print(f"1. {name}: {len(rows)} rows -> upsert on ({conflict})")
        if write:
            rest.upsert(name, rows, conflict, allow_writes=True)

    # ---- 4: invoices need company_id ------------------------------------
    company_id = {r["rut"]: r["company_id"] for r in rest.get("companies", "company_id,rut")}
    missing = {r["_company_rut"] for r in invoices} - set(company_id)
    if missing and write:
        sys.exit(f"{len(missing)} invoice company RUTs are not in companies, e.g. {sorted(missing)[:3]}")
    print(f"2. invoices: {len(invoices)} rows ({len(company_id)} companies resolved)")
    if write:
        rest.upsert("invoices", [{**strip_keys(r), "company_id": company_id[r["_company_rut"]]}
                                 for r in invoices],
                    "seller_rut,document_type,invoice_folio", allow_writes=True)

    # ---- 5: items need invoice_id, catalog_item_id, and live category ids -
    invoice_id = {(r["seller_rut"], str(r["document_type"]), str(r["invoice_folio"])): r["invoice_id"]
                  for r in rest.get("invoices", "invoice_id,seller_rut,document_type,invoice_folio")}
    catalog_id = {(r["item_name"], r.get("description") or ""): r["catalog_item_id"]
                  for r in rest.get("item_catalog", "catalog_item_id,item_name,description")}
    # the database generates categories_id, so any id in the payload is meaningless
    cat_id = {r["code"]: r["categories_id"] for r in rest.get("categories", "categories_id,code")}

    item_rows, unresolved = [], []
    for row in items:
        ikey = (row["_seller_rut"], str(row["_document_type"]), str(row["_invoice_folio"]))
        ckey = (row["_catalog_item_name"], row["_catalog_description"] or "")
        if ikey not in invoice_id or ckey not in catalog_id:
            unresolved.append((ikey, ckey))
            continue
        out = strip_keys(row)
        out["invoice_id"] = invoice_id[ikey]
        out["catalog_item_id"] = catalog_id[ckey]
        out["predicted_categories_id"] = cat_id.get(out["predicted_code"])
        out["final_categories_id"] = cat_id.get(out["final_code"]) if out["final_code"] else None
        if out["predicted_code"] and not out["predicted_categories_id"]:
            sys.exit(f"no live category row for {out['predicted_code']}")
        item_rows.append(out)
    if unresolved and write:
        sys.exit(f"{len(unresolved)} item rows could not resolve their foreign keys, e.g. {unresolved[:2]}")
    print(f"3. invoice_items: {len(item_rows)} rows resolved"
          + (f"  ({len(unresolved)} unresolved — dry run only)" if unresolved else ""))
    if write:
        rest.upsert("invoice_items", item_rows, "invoice_id,invoice_line_number", allow_writes=True)

    # ---- 6: drop live rows the payload no longer has ---------------------
    ours = {(r["invoice_id"], r["invoice_line_number"]) for r in item_rows}
    live = {(r["invoice_id"], r["invoice_line_number"])
            for r in rest.get("invoice_items", "invoice_id,invoice_line_number")}
    stale = sorted(live - ours)
    print(f"4. live rows not in the payload: {len(stale)} to delete")
    if write:
        for iid, line in stale:
            rest.delete("invoice_items",
                        f"invoice_id=eq.{iid}&invoice_line_number=eq.{line}", allow_writes=True)

    if not write:
        print("\n   (dry run — re-run with --execute --i-have-backed-up-the-database)")
        return

    # ---- 7: verify -------------------------------------------------------
    after = {(r["invoice_id"], r["invoice_line_number"]): r
             for r in rest.get("invoice_items",
                               "invoice_id,invoice_line_number,item_text,predicted_code,"
                               "final_code,decision,predicted_categories_id")}
    want = {(r["invoice_id"], r["invoice_line_number"]): r for r in item_rows}
    problems = []
    if len(after) != len(want):
        problems.append(f"row count {len(after)} != expected {len(want)}")
    diff = sum(1 for k, v in want.items()
               if k not in after
               or after[k]["predicted_code"] != v["predicted_code"]
               or after[k]["decision"] != v["decision"]
               or after[k]["item_text"] != v["item_text"])
    if diff:
        problems.append(f"{diff} rows did not take the update")
    bad = sum(1 for r in after.values() if (r["decision"] == "auto_accept") != bool(r["final_code"]))
    if bad:
        problems.append(f"{bad} rows show a label while awaiting review")
    noid = sum(1 for r in after.values() if r["predicted_code"] and not r["predicted_categories_id"])
    if noid:
        problems.append(f"{noid} rows have no category id")

    print(f"\n5. verify: {len(after)} live rows")
    if problems:
        sys.exit("verification FAILED: " + "; ".join(problems))
    print("   row count, labels, decisions, item names, category ids — all match")


if __name__ == "__main__":
    main()
