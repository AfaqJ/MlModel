"""Remove what a hand-run glassbox test created, and nothing else.

    python scripts/91_glassbox_test_cleanup.py --since 2026-09-21T09:00:00Z            # dry run
    python scripts/91_glassbox_test_cleanup.py --since ... --requests SOL-2026-0020    # + those requests
    python scripts/91_glassbox_test_cleanup.py --since ... --apply

Why this exists instead of 90_yunt_live_test_undo.py: that script's Test 3 deletes
EVERY purchase request and order with created_via='yunt', which today includes the
Yunt team's real SOL-2026-0016 / OC-2026-0011, and it has no per-test switch.
This one only touches:

  * invoices from the synthetic supplier (RUT 771234567), their lines, the catalog
    rows and company they created, and any batch that holds ONLY those lines;
  * batches, inbound emails, refusals and stored reports created at or after
    --since (UTC). Read the dry run: if the Yunt team was testing in that window
    their rows are in it too;
  * the purchase requests you name with --requests, with their quotations,
    drafts and order. SOL-2026-0016 is refused by name.

Dry run by default. Prints the plan, deletes children before parents.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from supabase_rest import Rest, load_env, quote_in  # noqa: E402

TEST_SELLER_RUT = "771234567"
PROTECTED_REQUESTS = {"SOL-2026-0016"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", required=True, help="UTC time before the test began, e.g. 2026-09-21T09:00:00Z")
    parser.add_argument("--requests", default="", help="comma-separated SOL numbers to remove")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    numbers = [n.strip().upper() for n in args.requests.split(",") if n.strip()]
    refused = PROTECTED_REQUESTS.intersection(numbers)
    if refused:
        raise SystemExit(f"refusing to touch {sorted(refused)}: that is the Yunt team's real request")

    url, key = load_env()
    db = Rest(url, key)
    W = {"allow_writes": args.apply}

    # ---- synthetic invoices and the batches that hold only them --------------
    invoices = db.get("invoices", "invoice_id", f"seller_rut=eq.{TEST_SELLER_RUT}")
    invoice_ids = [r["invoice_id"] for r in invoices]
    items = db.get("invoice_items", "item_id,catalog_item_id", f"invoice_id=in.{quote_in(invoice_ids)}") if invoice_ids else []
    item_ids = {r["item_id"] for r in items}
    catalog_ids = sorted({r["catalog_item_id"] for r in items if r["catalog_item_id"]})

    batches = {b["batch_id"] for b in db.get("yunt_batches", "batch_id", f"created_at=gte.{args.since}")}
    if item_ids:
        batches |= {r["batch_id"] for r in db.get("yunt_batch_items", "batch_id", f"item_id=in.{quote_in(sorted(item_ids))}")}
    for batch in sorted(batches):
        foreign = [r for r in db.get("yunt_batch_items", "item_id", f"batch_id=eq.{batch}") if r["item_id"] not in item_ids]
        if foreign:
            raise SystemExit(f"batch {batch} holds {len(foreign)} line(s) that are not synthetic — refusing")

    # ---- email, refusals, stored reports ------------------------------------
    inbound = db.get("yunt_inbound_requests", "request_id,subject,created_at", f"created_at=gte.{args.since}")
    inbound_ids = [r["request_id"] for r in inbound]

    # ---- named purchase requests --------------------------------------------
    requests = db.get("purchase_requests", "request_id,request_number,status", f"request_number=in.{quote_in(numbers)}") if numbers else []
    request_ids = [r["request_id"] for r in requests]
    missing = set(numbers) - {r["request_number"] for r in requests}
    if missing:
        raise SystemExit(f"no such request: {sorted(missing)}")
    orders = db.get("purchase_orders", "order_id,order_number", f"request_id=in.{quote_in(request_ids)}") if request_ids else []

    print(f"synthetic invoices   {len(invoice_ids)}   lines {len(items)}   catalog candidates {len(catalog_ids)}")
    print(f"batches              {len(batches)}  {sorted(b[:8] for b in batches)}")
    print(f"inbound emails       {len(inbound)}")
    for r in sorted(inbound, key=lambda r: r["created_at"]):
        print(f"    {r['created_at'][:19]}  {r['subject'][:60]}")
    print(f"purchase requests    {[(r['request_number'], r['status']) for r in requests]}   orders {[o['order_number'] for o in orders]}")
    if not args.apply:
        print("\ndry run — nothing was deleted. Re-run with --apply.")
        return

    for batch in sorted(batches):
        for table in ("yunt_flags", "yunt_review_evidence", "yunt_review_chunks", "yunt_review_outbox", "yunt_batch_items"):
            db.delete(table, f"batch_id=eq.{batch}", **W)
    if invoice_ids:
        db.delete("invoice_items", f"invoice_id=in.{quote_in(invoice_ids)}", **W)
        db.delete("invoices", f"seller_rut=eq.{TEST_SELLER_RUT}", **W)
    if catalog_ids:
        # Only catalog rows nothing else points at any more.
        still_used = {r["catalog_item_id"] for r in db.get("invoice_items", "catalog_item_id", f"catalog_item_id=in.{quote_in(catalog_ids)}")}
        orphans = [c for c in catalog_ids if c not in still_used]
        if orphans:
            db.delete("item_catalog", f"catalog_item_id=in.{quote_in(orphans)}", **W)
    db.delete("companies", f"rut=eq.{TEST_SELLER_RUT}", **W)
    for batch in sorted(batches):
        db.delete("yunt_batches", f"batch_id=eq.{batch}", **W)

    if request_ids:
        db.delete("yunt_purchase_order_drafts", f"purchase_request_id=in.{quote_in(request_ids)}", **W)
        db.delete("yunt_purchase_request_drafts", f"purchase_request_id=in.{quote_in(request_ids)}", **W)
        db.delete("purchase_orders", f"request_id=in.{quote_in(request_ids)}", **W)
        db.delete("quotations", f"request_id=in.{quote_in(request_ids)}", **W)
        db.delete("purchase_requests", f"request_id=in.{quote_in(request_ids)}", **W)
    if inbound_ids:
        db.delete("yunt_reports", f"source_request_id=in.{quote_in(inbound_ids)}", **W)
        db.delete("yunt_refusals", f"request_id=in.{quote_in(inbound_ids)}", **W)
        db.delete("yunt_inbound_requests", f"request_id=in.{quote_in(inbound_ids)}", **W)

    print("\ndone. counts now:")
    for table in ("invoices", "invoice_items", "companies", "item_catalog", "yunt_batches",
                  "purchase_requests", "purchase_orders", "yunt_inbound_requests"):
        print(f"  {table:<24}{db.count(table):>7}")


if __name__ == "__main__":
    main()
