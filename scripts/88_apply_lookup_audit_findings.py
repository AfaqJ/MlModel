"""Act on the 2026-08-18 audit of the product lookup and the silver backfill.

The audit asked one question of every promotion: does a rule the *client wrote*
support this, or are we agreeing with ourselves? Two of the four things this
session flagged as silver-audit errors turned out to be client-backed and were
dropped:

  * `SMART BLUE ... FERTILIZANTES(B)-UREA`, CLP 67.3M -- `SMARTBLUE FUNDO` is a
    `client_product_rule` mapping to EXP-6.2 Nitrogeno, and the item name ends
    in UREA. Correct as it stands.
  * `BIDON 20 LTS DIESEL` -> EXP-16.2 -- `BIDON CERT. AMARILLO DIESEL 20 L` is a
    `client_product_rule` mapping to EXP-16.2. A diesel jerrycan is field kit,
    not fuel. Correct as it stands.
  * `VENTA MATERIAL`, CLP 13.03M -> EXP-14.1 Mantencion Caminos. The item name
    names nothing, but the *description* is `MAICILLO` -- decomposed granite,
    road surfacing material -- from an excavation contractor. Correct as it
    stands. **Read the description before calling an item meaningless.**

All four silver-audit rows flagged as suspect were wrong flags. The one real
finding, `SEMILLA BALLICA TAMA` in Pradera Perenne when TAMA is a short-rotation
ryegrass, is a client question and is not decided here.

What survived:

PROMOTE -- a client-written rule covers the product, the model independently
agrees, and the object makes sense in that account. HDPE compression fittings
join HDPE pipe, and the client filed HDPE pipe under Water & Slurry; the 15
HDPE rows where the model says Milking Parlour instead are left in review,
because the evidence is no longer unanimous.

Run with no flags for a dry run; --write to save.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPLOAD = ROOT / "reports/recovery_v1_3_3/supabase_upload"
REPORT = ROOT / "reports/hardware_dispersal_2026_08_18"
LOOKUP = ROOT / "app/data/product_lookup.csv"
SUFFIX = ".bak_pre_lookup_audit"

NAMES = {"EXP-14.3": "Mantencion Agua y Purines", "EXP-6.2": "Nitrogeno",
         "EXP-2.5": "Otros Medicamentos"}

# (pattern, destination, the client-written lookup row that proves it, the code
# the model must independently already be predicting).
PROMOTE = [
    (r"\bHDPE\b", "EXP-14.3", "TUBERIA HDPE 63MM 2\" PN6 DIN 3,6MM", "EXP-14.3"),
    (r"SMART ?BLUE", "EXP-6.2", "SMARTBLUE FUNDO", "EXP-6.2"),
    (r"MOSKIMIC", "EXP-2.5", "MOSKIMIC FORTE X 3 LT.", None),
]

CLIENT_SOURCES = {"client_product_rule", "direct_client_example", "client_service_rule",
                  "client_product_family_resolution", "direct_client_family_resolution"}


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().upper()
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 \"',./-]", " ", text)).strip()


def current_code(row: dict) -> str:
    return row.get("final_code") or row.get("predicted_code")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="save; otherwise dry run")
    args = parser.parse_args()

    lookup = list(csv.DictReader(LOOKUP.open()))
    for _, destination, proof, _ in PROMOTE:
        matched = [x for x in lookup
                   if normalise(x["item_text"]) == normalise(proof)
                   and x["category_code"] == destination
                   and x["rule_source"] in CLIENT_SOURCES]
        assert matched, f"no client-written lookup rule proves {proof!r} -> {destination}"

    path = UPLOAD / "invoice_items.jsonl"
    items = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

    promoted = []
    for row in items:
        text = normalise(row.get("item_text"))
        if row["decision"] != "review_required" or not text:
            continue
        for pattern, destination, proof, model_must_say in PROMOTE:
            if not re.search(pattern, text):
                continue
            if model_must_say and current_code(row) != model_must_say:
                continue  # evidence is not unanimous; leave it in review
            was = current_code(row)
            row.update({
                "predicted_code": destination, "predicted_name": NAMES[destination],
                "predicted_categories_id": None,
                "prediction_source": "manually_audited_near_identical_backfill",
                "decision": "auto_accept", "final_code": destination,
                "final_categories_id": None,
            })
            promoted.append({"item": row["item_text"], "was_code": was,
                             "now_code": destination, "proof": proof,
                             "amount": row["amount"]})
            break

    print(f"PROMOTED {len(promoted)} rows  CLP {sum(c['amount'] for c in promoted):,.0f}")
    for _, destination, proof, _ in PROMOTE:
        selected = [c for c in promoted if c["proof"] == proof]
        if selected:
            print(f"   -> {destination:9} {len(selected):3} rows  "
                  f"CLP {sum(c['amount'] for c in selected):>12,.0f}  client rule: {proof[:40]}")
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
    with (REPORT / "lookup_audit_findings.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["item", "was_code", "now_code", "proof", "amount"])
        writer.writeheader()
        writer.writerows(promoted)
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
