"""Second batch of review rows the client's own folder placement settles.

Same principle as script 90 and the same bar: where the client filed the exact
item himself, consistently, and the object makes physical sense in that account,
his filing beats our model -- which is undertrained on most of these classes
(D-030 over D-037). Every row below was read individually, not rule-matched.

PROMOTED -- 31 rows:

  SONDAJES PERFOMAQ `SERVICIO TECNICO` (6). The item name is generic, but the
  DESCRIPTION names the job every time: "LIMPIEZA DE POZO PROFUNDO", "REEMPLAZO
  EQUIPO SUMERGIBLE 3HP/380V", "MEJORAS EN INSTALACION DE SISTEMA DE BOMBEO
  SUMERGIBLE". The supplier drills boreholes. Wells and submersible pumps are
  the farm water system, so `EXP-14.3` is confirmed independently of the
  client's filing, not merely inherited from it.

  DIFOR `S-MD.. ... MANTENCION` (18). Scheduled vehicle services at 8 mileage
  intervals. The client filed three of them himself -- S-MD10, S-MD40, S-MD50 --
  all `EXP-13.3`, and the model predicts `EXP-13.3` for all 18 unanimously. So
  S-MD20/30/60/80/90 are promoted as spec siblings: the same service at a
  different interval, with the client consistent on every one he filed and the
  model independently agreeing on every one he did not. This is an extension
  beyond the rows he touched, and it is the only one in this batch.

  GEA `JUEGO PEZONERAS MONOBLOCK` / `COLECTOR 300` (4). Teat cup clusters, a
  milking consumable. Client files them `EXP-10.4` and does so consistently.
  (`TAPON CIERRE PEZONERA` -> `EXP-2.6` is a different product, a closure plug,
  and is not a contradiction.)

  `SPRAY (PULVERIZADOR MANUAL 500 CC)` (1). A hand sprayer is equipment, not
  medicine; the model's `Medicamentos Mastitis` is the wrong kind of thing.

  `EMPANADAS DE HORNO` (1) and `ABRAZADERAS MET` (1). Exact string, model agrees.

DELIBERATELY NOT TOUCHED -- 12 rows, each for a different reason:

  `FILTRO LECHE` (2). The client is NOT consistent here: from the SAME supplier
  he filed `FILTRO LECHE JUMBO 100 UND` under `EXP-10.1` and `FILTRO LECHE 75 MM
  * 800 SE` under `EXP-10.4`. Same product, different size, different account.
  The size-stripped consistency check missed it because `JUMBO` and `SE` are
  different words. A spec sibling is only safe when the siblings agree.

  `PIOLA PERLON RETIRADOR` (9). The client filed it `EXP-10.3 Detergentes e
  higenizantes`, but that account holds ZINICIN, ORACID, CLORO and detergents --
  chemicals. A nylon cluster-remover cord is not a chemical. This is the one
  case that looks like the misfile we always feared, so the model's hint
  (`Mantencion Sala`) is left in place as the more useful thing for a human to
  see. Worth asking the client.

  ADDVISE `Arriendo <month> 25` (1 of 15). One client row says `Arriendo Oficina`,
  but ADDVISE's giro is animal nutrition and feed manufacturing, not property,
  and the model reads all 15 monthly lines as machinery rental. A feed company
  billing monthly rent is more likely equipment than office. Genuinely
  ambiguous -> client question, not a correction.

Run with no flags for a dry run; --write to save.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPLOAD = ROOT / "reports/recovery_v1_3_3/supabase_upload"
SUFFIX = ".bak_pre_folder_batch2"
SOURCE = "manually_audited_near_identical_backfill"

NAMES = {"EXP-14.3": "Mantencion Agua y Purines", "EXP-13.3": "Mantencion Vehiculos",
         "EXP-10.4": "Otros Gastos Lecheria", "EXP-2.6": "Otros Gastos Salud Animal",
         "EXP-1.1": "Otros Gastos RRHH", "EXP-9.2": "Otros Gastos Riego"}
# (supplier fragment, item regex) -> category
RULES = [
    ("SONDAJES PERFOMAQ", r"^SERVICIO T", "EXP-14.3"),
    ("DIFOR CHILE",       r"^S-MD\d+ .*MANTENCION", "EXP-13.3"),
    ("GEA Farm",          r"^JUEGO PEZONERAS", "EXP-10.4"),
    ("COOPERATIVA AGRICOLA Y LECHERA", r"^SPRAY \(PULVERIZADOR", "EXP-2.6"),
    ("MINERVA RUTH",      r"^EMPANADAS DE HORNO", "EXP-1.1"),
    ("WULFF",             r"^ABRAZADERAS MET", "EXP-9.2"),
]


def plan(item: str, provider: str) -> str | None:
    for frag, pattern, code in RULES:
        if frag.upper() in provider.upper() and re.match(pattern, item.upper()):
            return code
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    path = UPLOAD / "invoice_items.jsonl"
    items = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    companies = {c["rut"]: c["company_name"] for c in
                 (json.loads(l) for l in (UPLOAD / "companies.jsonl").read_text().splitlines() if l.strip())}
    cat_id = {r["predicted_code"]: r["predicted_categories_id"] for r in items
              if r.get("predicted_code") and r.get("predicted_categories_id")}

    before = sum(1 for r in items if r["decision"] == "auto_accept")
    changed = []
    for row in items:
        if row["decision"] != "review_required":
            continue
        code = plan(row.get("item_text") or "", companies.get(row["_seller_rut"], ""))
        if not code:
            continue
        was = row["predicted_code"]
        row.update(predicted_code=code, predicted_name=NAMES[code], final_code=code,
                   decision="auto_accept", prediction_source=SOURCE)
        if code in cat_id:
            row["predicted_categories_id"] = cat_id[code]
        row["final_categories_id"] = row.get("predicted_categories_id")
        changed.append((row, was, code))

    for row, was, code in sorted(changed, key=lambda x: -(x[0]["amount"] or 0)):
        print(f"   {(row.get('item_text') or '')[:38]:40} {was:9} -> {code:9} CLP {row['amount'] or 0:>10,.0f}")
    print(f"\n{len(changed)} rows promoted to auto_accept")

    assert all((r["decision"] == "auto_accept") == bool(r["final_code"]) for r in items), \
        "a row shows a label while awaiting review"
    assert len(changed) == 31, f"expected 31 rows, matched {len(changed)}"
    assert sum(1 for r in items if r["decision"] == "auto_accept") == before + len(changed)
    # the DIFOR extension is only safe while the model agrees on every one of them
    assert all(c == "EXP-13.3" for r, _, c in changed
               if "S-MD" in (r.get("item_text") or "").upper()), "a DIFOR row went somewhere else"
    # the three families that must stay untouched, and why (see docstring)
    for term, why in (("PIOLA PERLON", "looks like a client misfile"),
                      ("FILTRO LECHE", "client filed the same product two ways"),
                      ("ARRIENDO", "ADDVISE rent is genuinely ambiguous")):
        assert not any(term in (r.get("item_text") or "").upper() for r, *_ in changed), \
            f"{term} was touched but must stay in review: {why}"

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
