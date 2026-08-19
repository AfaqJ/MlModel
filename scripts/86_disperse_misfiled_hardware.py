"""Move obviously-misfiled hardware and materials to a defensible category.

Three things are wrong in the payload and none of them need the client:

1. Ten low-confidence rows were auto-accepted on a substring collision --
   `ESTUFA INFRARED WIFI` in Communications, `CADENA MOTOSIERRA` in Motorcycle
   Maintenance. They are moved to review with a better hint.
2. Whole families sit in an unrelated account -- nails in Agrochemicals,
   drywall screws in Communications, a brucellosis blood test in Installations
   Maintenance.
3. `EXP-1.1 Otros Gastos RRHH` became a catch-all: 313 review rows holding
   cement, pipe nipples and bushings next to actual staff costs.

Nothing here is promoted to auto_accept. Every touched row stays (or becomes)
`review_required`, because the destination is our reasoning about what the
object is, not a client convention or a lookup table. Where the client still
has to rule on the *account* -- paint, nails, chainsaw consumables -- the row
is parked somewhere defensible and the question goes to him separately.

`prediction_source` becomes `manual_recategorisation`, a new value: mixing this
into `business_rule` would destroy the distinction between "the client proved
this" and "we reasoned about it". Apply
`002_add_manual_recategorisation_source.sql` before script 82 uploads.

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
SUFFIX = ".bak_pre_hardware_dispersal"
SOURCE = "manual_recategorisation"

NAMES = {
    "EXP-12.2": "Analisis Animales",
    "EXP-13.1": "Mantencion Maquinaria",
    "EXP-14.3": "Mantencion Agua y Purines",
    "EXP-14.4": "Mantencion Instalaciones",
    "EXP-15.3": "Fletes",
    "EXP-16.1": "Ropa y Herramientas de Trabajo",
    "EXP-16.2": "Otros Gastos Campo",
    "EXP-1.1": "Otros Gastos RRHH",
}

# (pattern, destination, why). Matched against the normalised item text, and
# only where the row's current code is one this rule is allowed to overrule --
# that guard is what stops a keyword sweeping up a row someone already settled.
# `FROM_ANY` means the object is unambiguous enough that wherever it currently
# sits is wrong; the destination is still only a hint, never an acceptance.
FROM_ANY = "*"

# Provenance we must never overrule: a lookup table or the client's own labelled
# rows are facts, not guesses. `LIMA MOTOSIERRA 3/16"` is auto-accepted from
# `product_lookup` into EXP-16.2, and that is why the chainsaw rule sends its
# siblings to EXP-16.2 rather than to Machinery Maintenance -- the table already
# answered the question.
PROVEN = {
    "product_lookup",
    "meter_lookup",
    "client_evidence_backfill",
    "manually_audited_near_identical_backfill",
}

RULES: list[tuple[str, str, str, object]] = [
    # --- the object is certain; only the account could be argued -------------
    (r"\bBRUCELOSIS\b|ROSA DE BENGALA", "EXP-12.2",
     "a brucellosis blood test is an animal analysis, not building maintenance", FROM_ANY),
    (r"\bMOTOSIERRA[S]?\b", "EXP-16.2",
     "chainsaw consumable; the product lookup already files LIMA MOTOSIERRA here", FROM_ANY),
    (r"MOTOR HIDRAULICO", "EXP-13.1",
     "a hydraulic motor is machinery; matched Mantencion Motos on MOTOR", {"EXP-13.2"}),

    # --- plumbing and water fittings ---------------------------------------
    (r"^-?NIPLE\b|^-?BUSHING\b|^-?CODO H[IE]-H[IE]\b|^FU-|^AQ-|\bSIFON\b|"
     r"\bTUBERIA FUSION\b|JUEGO DE FITTING|KIT REGULADOR \+ FLEXIBLE",
     "EXP-14.3", "threaded/PPR plumbing fitting; belongs with the water and slurry line",
     {"EXP-1.1", "ADM-1.2", "ADM-1.6", "EXP-7.0"}),
    (r"^VALVULA (BOLA|COMPACTA)\b|^LLAVE BOLA\b", "EXP-14.3",
     "shut-off valve; belongs with the water and slurry line",
     {"EXP-1.1", "ADM-1.2", "ADM-1.6", "EXP-7.0"}),

    # --- building materials -------------------------------------------------
    (r"^CEMENTO\b", "EXP-14.4", "cement is a building material, not a staff cost",
     {"EXP-1.1", "ADM-1.2", "ADM-1.6", "EXP-7.0"}),
    (r"^CLAVO\b|^PAR ALCAYATA\b|^T1 TUERCA\b|^PCO PERNO\b|^TAUTO-FINA\b|"
     r"^TVZC\b|^KG SOLDADURA\b|^LIJA \w+|^GUARDAPOLVO\b|^SOPORTE POLICARBONATO\b",
     "EXP-14.4", "nail, screw, weld rod or board; building material, not comms or agrochemicals",
     {"EXP-1.1", "ADM-1.2", "ADM-1.6", "EXP-7.0"}),
    (r"^PTA TERC\b|^PUERTA \w+", "EXP-14.4", "a door is a building material",
     {"EXP-14.3", "ADM-1.2", "ADM-1.6"}),
    (r"^ESMALTE\b|^BROCHA\b", "EXP-14.4",
     "paint and brush; parked here pending the client's ruling on where paint goes",
     {"ADM-1.6", "EXP-1.1"}),

    # --- one-off collisions -------------------------------------------------
    (r"^ESTUFA\b", "EXP-16.2", "a heater matched Comunicaciones on the word WIFI",
     {"ADM-1.2"}),
    (r"^DESPACHO ONLINE$", "EXP-15.3", "a delivery charge is freight, not internet",
     {"ADM-1.2"}),
    (r"^GRAPAS PARA ENGRAPADORA", "EXP-16.1",
     "stapler consumable from a hardware store; not fence maintenance", {"EXP-14.2"}),
    (r"^BOTELLON \d+ LITROS$", "EXP-1.1",
     "bottled drinking water for staff; matched Mantencion Motos on nothing meaningful",
     {"EXP-13.2", "EXP-16.2"}),
]


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().upper()
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 +-]", " ", text)).strip()


def current_code(row: dict) -> str:
    return row.get("final_code") or row.get("predicted_code")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="save; otherwise dry run")
    args = parser.parse_args()

    path = UPLOAD / "invoice_items.jsonl"
    items = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

    changes = []
    for row in items:
        text = normalise(row.get("item_text"))
        if not text or row["prediction_source"] in PROVEN:
            continue
        for pattern, destination, why, allowed in RULES:
            was_code = current_code(row)
            if was_code == destination and row["decision"] == "review_required":
                continue  # already parked correctly; nothing to do
            if allowed is not FROM_ANY and was_code not in allowed:
                continue
            if not re.search(pattern, text):
                continue
            was = (was_code, row["decision"], row["prediction_source"])
            row["predicted_code"] = destination
            row["predicted_name"] = NAMES[destination]
            row["predicted_categories_id"] = None  # script 82 remaps from live
            row["prediction_source"] = SOURCE
            row["decision"] = "review_required"
            row["final_code"] = None
            row["final_categories_id"] = None
            changes.append({
                "input_id": f"COMPRAS|{row['_seller_rut']}|{row['_invoice_folio']}"
                            f"|{row['invoice_line_number']}",
                "item": row["item_text"],
                "was_code": was[0], "was_decision": was[1], "was_source": was[2],
                "now_code": destination, "now_decision": "review_required",
                "why": why, "amount": row["amount"],
            })
            break

    freed = [c for c in changes if c["was_decision"] == "auto_accept"]
    print(f"{len(changes)} rows recategorised  CLP {sum(c['amount'] for c in changes):,.0f}")
    print(f"  {len(freed)} pulled out of auto_accept  CLP {sum(c['amount'] for c in freed):,.0f}")
    print(f"  {len(changes) - len(freed)} already in review, hint corrected\n")
    for _, destination, why, _ in RULES:
        selected = [c for c in changes if c["why"] == why]
        if selected:
            print(f"  -> {destination:9} {len(selected):3} rows  CLP {sum(c['amount'] for c in selected):>11,.0f}  {why[:56]}")

    assert not any(c["now_decision"] == "auto_accept" for c in changes), \
        "this script must never promote a row to auto_accept"
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
    with (REPORT / "hardware_dispersal.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(changes[0]))
        writer.writeheader()
        writer.writerows(changes)
    print(f"\nwrote {path} and {REPORT/'hardware_dispersal.csv'}")


if __name__ == "__main__":
    main()
