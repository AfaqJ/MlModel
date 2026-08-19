"""Correct the one auto-accepted row that contradicts a client product rule.

Every auto-accepted row in the payload was checked against the products the
client decided himself (`client_product_rule`, `direct_client_example`,
`client_service_rule` and the family resolutions), matched on product identity
with sizes and codes stripped. Result: **1 of 7,286**.

  SULFATO COBRE 25 KG.  ->  EXP-7.0 AGROQUIMICOS   (manually audited backfill)
  SULFATO DE COBRE X 25 KL. -> EXP-16.2 Otros Gastos Campo  (client_product_rule,
                                                             3 rows auto-accepted)

Same product, different supplier's wording -- so one of the two is wrong.

**Afaq's call 2026-08-18: none of these are auto-accepted, all go to review.**
He doubts the client's own rule here, and copper sulphate genuinely reads as an
agrochemical: it is a fungicide, and on a dairy it is also the standard hoof
footbath. The client rule may have been written from the name rather than the
use. So the contradiction is not resolved in either direction -- the row is
demoted to review, keeps the agrochemical hint the model and Afaq both read, and
the question goes to the client.

The three `SULFATO DE COBRE X 25 KL.` rows auto-accepted from `product_lookup`
are left alone: those ARE the client's rule, and overturning a client decision
without asking him is exactly what D-030 forbids. If he answers that copper
sulphate is an agrochemical, those three move too.

Notably clean: `silver_audit_backfill` contradicts a client product decision in
**0 of its 365** auto-accepted rows, and `product_lookup` in 0 of 2,639.

Run with no flags for a dry run; --write to save.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPLOAD = ROOT / "reports/recovery_v1_3_3/supabase_upload"
SUFFIX = ".bak_pre_sulfato"

TARGET, TARGET_NAME = "EXP-16.2", "Otros Gastos Campo"
PROOF = "SULFATO DE COBRE X 25 KL."


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="save; otherwise dry run")
    args = parser.parse_args()

    path = UPLOAD / "invoice_items.jsonl"
    items = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

    proven = [r for r in items if (r.get("item_text") or "").strip() == PROOF
              and r["decision"] == "auto_accept" and r["final_code"] == TARGET
              and r["prediction_source"] == "product_lookup"]
    assert proven, f"the client rule proving {PROOF!r} -> {TARGET} is gone"

    changes = []
    for row in items:
        text = (row.get("item_text") or "").upper()
        if "SULFATO" not in text or "COBRE" not in text:
            continue
        if row["prediction_source"] == "product_lookup":
            continue  # the client's own rule; only he may overturn it
        was, decision = row["final_code"] or row["predicted_code"], row["decision"]
        row["decision"] = "review_required"
        row["final_code"] = None
        row["final_categories_id"] = None
        row["predicted_categories_id"] = None
        row["prediction_source"] = "manual_recategorisation"
        changes.append((row.get("item_text"), was, decision, row["amount"]))

    for item, was, decision, amount in changes:
        print(f"   {item[:34]:34} was {was} ({decision}) -> review_required, "
              f"hint {was}  CLP {amount:,.0f}")
    print(f"{len(changes)} rows held in review pending the client's answer")

    assert all((r["decision"] == "auto_accept") == bool(r["final_code"]) for r in items), \
        "a row shows a label while awaiting review"
    assert len(changes) == 3, f"expected 3 copper-sulphate rows, matched {len(changes)}"
    assert not any(r["decision"] == "auto_accept" and "SULFATO" in (r.get("item_text") or "").upper()
                   and "COBRE" in (r.get("item_text") or "").upper()
                   and r["prediction_source"] != "product_lookup" for r in items), \
        "a copper-sulphate row outside the client's own rule is still auto-accepted"

    if not args.write:
        print("\n(dry run — re-run with --write)")
        return
    backup = path.with_suffix(path.suffix + SUFFIX)
    if not backup.exists():
        backup.write_bytes(path.read_bytes())
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in items))
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
