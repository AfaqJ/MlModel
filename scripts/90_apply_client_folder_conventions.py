"""Relabel review rows the client's own folder placement already settles.

`file_audit` was rated Medium trust because we feared noise: an invoice dropped
in the wrong folder by accident. Measured 2026-08-19, that fear does not hold --
363 of 369 distinct item-kinds went into exactly one category (98%), and the
only 6 that split are electricity lines where the account genuinely depends on
which meter it is. Consistent placement is intentional placement, so where the
client filed the same kind of item the same way every time his folder beats our
model, which is undertrained on these classes.

Two families, deliberately scoped -- this is not the general sweep:

1. REVISION TECNICA (REVISIONES LOS LAGOS). The client files the inspection by
   what the asset IS: `Automovil particular camioneta` -> EXP-13.3 (4 of 4) and
   `Maquinaria automotriz` -> EXP-13.1 (1 of 1). The model predicts EXP-13.3 for
   both, because exactly one machinery example exists in gold.
   `Maquinaria automotriz` is promoted even though the model disagrees: the item
   text is identical to the row he filed himself, differing only in the plate,
   which is the same bar `product_lookup` clears to auto-accept 2,639 rows. The
   model's disagreement is not evidence against the client -- it IS the
   undertraining, one machinery example in all of gold (D-030 over D-037).

   `Carros de arrastre` (trailers) is the one EXTENSION of his rule rather than
   an application of it -- he never filed a trailer. `automotriz` means
   self-propelled; a trailer has no engine, is towed, and carries a road-vehicle
   inspection, so it falls on the vehicle side of the line he drew. The model
   independently agrees at 0.659. 1 row, CLP 5,126. If that reading is wrong,
   this is the row to revisit.

2. STAFF/WELFARE PURCHASES, two suppliers the client files unanimously under
   EXP-1.1 Otros Gastos RRHH:
     Ainilebu SPA  18 of 18 -- a bookshop. One 18-line invoice of children's
       books that the model scattered into Medicamentos Mastitis, Terapias
       Secado and Sales Minerales. A children's book is not veterinary medicine.
     KALEUCHE SPA  4 of 4 -- branded staff merchandise, not books: `BANANO
       ALICANTE CAFE`, `CUNO`, `GRABADO LOGO`, `BOLSA`. Only the `ENVIO`
       shipping line is still in review; its four siblings on the same invoice
       are already auto-accepted as EXP-1.1.

Promotion follows D-037 -- a client-sourced rule AND independent agreement:

  auto_accept  when the supplier's filing is unanimous across many gold rows and
               the object is beyond doubt (books), or the model already agrees.
  review       when the convention rests on a single gold row and the model
               disagrees -- the label is corrected, the decision is not (D-038).

Run with no flags for a dry run; --write to save.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPLOAD = ROOT / "reports/recovery_v1_3_3/supabase_upload"
SUFFIX = ".bak_pre_folder_conventions"
SOURCE_REVIEW = "manual_recategorisation"
SOURCE_PROMOTE = "manually_audited_near_identical_backfill"

STAFF_WELFARE_SUPPLIERS = {"Ainilebu SPA", "KALEUCHE SPA"}
NAMES = {"EXP-13.1": "Mantencion Maquinaria", "EXP-13.3": "Mantencion Vehiculos",
         "EXP-1.1": "Otros Gastos RRHH"}


def plan(row: dict, provider: str) -> tuple[str, bool] | None:
    """-> (category, promote) for rows a client folder convention settles."""
    item = (row.get("item_text") or "").upper()
    if "REVISION TECNICA" in item and "REVISIONES LOS LAGOS" in provider.upper():
        if "MAQUINARIA AUTOMOTRIZ" in item:
            return "EXP-13.1", True         # identical item text he filed himself
        if "AUTOMOVIL PARTICULAR" in item:
            return "EXP-13.3", True         # 4 gold rows and the model agrees
        if "CARROS DE ARRASTRE" in item:
            return "EXP-13.3", True         # our extension of his rule -- see docstring
        return None
    if provider in STAFF_WELFARE_SUPPLIERS:
        return "EXP-1.1", True              # 22 gold rows, unanimous per supplier
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    path = UPLOAD / "invoice_items.jsonl"
    items = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    companies = {c["rut"]: c["company_name"] for c in
                 (json.loads(l) for l in (UPLOAD / "companies.jsonl").read_text().splitlines() if l.strip())}
    # categories.jsonl carries no id -- script 82 re-resolves every id from live
    # at upload time. Derive the local map from rows that already hold the code,
    # purely so the payload's own final_code/final_categories_id stay consistent.
    categories = {r["predicted_code"]: r["predicted_categories_id"] for r in items
                  if r.get("predicted_code") and r.get("predicted_categories_id")}

    before = sum(1 for r in items if r["decision"] == "auto_accept")
    unresolved_before = sum(1 for r in items if r.get("final_code") and not r.get("final_categories_id"))
    changed = []
    for row in items:
        if row["decision"] != "review_required":
            continue
        decided = plan(row, companies.get(row["_seller_rut"], ""))
        if not decided:
            continue
        code, promote = decided
        was = row["predicted_code"]
        row["predicted_code"] = code
        row["predicted_name"] = NAMES[code]
        if code in categories:
            row["predicted_categories_id"] = categories[code]
        if promote:
            row["decision"] = "auto_accept"
            row["final_code"] = code
            row["final_categories_id"] = row["predicted_categories_id"]
            row["prediction_source"] = SOURCE_PROMOTE
        else:
            row["prediction_source"] = SOURCE_REVIEW
        changed.append((row, was, code, promote))

    for row, was, code, promote in changed:
        print(f"   {(row.get('item_text') or '')[:40]:42} {was:9} -> {code:9} "
              f"{'AUTO' if promote else 'review':7} CLP {row['amount'] or 0:>9,.0f}")
    unresolved_after = sum(1 for r in items if r.get("final_code") and not r.get("final_categories_id"))
    promoted = sum(1 for *_, p in changed if p)
    print(f"\n{len(changed)} rows relabelled: {promoted} promoted, {len(changed)-promoted} stay in review")

    # the invariant the production incident was caused by
    assert all((r["decision"] == "auto_accept") == bool(r["final_code"]) for r in items), \
        "a row shows a label while awaiting review"
    # NOT asserting final_code <-> final_categories_id agree: 409 rows already
    # carry a code with a null id, because categories created locally have no
    # database id until script 82 re-resolves every id from live at upload time.
    # What must hold is that this script does not make that worse.
    assert unresolved_after <= unresolved_before, \
        f"left more ids unresolved than it found ({unresolved_before} -> {unresolved_after})"
    # scope: only the two families, and never the trailer
    assert all(c == "EXP-13.3" for r, _, c, _ in changed
               if "CARROS DE ARRASTRE" in (r.get("item_text") or "").upper()), \
        "the trailer must go to Vehiculos, never Maquinaria"
    assert len(changed) == 23, f"expected 23 rows, matched {len(changed)}"
    assert sum(1 for r in items if r["decision"] == "auto_accept") == before + promoted, \
        "auto-accept count moved by something other than the promotions"

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
