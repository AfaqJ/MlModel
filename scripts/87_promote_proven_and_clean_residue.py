"""Promote only what a lookup table already proves, and re-hint what is left.

Two strictly separated halves.

PROMOTE moves a review row to auto_accept. A row qualifies only when the
identical *product* is already auto-accepted from `product_lookup` or
`manually_audited_near_identical_backfill` -- a fact, not a model guess -- and
the destination is that same code. Brand, size and supplier may differ; the
product may not. Seven products qualify. `MANGA PALPACION` is why this half
exists: six sleeves sat in Other HR Costs while fifteen identical sleeves were
already auto-accepted into Work Clothing & Tools from the lookup.

REHINT never changes a decision. It corrects the category shown against rows
that stay in review, in two places script 86 could not reach:
  * fasteners and fittings filed under narrow product accounts -- nails in
    Mineral Salts, ball valves in Silage Bales, a drive belt in Lime. Script 86
    only overruled a short list of source categories and these were not on it.
  * the residue left in Other HR Costs after 86: windscreen fluid, a Starlink
    subscription, a herbicide filed as mineral salts.

Deliberately NOT touched: generic nails, plain fittings and welding rod, which
are open convention questions in CLIENT_CONVENTIONS.md; gas fittings on a gas
invoice, which are probably right; pool chemicals, earthworks, dining chairs and
the TRU-TEST reader wands, where the correct account is genuinely unknown.

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
SUFFIX = ".bak_pre_proven_promotion"

NAMES = {
    "ADM-1.2": "Comunicaciones e Internet",
    "ADM-1.6": "Utiles y gastos de oficina.",
    "EXP-7.0": "AGROQUIMICOS",
    "EXP-9.2": "Otros Gastos Riego",
    "EXP-10.1": "Mantencion Sala",
    "EXP-10.3": "Detergentes e higenizantes",
    "EXP-13.1": "Mantencion Maquinaria",
    "EXP-13.3": "Mantencion Vehiculos",
    "EXP-14.2": "Mantencion Cercos",
    "EXP-14.3": "Mantencion Agua y Purines",
    "EXP-14.4": "Mantencion Instalaciones",
    "EXP-16.1": "Ropa y Herramientas de Trabajo",
    "EXP-16.2": "Otros Gastos Campo",
}

PROVEN_SOURCES = {"product_lookup", "manually_audited_near_identical_backfill"}

# (pattern, destination, the proof). Each `proof` names an item that is already
# auto-accepted into `destination` from a proven source; a startup check finds
# it in the payload and fails loudly if it has gone.
# NOT promoted, and the reason is the whole point of this bar:
#   HORA TECNICA -- the client labelled exactly one technician's initials,
#   `HORA TECNICA AM` -> EXP-10.1. Gold labels `HORA TECNICA LH` from the same
#   supplier EXP-13.1 and `HORA TECNICA JM` EXP-10.1, both from silver_audit_v2.
#   Extending AM to JM/FA/CAL/LH assumes the initials carry no meaning, and gold
#   itself disagrees. Left in review; it is now a client question.
PROMOTE: list[tuple[str, str, str]] = [
    (r"MANGA[S]? PALPACION", "EXP-16.1", "MANGA PALPACION ECOGAN SHOOF 219511"),
    (r"ESPUMA CLORADA", "EXP-10.3", "ESPUMA CLORADA DA X 20 LT"),
    (r"COPLA COMPRESION", "EXP-14.3", "COPLA COMPRESION 32MM PN16 ARANGUL"),
    (r"CLAVO TERRANO", "EXP-14.2", "CLAVO TERRANO 1 1/2\" X 1 KG"),
    (r"PAPEL HIGIENICO", "ADM-1.6", "PAPEL HIGIENICO ECONOMICO 500 M ELITE"),
    (r"^LIMA MOTOSIERRA", "EXP-16.2", "LIMA MOTOSIERRA 3/16\""),
]

# (pattern, destination, why, the current codes this rule may overrule).
# The `from` set is always narrow: a rule may only correct an account where the
# object provably cannot belong.
REHINT: list[tuple[str, str, str, set[str]]] = [
    (r"^CLAVO (CTE|CORRIENTE|DE )", "EXP-14.4",
     "a nail is not mineral salts, drying-off therapy or a sanitiser",
     {"EXP-2.4", "EXP-2.1", "EXP-10.3", "EXP-5.2"}),
    (r"^(FU|PL|GG|KO|K1|K12|K34)-", "EXP-14.3",
     "a threaded pipe fitting is not mineral salts, an agrochemical or feed",
     {"EXP-2.4", "EXP-7.0", "EXP-5.2", "EXP-2.2"}),
    (r"^VALVULA (COMPTA|DE BOLA)", "EXP-14.3",
     "a ball valve is not mineral salts or a silage bale",
     {"EXP-2.4", "EXP-4.2", "EXP-5.2"}),
    (r"^T1 TUERCA|^TUERCA ESPECIAL BOMBA|^PAN PERNO ANCLAJE|^TVNC TORNILLO",
     "EXP-14.4", "a nut, anchor bolt or screw is not feed, pasture or silage",
     {"EXP-5.2", "EXP-8.2", "EXP-4.1", "ADM-1.2", "EXP-2.4"}),
    (r"^LIJA MADERA", "EXP-14.4", "sandpaper is not a drying-off therapy", {"EXP-2.1"}),
    (r"^CORREA ENTREGA LATERAL", "EXP-13.1",
     "a machine drive belt is not lime", {"EXP-6.3"}),
    (r"^%?FILTRO (COMBUSTIBLE|ACEITE)", "EXP-13.1",
     "an engine filter is not mastitis medicine or animal health",
     {"EXP-2.2", "EXP-2.6"}),
    (r"^ACEITE CADENA", "EXP-16.2",
     "chainsaw chain oil; the product lookup files chainsaw items here",
     {"EXP-2.2"}),
    (r"^(CODO|COPLA|TERMINAL|UNION|TEE|NIPLE|BUSHING)\s*\d+\s*(MM|/\d+)|"
     r"^CODO \d+/\d+|^TERMINAL SO HE", "EXP-14.3",
     "a bare pipe fitting is not mineral salts, an agrochemical or mastitis medicine",
     {"EXP-2.4", "EXP-7.0", "EXP-2.2", "EXP-5.2"}),
    (r"^CLAVO\b|^CEMENTO\b|^ESCUADRA FIERRO|^LIJA\b", "EXP-14.4",
     "nails, cement, angle bracket and sandpaper are not mineral salts", {"EXP-2.4"}),
    (r"^BUSHING\b|^SIFON\b|^CODO \d+", "EXP-14.3",
     "a bushing, siphon or elbow is not a mineral salt or an agrochemical",
     {"EXP-2.4", "EXP-7.0"}),
    (r"FIERRO REDONDO", "EXP-14.4",
     "round bar stock is a building material, not a mineral salt", {"EXP-2.4"}),
    (r"^%?FILTRO AIRE", "EXP-13.1",
     "an air filter is not an agrochemical", {"EXP-7.0", "EXP-2.4"}),
    (r"^ESTERON TEN", "EXP-7.0",
     "Esteron is a herbicide, not a mineral salt", {"EXP-2.4"}),
    # --- residue left in Other HR Costs by script 86 ------------------------
    (r"^LAVAPARABRISAS|VISION CLARA", "EXP-13.3",
     "windscreen washer fluid is a vehicle consumable", {"EXP-1.1"}),
    (r"BYOD SHOP PRORATED SUBSCRIPTION", "ADM-1.2",
     "a Starlink subscription line is internet service", {"EXP-1.1"}),
    (r"^ABRAZADERA CON PERNO", "EXP-14.4",
     "a bolted clamp is hardware, not a staff cost", {"EXP-1.1"}),
]


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().upper()
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 %\"/-]", " ", text)).strip()


def current_code(row: dict) -> str:
    return row.get("final_code") or row.get("predicted_code")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="save; otherwise dry run")
    args = parser.parse_args()

    path = UPLOAD / "invoice_items.jsonl"
    items = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

    # Every promotion must still be able to point at its proof.
    for pattern, destination, proof in PROMOTE:
        proven = [
            row for row in items
            if row["decision"] == "auto_accept"
            and row["prediction_source"] in PROVEN_SOURCES
            and current_code(row) == destination
            and normalise(row.get("item_text")) == normalise(proof)
        ]
        assert proven, f"proof row vanished: {proof!r} -> {destination}"

    promoted, rehinted = [], []
    for row in items:
        text = normalise(row.get("item_text"))
        if not text or row["decision"] != "review_required":
            continue

        for pattern, destination, proof in PROMOTE:
            if not re.search(pattern, text):
                continue
            was = current_code(row)
            row.update({
                "predicted_code": destination, "predicted_name": NAMES[destination],
                "predicted_categories_id": None,
                "prediction_source": "manually_audited_near_identical_backfill",
                "decision": "auto_accept", "final_code": destination,
                "final_categories_id": None,
            })
            promoted.append({
                "input_id": f"COMPRAS|{row['_seller_rut']}|{row['_invoice_folio']}"
                            f"|{row['invoice_line_number']}",
                "item": row["item_text"], "was_code": was, "now_code": destination,
                "proof": proof, "amount": row["amount"],
            })
            break
        else:
            for pattern, destination, why, allowed in REHINT:
                was = current_code(row)
                if was not in allowed or not re.search(pattern, text):
                    continue
                row.update({
                    "predicted_code": destination, "predicted_name": NAMES[destination],
                    "predicted_categories_id": None,
                    "prediction_source": "manual_recategorisation",
                    "final_code": None, "final_categories_id": None,
                })
                rehinted.append({
                    "input_id": f"COMPRAS|{row['_seller_rut']}|{row['_invoice_folio']}"
                                f"|{row['invoice_line_number']}",
                    "item": row["item_text"], "was_code": was, "now_code": destination,
                    "proof": why, "amount": row["amount"],
                })
                break

    print(f"PROMOTED to auto_accept: {len(promoted)} rows  "
          f"CLP {sum(c['amount'] for c in promoted):,.0f}")
    for _, destination, proof in PROMOTE:
        selected = [c for c in promoted if c["proof"] == proof]
        if selected:
            print(f"   -> {destination:9} {len(selected):3} rows  proof: {proof[:44]}")
    print(f"\nRE-HINTED, still in review: {len(rehinted)} rows  "
          f"CLP {sum(c['amount'] for c in rehinted):,.0f}")
    for _, destination, why, _ in REHINT:
        selected = [c for c in rehinted if c["proof"] == why]
        if selected:
            print(f"   -> {destination:9} {len(selected):3} rows  {why[:56]}")

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
    for name, changes in (("promoted_on_lookup_proof", promoted), ("rehinted_residue", rehinted)):
        with (REPORT / f"{name}.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(changes[0]))
            writer.writeheader()
            writer.writerows(changes)
    print(f"\nwrote {path} and 2 CSVs in {REPORT}")


if __name__ == "__main__":
    main()
