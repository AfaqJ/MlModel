"""Return the four SONDAJES lines that touch the open fixed-asset question.

Script 91 promoted all six SONDAJES PERFOMAQ lines to `EXP-14.3 Mantencion Agua
y Purines` on the strength of their descriptions. Two of those six are pure
service and stand. The other four describe buying or improving equipment, and
the supplier's giro is "Perforacion de Pozos Profundos, Const. e Instalaciones,
Bombas para Agua" -- they do construction as well as maintenance.

Whether work of that kind is an expense or a fixed asset is exactly what was
asked of the client on 2026-08-19 (question 1 of that email). Answering it
ourselves in the payload while the question is outstanding is the same error
avoided with the silage/hay rows, so these four go back to review and keep the
water-system hint.

  REEMPLAZO EQUIPO SUMERGIBLE ... POR UNO NUEVO   -- buys a named pump + motor
  PUESTA EN MARCHA ... SONDAJE N 2824             -- commissioning a borehole
  MEJORAS EN INSTALACION DE SISTEMA DE BOMBEO     -- betterment
  LIMPIEZA ... + REEMPLAZO DE PARTE HI. NUEVA     -- cleaning plus a new part

Kept auto-accepted, because neither creates an asset:
  LIMPIEZA DE POZO 6" ACERO FUNDO YUTRECO
  REVISION EQUIPO SUMERGIBLE ... FALLA EN CONTACTOR

Run with no flags for a dry run; --write to save.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPLOAD = ROOT / "reports/recovery_v1_3_3/supabase_upload"
SUFFIX = ".bak_pre_sondajes_revert"
CAPITAL = ("REEMPLAZO EQUIPO SUMERGIBLE", "PUESTA EN MARCHA", "MEJORAS EN INSTALACI",
           "REEMPLAZO DE PARTE")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    path = UPLOAD / "invoice_items.jsonl"
    items = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    companies = {c["rut"]: c["company_name"] for c in
                 (json.loads(l) for l in (UPLOAD / "companies.jsonl").read_text().splitlines() if l.strip())}

    changed = []
    for row in items:
        if "SONDAJES PERFOMAQ" not in companies.get(row["_seller_rut"], "").upper():
            continue
        if row["decision"] != "auto_accept":
            continue
        desc = (row.get("description") or "").upper()
        if not any(t in desc for t in CAPITAL):
            continue
        row.update(decision="review_required", final_code=None,
                   final_categories_id=None, prediction_source="manual_recategorisation")
        changed.append(row)

    for r in changed:
        print(f"   back to review  CLP {r['amount'] or 0:>10,.0f}  {(r.get('description') or '')[:64]}")
    kept = [r for r in items if "SONDAJES PERFOMAQ" in companies.get(r["_seller_rut"], "").upper()
            and r["decision"] == "auto_accept"]
    print(f"\n{len(changed)} rows returned to review, {len(kept)} stay auto-accepted")

    assert all((r["decision"] == "auto_accept") == bool(r["final_code"]) for r in items), \
        "a row shows a label while awaiting review"
    assert len(changed) == 4, f"expected 4 rows, matched {len(changed)}"
    assert len(kept) == 2, f"expected 2 to stay, got {len(kept)}"
    assert all("LIMPIEZA DE POZO" in (r.get("description") or "").upper()
               or "REVISI" in (r.get("description") or "").upper() for r in kept), \
        "a row that buys or improves equipment is still auto-accepted"

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
