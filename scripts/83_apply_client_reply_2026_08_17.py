"""Apply Cristian's 2026-08-17 email reply to the local Supabase payload.

Local only. Nothing is pushed — `82_apply_label_corrections.py` is the pusher
and it remaps `categories_id` from live, so the ids in this payload stay None.

Three categories are added and 175 rows relabelled:

  EXP-15.6  Arriendo Predio Lecheria   0 rows  — client named it; no invoice
                                                 for it exists yet.
  EXP-15.7  Arriendo Otros Predios    14 rows  — ARRIENDO FUNDO PELLECO.
                                                 Client: "in the case of
                                                 Pelleco it must go to
                                                 Arriendo Otros Predios".
  EXP-15.8  Leasing                  158 rows  — Banco BICE lease rent (141)
                                                 + Santander (17). Client:
                                                 "Just put them in leasing
                                                 account ... you can create it".

Plus 3 BICE lines that are NOT lease rent: two purchase options and one full
prepayment, each naming the machine it buys out (a milk tank, a rotary parlour,
a John Deere tractor). Those are a fixed-asset purchase, not a rent payment —
but that is our reading, not the client's, so they move to AF-2.1 and stay in
review. `final_code` stays NULL, which is the rule for any unconfirmed row.

The 62 remaining BICE lines are bank fees, commissions and FX. Out of scope.

Run with no flags for a dry run; `--write` to save.
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
SUFFIX = ".bak_pre_clientreply"

BICE, SANTANDER = "97080000K", "97036000K"

NEW_CATEGORIES = [
    {"code": "EXP-15.6", "name": "Arriendo Predio Lecheria"},
    {"code": "EXP-15.7", "name": "Arriendo Otros Predios"},
    {"code": "EXP-15.8", "name": "Leasing"},
]

# Lease rent as the bank writes it. All three are payments of a numbered rent
# instalment against a numbered contract; the wording varies only by whether the
# payment was late or partial.
LEASE_RENT = ("renta de arrendamiento", "pago parcial de la renta de arrendamiento")
# Ending the lease by buying the asset. Different event, different category.
BUYOUT = ("opcion de compra del contrato", "prepago total del contrato")


def classify(row: dict) -> tuple[str, str, bool] | None:
    """-> (code, name, confirmed_by_client) for the rows this session touches."""
    rut, text = row.get("_seller_rut"), (row.get("item_text") or "").lower()
    if rut == BICE:
        if any(p in text for p in LEASE_RENT):
            return "EXP-15.8", "Leasing", True
        if any(text.startswith(p) for p in BUYOUT):
            return "AF-2.1", "COMPRAS DE ACTIVO FIJO", False
    if rut == SANTANDER and text.startswith("pago arriendo operacion"):
        return "EXP-15.8", "Leasing", True
    if text.startswith("arriendo fundo pelleco"):
        return "EXP-15.7", "Arriendo Otros Predios", True
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="save; otherwise dry run")
    args = ap.parse_args()

    cats = [json.loads(l) for l in (UPLOAD / "categories.jsonl").read_text().splitlines() if l.strip()]
    items = [json.loads(l) for l in (UPLOAD / "invoice_items.jsonl").read_text().splitlines() if l.strip()]

    have = {c["code"] for c in cats}
    added = [c for c in NEW_CATEGORIES if c["code"] not in have]
    clash = [c for c in NEW_CATEGORIES if c["code"] in have]
    if clash:
        sys.exit(f"code already in use: {clash} — pick free codes, do not overwrite")

    changes = []
    for row in items:
        verdict = classify(row)
        if not verdict:
            continue
        code, name, confirmed = verdict
        was, was_decision = row["predicted_code"], row["decision"]
        row["predicted_code"] = code
        row["predicted_name"] = name
        row["predicted_categories_id"] = None  # remapped from live on push
        row["prediction_source"] = "business_rule"
        if confirmed:
            row["decision"] = "auto_accept"
            row["final_code"] = code
        else:
            row["decision"] = "review_required"
            row["final_code"] = None
        row["final_categories_id"] = None
        changes.append({
            "input_id": f"{row['_seller_rut']}|{row['_invoice_folio']}|{row['invoice_line_number']}",
            "item": row["item_text"], "was": was, "now": code,
            "was_decision": was_decision, "now_decision": row["decision"],
            "why": "client 2026-08-17" if confirmed else "ours — buyout, not rent; left in review",
            "amount": row["amount"],
        })

    counts: dict[tuple[str, str], list] = {}
    for c in changes:
        counts.setdefault((c["now"], c["now_decision"]), []).append(c["amount"])
    print(f"categories: {len(cats)} -> {len(cats) + len(added)}  (+{[c['code'] for c in added]})")
    for (code, decision), amounts in sorted(counts.items()):
        print(f"  {code:9} {decision:16} {len(amounts):4d} lines  CLP {sum(amounts):>15,.0f}")

    # The reply covers exactly these rows. Any other count means the selection
    # drifted, and a silent drift here relabels real money.
    assert len(counts.get(("EXP-15.8", "auto_accept"), [])) == 158, "expected 158 lease lines"
    assert len(counts.get(("EXP-15.7", "auto_accept"), [])) == 14, "expected 14 Pelleco lines"
    assert len(counts.get(("AF-2.1", "review_required"), [])) == 3, "expected 3 buyout lines"
    # The rule that caused the incident: no label on a row awaiting review.
    assert all((r["decision"] == "auto_accept") == bool(r["final_code"]) for r in items), \
        "a row shows a label while awaiting review"

    if not args.write:
        print("\n(dry run — re-run with --write)")
        return

    for name in ("categories.jsonl", "invoice_items.jsonl"):
        path = UPLOAD / name
        backup = path.with_suffix(path.suffix + SUFFIX)
        if not backup.exists():
            backup.write_bytes(path.read_bytes())
    (UPLOAD / "categories.jsonl").write_text(
        "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cats + added))
    (UPLOAD / "invoice_items.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in items))

    REPORT.mkdir(parents=True, exist_ok=True)
    with (REPORT / "changelog.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(changes[0]))
        writer.writeheader()
        writer.writerows(changes)
    print(f"\nwritten. backups at *{SUFFIX}, changelog at {REPORT.relative_to(ROOT)}/changelog.csv")


if __name__ == "__main__":
    main()
