#!/usr/bin/env python3
"""Harvest sales-category training rows directly from raw VENTAS invoices,
quarantine purchase rows mislabeled as sales, and clear the 2-example training
floor for sales classes that still fall short.

WHY THIS SCRIPT EXISTS
----------------------
Three separate problems, all in the income (ING-*) categories:

1. Calves and heifers were never routed into the Ollama audit at all
   (`TERNERO`: 1 ledger row with a blank verdict; `VAQUILLA`: 0 rows). Fixing
   the promotion dedup key does nothing for them. But we do not need an audit:
   these are the client's OWN outgoing invoices, the item name literally states
   the category, and the document direction is unambiguously a sale. The label
   is certain by inspection.  (DECISIONS.md D-003)

2. Gold contains purchase rows labeled as sales — `vacas` and `vacas preñadas`
   bought on COMPRAS invoices sitting in ING-0.2 VENTA DE VACAS, and `leña`
   bought on a COMPRAS invoice sitting in ING-0.6 VENTA LEÑA. Training a "cow
   sales" class on cow *purchases* teaches the opposite of the business rule.

3. If every harvested row goes into training, "the model classifies milk
   correctly" only proves it memorized them. A held-out slice makes the metric
   mean something.  (D-004)

SCHEMA CHANGE
-------------
Adds two columns to _master_gold.csv:
  direction : COMPRAS | VENTAS | ''    provenance of the row
  split     : holdout | ''             'holdout' is forced into validation
Existing rows get '' for both, which preserves current behavior exactly.

SAFETY
------
Dry run by default. --commit backs up _master_gold.csv first. No network access.

Usage:
    .venv-train/bin/python scripts/57_harvest_sales_gold.py            # dry run
    .venv-train/bin/python scripts/57_harvest_sales_gold.py --commit
"""
from __future__ import annotations

import csv
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "Data" / "gold" / "_master_gold.csv"
LINE_ITEMS = ROOT / "Data" / "processed" / "line_items.csv"
TAXONOMY = ROOT / "Data" / "current_context_2026_06_30" / "taxonomy_from_plan.csv"

COMMIT = "--commit" in sys.argv
SEED = 42
HOLDOUT_FRAC = 0.20
MIN_TRAIN_AFTER_HOLDOUT = 3   # never hold out if it would starve the train side
TRAINING_FLOOR = 3            # synthetic top-up target for name==category classes

# Canonical sales item names -> category code.
# Every one of these is a VENTAS-only phrase whose meaning is unambiguous:
#   VENTA DE LECHE     = sale of milk
#   VENTA DE VACAS     = sale of cows
#   VENTA DE VAQUILLAS = sale of heifers
#   VENTAS TERNEROS    = sales of calves (male)
#   VENTA DE TERNERAS  = sales of calves (female)
# Calves male/female both map to ING-0.4; the taxonomy has one calf category.
SALES_MAP = {
    "venta de leche": "ING-0.1",
    "venta de vacas": "ING-0.2",
    "venta de vaquillas": "ING-0.3",
    "ventas terneros": "ING-0.4",
    "venta de terneras": "ING-0.4",
}

# Deliberately NOT mapped — these are asset disposals, not dairy revenue, and the
# correct accounting treatment is a client decision (HANDOVER.md open question 1):
#   VENTA CAMIONETA (pickup truck), VENTA DE ACTIVO FIJO (fixed asset),
#   maquinaria (machinery), OTROS INGRESOS (other income)
UNMAPPED_SALES = ["venta camioneta", "venta de activo fijo", "maquinaria", "otros ingresos"]

# Synthetic descriptions for floor-clearing. Realistic phrasings of the same
# business event, modeled on how the real sales lines are written.
SYNTHETIC_DESCRIPTIONS = {
    "ING-0.3": [
        "Venta de vaquillas de reposicion, feria ganadera",
        "Vaquillas prenadas vendidas segun guia de despacho",
        "Venta vaquillas H. Friesian, lote completo",
    ],
    "ING-0.6": [
        "Venta de lena seca, metros ruma",
        "Lena nativa vendida a tercero, despacho en predio",
        "Venta de lena, madera de raleo",
    ],
}


def norm(text: str | None) -> str:
    s = "" if text is None else str(text).lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", s).strip()


def clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", "" if text is None else str(text)).strip()


