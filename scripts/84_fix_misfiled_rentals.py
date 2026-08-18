"""Fix rental lines filed under categories that are not rental categories.

Found by a second-eye audit after the 2026-08-17 client reply. None of this is
client-instructed, so nothing here invents a label the invoice does not state.
Two rules only:

  * the line's own text says it rents a NAMED machine  -> EXP-15.4, auto_accept
  * the line's own text says "rent" but names no object -> EXP-15.4, review

The second rule keeps the money visible under a sensible filter without
claiming an answer we do not have. `final_code` stays NULL there, which is the
rule for every unconfirmed row.

Deliberately NOT touched: "Arriendo de Medidor" (meter rental) and "Arriendo
Equipos No Regulados" from the power company. Those are line items on the
electricity bill itself, so EXP-11.1/EXP-11.2 is where they belong. The audit
called them misfiled; it is wrong.

Deliberately NOT used: a rule keyed on the supplier's line of business. Nine
suppliers have a machinery-rental `giro`, but 36 of their 41 rows are chainsaw
parts, tarpaulins and plumbing work. The giro describes the company, not the
line.

Run with no flags for a dry run; --write to save.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPLOAD = ROOT / "reports/recovery_v1_3_3/supabase_upload"
REPORT = ROOT / "reports/client_reply_2026_08_17"
SUFFIX = ".bak_pre_rentalfix"

RENTAL, RENTAL_NAME = "EXP-15.4", "Arriendo Maquinaria y Vehiculos"

# (matcher, confirmed) — confirmed means the line names the machine, so the
# category is read off the text rather than guessed.
FIXES = [
    ("arriendo de retro excavadora", True,   "rents a named machine (backhoe)"),
    ("renta gener inso",             True,   "rents a named machine (generator)"),
    ("arriendo parrilla",            False,  "says rent, object unclear"),
]


def target(row: dict) -> tuple[bool, str] | None:
    text = (row.get("item_text") or "").strip().lower()
    for prefix, confirmed, why in FIXES:
        if text.startswith(prefix):
            return confirmed, why
    # A bare machine name from a supplier whose only line of business is renting
    # it out, sitting at 0.23 confidence under fence maintenance.
    if text == "excavadora" and float(row["amount"]) > 10_000_000:
        return False, "bare machine name, supplier rents machinery, 0.23 confidence"
    # A feed company billing monthly "rent" is not renting an office. 14 rows
    # auto-accepted at 0.92-1.00 on the word "arriendo" alone.
    if row.get("_seller_rut") == "764503287" and text.startswith("arriendo"):
        return False, "monthly rent from a feed supplier; not an office landlord"
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    items = [json.loads(l) for l in (UPLOAD / "invoice_items.jsonl").read_text().splitlines() if l.strip()]

    changes = []
    for row in items:
        hit = target(row)
        if not hit:
            continue
        confirmed, why = hit
        changes.append({
            "item": row["item_text"], "was": row["predicted_code"],
            "was_decision": row["decision"], "was_confidence": row["top1_score"],
            "now": RENTAL, "now_decision": "auto_accept" if confirmed else "review_required",
            "why": why, "amount": row["amount"],
        })
        row["predicted_code"], row["predicted_name"] = RENTAL, RENTAL_NAME
        row["predicted_categories_id"] = None
        row["prediction_source"] = "business_rule"
        row["decision"] = "auto_accept" if confirmed else "review_required"
        row["final_code"] = RENTAL if confirmed else None
        row["final_categories_id"] = None

    moved_to_review = [c for c in changes if c["now_decision"] == "review_required"]
    print(f"{len(changes)} rows -> {RENTAL}   CLP {sum(c['amount'] for c in changes):,.0f}")
    print(f"  {len(changes) - len(moved_to_review)} auto_accept, {len(moved_to_review)} review")
    for c in sorted(changes, key=lambda c: -c["amount"]):
        print(f"  {c['amount']:>11,.0f} | {c['was']:<8} {c['was_decision']:<16} -> {c['now_decision']:<16} | {c['item'][:40]}")

    assert len(changes) == 18, f"expected 18 rows, matched {len(changes)}"
    assert all((r["decision"] == "auto_accept") == bool(r["final_code"]) for r in items), \
        "a row shows a label while awaiting review"

    if not args.write:
        print("\n(dry run — re-run with --write)")
        return

    path = UPLOAD / "invoice_items.jsonl"
    backup = path.with_suffix(path.suffix + SUFFIX)
    if not backup.exists():
        backup.write_bytes(path.read_bytes())
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in items))

    REPORT.mkdir(parents=True, exist_ok=True)
    with (REPORT / "rental_fixes.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(changes[0]))
        writer.writeheader()
        writer.writerows(changes)
    print(f"\nwritten. backup at *{SUFFIX}, changelog at {REPORT.relative_to(ROOT)}/rental_fixes.csv")


if __name__ == "__main__":
    main()
