#!/usr/bin/env python3
"""Push the v1.3.3 payload into Supabase through PostgREST.

PostgREST cannot wrap five tables in one transaction, so this migration cannot
be rolled back by the database. Three things compensate:

1. **Ordering.** Dependencies land before dependants, so a failure at any stage
   leaves a database that is *valid*, merely partially updated - never one with
   dangling references.
2. **Stop on first mismatch.** Every stage verifies its own result against the
   expected count and aborts rather than continuing on a wrong assumption.
3. **Idempotence.** Every write is an upsert on a business key or a delete of an
   already-identified row, so a failed run can simply be run again.

The user's backup is the real rollback. Writing therefore requires both
`--execute` and `--i-have-backed-up-the-database`; neither alone is enough, and
the default is a dry run that touches nothing.

Stage 7 deliberately re-queries the live database instead of trusting the
pre-flight: it is the only destructive step whose safety depends on an earlier
step having actually completed.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from supabase_rest import Rest, chunks, load_env, quote_in  # noqa: E402

UPLOAD = ROOT / "reports/recovery_v1_3_3/supabase_upload"
LOG = ROOT / "reports/recovery_v1_3_3/upload_log.jsonl"

EXPECTED_AFTER = {
    "categories": 71,
    "companies": 461,
    "item_catalog": 5402,
    "invoices": 5195,
    "invoice_items": 11766,
}


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def strip_natural_keys(row: dict) -> dict:
    return {key: value for key, value in row.items() if not key.startswith("_")}


def resolved_map(live: dict, payload_keys, execute: bool, label: str) -> dict:
    """Ids as they will exist once the preceding upsert stages have run.

    On a real run the map is exactly what the database returned. On a dry run
    the rows that stage would have inserted do not exist yet, so they are filled
    with a placeholder - otherwise the dry run reports a failure to resolve a
    key that a real run would have created moments earlier, and the rest of the
    chain never gets validated.
    """
    if execute:
        return live
    merged = dict(live)
    for index, key in enumerate(sorted(set(payload_keys) - set(live), key=str)):
        merged[key] = f"dry-run-{label}-{index}"
    return merged


class Runner:
    def __init__(self, rest: Rest, log_path: Path, execute: bool):
        self.rest = rest
        self.log_path = log_path
        self.execute = execute
        self.stage = 0

    def record(self, name: str, detail: dict) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "at": datetime.now(timezone.utc).isoformat(),
                "stage": self.stage, "name": name, "executed": self.execute, **detail,
            }, ensure_ascii=False) + "\n")

    def begin(self, name: str) -> None:
        self.stage += 1
        print(f"\n[{self.stage}] {name}")

    def expect(self, label: str, actual: int, expected: int) -> None:
        ok = actual == expected
        print(f"      {'ok  ' if ok else 'FAIL'} {label}: {actual} (expected {expected})")
        self.record(label, {"actual": actual, "expected": expected, "ok": ok})
        if not ok and self.execute:
            raise SystemExit(
                f"\nABORTED at stage {self.stage}: {label} is {actual}, expected {expected}.\n"
                f"The database is partially updated but valid. Inspect, then re-run - "
                f"every write is idempotent."
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upload", type=Path, default=UPLOAD)
    parser.add_argument("--log", type=Path, default=LOG)
    parser.add_argument("--execute", action="store_true", help="actually write")
    parser.add_argument("--i-have-backed-up-the-database", action="store_true",
                        help="required alongside --execute; there is no rollback")
    parser.add_argument("--verify-only", action="store_true", help="run only the final checks")
    args = parser.parse_args()

    execute = args.execute and args.i_have_backed_up_the_database
    if args.execute and not args.i_have_backed_up_the_database:
        raise SystemExit(
            "--execute also needs --i-have-backed-up-the-database.\n"
            "PostgREST gives no transaction, so your backup is the only rollback."
        )

    rest = Rest(*load_env())
    runner = Runner(rest, args.log, execute)

    if args.verify_only:
        verify(rest)
        return

    categories = read_jsonl(args.upload / "categories.jsonl")
    companies = read_jsonl(args.upload / "companies.jsonl")
    catalog = read_jsonl(args.upload / "item_catalog.jsonl")
    invoices = read_jsonl(args.upload / "invoices.jsonl")
    items = read_jsonl(args.upload / "invoice_items.jsonl")
    junk = read_jsonl(args.upload / "reconcile_delete_junk_lines.jsonl")
    prune = read_jsonl(args.upload / "prune_orphan_catalog_rows.jsonl")

    mode = "EXECUTE — writing to the live database" if execute else "DRY RUN — nothing will be written"
    print(f"{mode}\n  {len(categories)} categories, {len(companies)} companies, {len(catalog)} catalog, "
          f"{len(invoices)} invoices, {len(items)} items, {len(junk)} junk keys, {len(prune)} prune targets")

    # ---- 1-3: leaf tables, no foreign keys ------------------------------
    for name, rows, conflict, expected in (
        ("categories", categories, "code", EXPECTED_AFTER["categories"]),
        ("companies", companies, "rut", EXPECTED_AFTER["companies"]),
        ("item_catalog", catalog, "item_name,description", None),
    ):
        runner.begin(f"upsert {name} ({len(rows)} rows)")
        if execute:
            rest.upsert(name, rows, conflict, allow_writes=True)
        if expected is not None:
            runner.expect(f"{name} rows", rest.count(name) if execute else expected, expected)

    # item_catalog is verified after the prune, not here: the upsert adds 48
    # before anything is removed, so mid-migration it is legitimately 5,627.

    # ---- 4: invoices need company_id ------------------------------------
    runner.begin(f"upsert invoices ({len(invoices)} rows)")
    company_id = resolved_map(
        {r["rut"]: r["company_id"] for r in rest.get("companies", "company_id,rut")},
        [r["rut"] for r in companies], execute, "company")
    missing = {r["_company_rut"] for r in invoices} - set(company_id)
    if missing:
        raise SystemExit(f"{len(missing)} invoice company RUTs are not in companies: {sorted(missing)[:3]}")
    invoice_rows = [{**strip_natural_keys(r), "company_id": company_id[r["_company_rut"]]} for r in invoices]
    if execute:
        rest.upsert("invoices", invoice_rows, "seller_rut,document_type,invoice_folio", allow_writes=True)
    runner.expect("invoices rows", rest.count("invoices") if execute else EXPECTED_AFTER["invoices"],
                  EXPECTED_AFTER["invoices"])

    # ---- 5: items need invoice_id and catalog_item_id -------------------
    runner.begin(f"upsert invoice_items ({len(items)} rows)")
    invoice_id = resolved_map(
        {(r["seller_rut"], str(r["document_type"]), str(r["invoice_folio"])): r["invoice_id"]
         for r in rest.get("invoices", "invoice_id,seller_rut,document_type,invoice_folio")},
        [(r["seller_rut"], str(r["document_type"]), str(r["invoice_folio"])) for r in invoices],
        execute, "invoice")
    catalog_id = resolved_map(
        {(r["item_name"], r.get("description") or ""): r["catalog_item_id"]
         for r in rest.get("item_catalog", "catalog_item_id,item_name,description")},
        [(r["item_name"], r["description"]) for r in catalog], execute, "catalog")
    item_rows, unresolved = [], []
    for row in items:
        key = (row["_seller_rut"], str(row["_document_type"]), str(row["_invoice_folio"]))
        catalog_key = (row["_catalog_item_name"], row["_catalog_description"])
        if key not in invoice_id or catalog_key not in catalog_id:
            unresolved.append((key, catalog_key))
            continue
        item_rows.append({
            **strip_natural_keys(row),
            "invoice_id": invoice_id[key],
            "catalog_item_id": catalog_id[catalog_key],
        })
    if unresolved:
        raise SystemExit(f"{len(unresolved)} item rows could not resolve their FKs, e.g. {unresolved[:2]}")
    if execute:
        rest.upsert("invoice_items", item_rows, "invoice_id,invoice_line_number", allow_writes=True)
    print(f"      resolved all {len(item_rows)} item rows to invoice_id + catalog_item_id")

    # ---- 6: delete the junk lines ---------------------------------------
    runner.begin("delete audited junk item rows")
    by_invoice: defaultdict[str, list[int]] = defaultdict(list)
    absent = 0
    for row in junk:
        key = (row["seller_rut"], str(row["document_type"]), str(row["invoice_folio"]))
        if key in invoice_id:
            by_invoice[invoice_id[key]].append(int(row["invoice_line_number"]))
        else:
            absent += 1
    targeted = sum(len(v) for v in by_invoice.values())
    if execute:
        for uuid, lines in by_invoice.items():
            for batch in chunks(sorted(lines), 200):
                rest.delete(
                    "invoice_items",
                    f"invoice_id=eq.{uuid}&invoice_line_number=in.({','.join(map(str, batch))})",
                    allow_writes=True,
                )
    after = rest.count("invoice_items") if execute else EXPECTED_AFTER["invoice_items"]
    print(f"      {len(junk)} keys in file, {targeted} target live invoices, {absent} name unknown invoices")
    runner.expect("invoice_items rows", after, EXPECTED_AFTER["invoice_items"])

    # ---- 7: prune orphan catalog rows -----------------------------------
    runner.begin(f"prune orphan catalog rows ({len(prune)})")
    live_catalog = rest.get("item_catalog", "catalog_item_id,item_name,description")
    identity = {(r["item_name"], r.get("description") or ""): r["catalog_item_id"] for r in live_catalog}
    prune_ids = [identity[(r["item_name"], r["description"])]
                 for r in prune if (r["item_name"], r["description"]) in identity]
    # Re-checked live rather than trusted from the pre-flight: this is the only
    # destructive step whose safety depends on stage 6 having actually run.
    still_referenced = 0
    if execute:
        for batch in chunks(prune_ids, 100):
            still_referenced += rest.count("invoice_items", f"catalog_item_id=in.{quote_in(batch)}")
    print(f"      {len(prune_ids)} targets resolved; live item rows still referencing them: {still_referenced}")
    if still_referenced:
        raise SystemExit(
            f"ABORTED before pruning: {still_referenced} item rows still reference these catalog rows.\n"
            f"Stage 6 did not remove everything it should have. Nothing was deleted from item_catalog."
        )
    if execute:
        for batch in chunks(prune_ids, 100):
            rest.delete("item_catalog", f"catalog_item_id=in.{quote_in(batch)}", allow_writes=True)
    runner.expect("item_catalog rows",
                  rest.count("item_catalog") if execute else EXPECTED_AFTER["item_catalog"],
                  EXPECTED_AFTER["item_catalog"])

    # ---- 8 ---------------------------------------------------------------
    runner.begin("verify")
    if execute:
        verify(rest)
    else:
        print("      (dry run — re-run with --execute --i-have-backed-up-the-database)")
        print(f"\nDRY RUN complete. {rest.writes} writes performed (must be 0).")


def verify(rest: Rest) -> None:
    failures: list[str] = []

    def assert_count(label: str, actual: int, expected: int) -> None:
        ok = actual == expected
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}: {actual} (expected {expected})")
        if not ok:
            failures.append(label)

    for table, expected in EXPECTED_AFTER.items():
        assert_count(table, rest.count(table), expected)

    assert_count("final_code set", rest.count("invoice_items", "final_code=not.is.null"), 6583)
    assert_count("needs_review true", rest.count("invoice_items", "needs_review=is.true"), 5183)
    assert_count("reviewed true", rest.count("invoice_items", "reviewed=is.true"), 0)
    assert_count("final_code null but final_categories_id set",
                 rest.count("invoice_items", "final_code=is.null&final_categories_id=not.is.null"), 0)

    # predicted_categories_id must agree with predicted_code on every row.
    categories = {r["categories_id"]: r["code"] for r in rest.get("categories", "categories_id,code")}
    rows = rest.get("invoice_items", "predicted_code,predicted_categories_id,final_code,final_categories_id")
    mismatched = sum(1 for r in rows if categories.get(r["predicted_categories_id"]) != r["predicted_code"])
    assert_count("predicted_categories_id disagrees with predicted_code", mismatched, 0)
    final_mismatch = sum(
        1 for r in rows
        if r["final_code"] and categories.get(r["final_categories_id"]) != r["final_code"]
    )
    assert_count("final_categories_id disagrees with final_code", final_mismatch, 0)

    # The original incident: sales must land in income categories.
    ventas = {r["invoice_id"] for r in rest.get("invoices", "invoice_id,transaction_type",
                                                "transaction_type=eq.VENTAS")}
    compras = {r["invoice_id"] for r in rest.get("invoices", "invoice_id,transaction_type",
                                                 "transaction_type=eq.COMPRAS")}
    lines = rest.get("invoice_items", "invoice_id,predicted_code,decision")
    sales = [r for r in lines if r["invoice_id"] in ventas]
    assert_count("VENTAS lines", len(sales), 125)
    assert_count("VENTAS auto-accepted into ING-*",
                 sum(1 for r in sales if r["decision"] == "auto_accept"
                     and r["predicted_code"].startswith("ING-")), 118)
    assert_count("VENTAS in review", sum(1 for r in sales if r["decision"] != "auto_accept"), 7)
    assert_count("VENTAS auto-accepted on a non-income code",
                 sum(1 for r in sales if r["decision"] == "auto_accept"
                     and not r["predicted_code"].startswith("ING-")), 0)
    assert_count("COMPRAS auto-accepted on an income code",
                 sum(1 for r in lines if r["invoice_id"] in compras and r["decision"] == "auto_accept"
                     and r["predicted_code"].startswith("ING-")), 0)

    if failures:
        raise SystemExit(f"\nVERIFICATION FAILED ({len(failures)}): {', '.join(failures)}")
    print("\nall verification checks passed")


if __name__ == "__main__":
    main()