def read_csv(path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def dedup_key(item, desc, prov, code) -> tuple:
    """Same key as scripts/56. See DECISIONS.md D-001."""
    return (norm(item), norm(desc), norm(prov), code)


def text_key(item, desc, prov) -> tuple:
    """Same fields without the label — two rows sharing this key are the same
    model input, so they must not carry different labels. See scripts/56."""
    return (norm(item), norm(desc), norm(prov))


def main() -> None:
    taxonomy = {r["new_code"]: r for r in read_csv(TAXONOMY)}
    gold = read_csv(GOLD)
    raw = read_csv(LINE_ITEMS)

    fields = list(gold[0].keys())
    for col in ("direction", "split"):
        if col not in fields:
            fields.append(col)

    print(f"gold rows before        : {len(gold)}")

    # --- Stage 1: quarantine purchase rows sitting in sales categories -------
    # Data-driven test: an ING-* gold row is suspect when its item name appears
    # in COMPRAS raw data and never appears in VENTAS raw data. That means the
    # phrase describes something the business BUYS, not something it sells.
    compras_names = {norm(r["nmb_item"]) for r in raw if r["source"] == "COMPRAS"}
    ventas_names = {norm(r["nmb_item"]) for r in raw if r["source"] == "VENTAS"}
    purchase_only = compras_names - ventas_names

    quarantined = [r for r in gold
                   if r["category_code"].startswith("ING-")
                   and norm(r["item_text"]) in purchase_only]

    print(f"\nquarantine — purchase rows labeled as sales: {len(quarantined)}")
    for r in quarantined:
        print(f"    {r['category_code']:9s} {r['item_text'][:40]:42s} src={r['source']}")

    quarantine_ids = {id(r) for r in quarantined}
    kept_gold = [r for r in gold if id(r) not in quarantine_ids]

    # --- Stage 2: harvest canonical sales rows from raw VENTAS ---------------
    seen = {dedup_key(r["item_text"], r["description"], r["provider"], r["category_code"])
            for r in kept_gold}

    gold_label_of = {}
    for r in kept_gold:
        gold_label_of.setdefault(
            text_key(r["item_text"], r["description"], r["provider"]), r["category_code"])

    harvested = []
    already = 0
    contradicted = []
    for r in raw:
        if r["source"] != "VENTAS":
            continue
        code = SALES_MAP.get(norm(r["nmb_item"]))
        if not code:
            continue
        # The provider MUST come from the same field the silver ledger used
        # (rzn_soc_emisor -> 'provider'), or the dedup key silently fails to
        # match rows that are in fact the same invoice line and we duplicate the
        # whole class. This is the same failure mode as BUG-001, one level up:
        # a key is only as good as the consistency of the fields feeding it.
        provider = r.get("rzn_soc_emisor", "")
        tkey = text_key(r["nmb_item"], r["dsc_item"], provider)
        established = gold_label_of.get(tkey)
        if established is not None and established != code:
            # Same input already carries a different label in gold. Adding this
            # would create an unlearnable contradiction. Report, don't guess.
            contradicted.append((r["nmb_item"], established, code))
            continue
        key = dedup_key(r["nmb_item"], r["dsc_item"], provider, code)
        if key in seen:
            already += 1
            continue
        seen.add(key)
        gold_label_of.setdefault(tkey, code)
        harvested.append({"code": code, "item": r["nmb_item"],
                          "desc": r["dsc_item"], "provider": provider})

    print(f"\nharvest from raw VENTAS : {len(harvested)} new rows "
          f"({already} already in gold by key)")
    if contradicted:
        print(f"  CONTRADICTED existing gold, skipped: {len(contradicted)}")
        for item, old, new in contradicted[:6]:
            print(f"    gold says {old:9s} / harvest says {new:9s}  <- {item[:40]}")
    for code, n in sorted(Counter(h["code"] for h in harvested).items()):
        print(f"    {code}  +{n:3d}   {taxonomy[code]['leaf']}")

    skipped = Counter(norm(r["nmb_item"]) for r in raw
                      if r["source"] == "VENTAS" and norm(r["nmb_item"]) in UNMAPPED_SALES)
    if skipped:
        print("\n  deliberately NOT harvested (asset disposal / needs client decision):")
        for name, n in skipped.most_common():
            print(f"    {n:3d}  {name}")

    # --- Stage 3: mark a held-out slice per harvested class ------------------
    rng = random.Random(SEED)
    by_code = defaultdict(list)
    for h in harvested:
        by_code[h["code"]].append(h)

    for code, items in by_code.items():
        rng.shuffle(items)
        n_hold = int(len(items) * HOLDOUT_FRAC)
        # Never hold out so much that the training side drops below the floor.
        n_hold = min(n_hold, max(0, len(items) - MIN_TRAIN_AFTER_HOLDOUT))
        for i, h in enumerate(items):
            h["split"] = "holdout" if i < n_hold else ""

    print("\nheld-out slice (forced into validation, never trained):")
    for code in sorted(by_code):
        n_hold = sum(1 for h in by_code[code] if h["split"] == "holdout")
        print(f"    {code}  {n_hold:3d} holdout / {len(by_code[code]):3d} harvested")

    # --- Stage 4: synthetic floor-clearing -----------------------------------
    # Only for classes whose taxonomy leaf IS the item name (a "VENTA X" sales
    # category), and only up to TRAINING_FLOOR. These are a device to clear the
    # <2 exclusion in train_setfit.py, not a substitute for real data. (D-005)
    projected = Counter(r["category_code"] for r in kept_gold)
    projected.update(h["code"] for h in harvested)

    synthetic = []
    for code in sorted(taxonomy):
        if not code.startswith("ING-"):
            continue
        have = projected.get(code, 0)
        if have >= TRAINING_FLOOR:
            continue
        pool = SYNTHETIC_DESCRIPTIONS.get(code)
        if not pool:
            continue
        leaf = taxonomy[code]["leaf"]
        for desc in pool[: TRAINING_FLOOR - have]:
            synthetic.append({"code": code, "item": leaf, "desc": desc})

    if synthetic:
        print(f"\nsynthetic floor-clearing rows: {len(synthetic)}")
        for s in synthetic:
            print(f"    {s['code']}  {s['item']:24s} | {s['desc'][:52]}")

    # --- Stage 5: final projection ------------------------------------------
    final = Counter(r["category_code"] for r in kept_gold)
    final.update(h["code"] for h in harvested)
    final.update(s["code"] for s in synthetic)

    print("\nincome categories, final:")
    for code in sorted(c for c in taxonomy if c.startswith("ING-")):
        before = Counter(r["category_code"] for r in gold).get(code, 0)
        after = final.get(code, 0)
        state = "UNTRAINABLE" if after < 2 else ("weak" if after < 15 else "ok")
        print(f"    {code}  {before:4d} -> {after:4d}   {state:12s} {taxonomy[code]['leaf']}")

    still_starved = sorted(c for c in taxonomy if final.get(c, 0) < 2)
    print(f"\nstill untrainable (<2 examples): {len(still_starved)}")
    for c in still_starved:
        print(f"    {c}  n={final.get(c, 0)}  {taxonomy[c]['leaf']}")

    total = len(kept_gold) + len(harvested) + len(synthetic)
    print(f"\ntotal gold rows: {len(gold)} -> {total} "
          f"(-{len(quarantined)} quarantined, +{len(harvested)} harvested, "
          f"+{len(synthetic)} synthetic)")

    if not COMMIT:
        print("\n[DRY RUN] nothing written. Re-run with --commit to apply.")
        return

    # --- Stage 6: write ------------------------------------------------------
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = GOLD.parent / f"_master_gold.backup_{stamp}.csv"
    with open(backup, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(gold[0].keys()))
        w.writeheader()
        w.writerows(gold)
    print(f"\nbackup written: {backup.name}")

    # Quarantined rows are dropped from gold but recorded so the decision is
    # auditable and reversible without re-deriving it.
    qpath = ROOT / "Data" / "gold" / f"_quarantined_purchase_as_sale_{stamp}.csv"
    with open(qpath, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(gold[0].keys()))
        w.writeheader()
        w.writerows(quarantined)
    print(f"quarantine log: {qpath.name}")

    rows_out = [{**r, "direction": r.get("direction", ""), "split": r.get("split", "")}
                for r in kept_gold]

    for i, h in enumerate(harvested, 1):
        rows_out.append({
            "gold_id": f"HV-{i:05d}",
            "category_code": h["code"],
            "leaf": taxonomy[h["code"]]["leaf"],
            "source": "raw_ventas_harvest",
            "item_text": clean(h["item"]),
            "description": clean(h["desc"]),
            "provider": clean(h.get("provider")),
            "farm": "",
            "audit_reason": "Harvested from client's own VENTAS invoice; item name "
                            "states the category and direction is a sale.",
            "verify_flag": "",
            "direction": "VENTAS",
            "split": h.get("split", ""),
        })

    for i, s in enumerate(synthetic, 1):
        rows_out.append({
            "gold_id": f"SY-{i:05d}",
            "category_code": s["code"],
            "leaf": taxonomy[s["code"]]["leaf"],
            "source": "synthetic_floor",
            "item_text": clean(s["item"]),
            "description": clean(s["desc"]),
            "provider": "",
            "farm": "",
            "audit_reason": "SYNTHETIC. Generated only to clear the 2-example training "
                            "floor. Not a real invoice: no folio, no row_id. Never "
                            "used for validation.",
            "verify_flag": "synthetic",
            "direction": "VENTAS",
            "split": "",
        })

    with open(GOLD, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows([{k: r.get(k, "") for k in fields} for r in rows_out])

    print(f"wrote {len(rows_out)} rows to {GOLD.name}")


if __name__ == "__main__":
    main()
