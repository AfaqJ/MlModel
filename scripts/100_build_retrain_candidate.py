#!/usr/bin/env python3
"""Build the 2026-09 retrain candidate and its locked train/test split.

Reads `Data/gold/_master_gold.csv` and writes a separate candidate folder; gold
itself, Supabase and every deployed artifact are left alone.

1. Direction: the raw XML line (`Data/processed/line_items.csv`, folder
   COMPRAS/VENTAS) when the gold row matches one, otherwise the category family
   (`ING-` is a sale). The two are asserted to agree wherever both exist.
2. Restores the audited rows the v1.3.3 candidate trained on that master gold
   never received, when their model input is absent from master gold.
3. Adds D-005 synthetic rows for ADM-1.9 (one real row) in the candidate only.
4. Locked split, so no evaluated model has seen a test row:
   - v1.3.3's validation inputs stay test; its training inputs stay train;
   - 20% of each class's new inputs become test;
   - classes under 5 distinct inputs, synthetic rows and plate-conflict rows
     (verify_flag=conflict, D-029) are train only.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("trainer", ROOT / "training/train_recovery_setfit.py")
trainer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trainer)
normalize, build_text, clean_description = trainer.normalize, trainer.build_text, trainer.clean_description

GOLD = ROOT / "Data/gold/_master_gold.csv"
PREVIOUS = ROOT / "Data/candidates/recovery_v1_3_2"
RAW = ROOT / "Data/processed/line_items.csv"
OUT = ROOT / "Data/candidates/retrain_2026_09_15"
SEED = 42
TEST_FRACTION = 0.20
SYNTHETIC_ADM_1_9 = ["ASESORIA LEGAL", "SERVICIOS DE ASESORIA LEGAL"]  # D-005: up to 3 rows in total


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def family_direction(code: str) -> str:
    return "VENTAS" if code.startswith("ING-") else "COMPRAS"


def main() -> None:
    gold = read(GOLD)
    fields = list(gold[0].keys()) + ["direction_evidence"]

    raw_full, raw_item = defaultdict(set), defaultdict(set)
    for row in read(RAW):
        item, provider = normalize(row["nmb_item"]), normalize(row["rzn_soc_emisor"])
        raw_full[(item, normalize(clean_description(row["dsc_item"])), provider)].add(row["source"])
        raw_item[(item, provider)].add(row["source"])

    evidence = Counter()
    for row in gold:
        item, provider = normalize(row["item_text"]), normalize(row["provider"])
        found = raw_full.get((item, normalize(clean_description(row["description"])), provider)) or raw_item.get((item, provider))
        family = family_direction(row["category_code"])
        if found and len(found) == 1:
            direction = next(iter(found))
            if direction != family:
                raise SystemExit(f"{row['gold_id']}: raw XML says {direction}, category family says {family}")
            row["direction_evidence"] = "raw_xml_folder"
        else:
            direction = family
            row["direction_evidence"] = "category_family"
        if row["direction"] and row["direction"] != direction:
            raise SystemExit(f"{row['gold_id']}: explicit direction {row['direction']} disagrees with {direction}")
        row["direction"] = direction
        evidence[row["direction_evidence"]] += 1

    gold_texts = {normalize(build_text(row)) for row in gold}
    gold_ids = {row["gold_id"] for row in gold}
    restored = []
    for row in read(PREVIOUS / "master_gold.csv"):
        if row["gold_id"] in gold_ids or normalize(build_text(row)) in gold_texts:
            continue
        restored.append({**{f: row.get(f, "") for f in fields}, "direction_evidence": "restored_from_v1_3_2"})

    synthetic = [{
        **{f: "" for f in fields},
        "gold_id": f"SY-RT-{index:03d}", "category_code": "ADM-1.9", "leaf": "Asesoria Legal",
        "source": "synthetic_floor", "item_text": text, "verify_flag": "synthetic",
        "direction": "COMPRAS", "direction_evidence": "synthetic",
        "audit_reason": "D-005 floor rows for training only; never in gold, Supabase or test.",
    } for index, text in enumerate(SYNTHETIC_ADM_1_9, start=1)]

    rows = gold + restored + synthetic
    OUT.mkdir(parents=True, exist_ok=True)
    candidate = OUT / "master_gold.csv"
    with candidate.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    collapsed, collapse_audit = trainer.load_and_collapse(candidate)

    previous_split = {}
    for row in read(PREVIOUS / "split_seed42.csv"):
        previous_split[row["text_sha256"]] = row["split"]

    by_class = defaultdict(list)
    for row in collapsed:
        by_class[row["category_code"]].append(row)

    assignments = {}
    for code, class_rows in sorted(by_class.items()):
        distinct = len({normalize(row["text"]) for row in class_rows})
        new_rows = []
        for row in class_rows:
            sha = hashlib.sha256(normalize(row["text"]).encode()).hexdigest()
            before = previous_split.get(sha)
            if row.get("verify_flag") in {"synthetic", "conflict"} or row["source"].startswith("synthetic_"):
                assignments[row["gold_id"]] = "train"
            elif distinct < 5:
                assignments[row["gold_id"]] = "train_weak"
            elif before == "validation":
                assignments[row["gold_id"]] = "test"
            elif before in {"train", "train_weak"}:
                assignments[row["gold_id"]] = "train"
            elif row.get("split") == "holdout":  # D-004 harvest holdout
                assignments[row["gold_id"]] = "test"
            else:
                new_rows.append(row)
        new_rows.sort(key=lambda row: hashlib.sha256(f"{SEED}\0{row['gold_id']}".encode()).hexdigest())
        n_test = round(len(new_rows) * TEST_FRACTION)
        has_test = any(assignments.get(row["gold_id"]) == "test" for row in class_rows)
        if n_test == 0 and new_rows and not has_test:
            n_test = 1
        for index, row in enumerate(new_rows):
            assignments[row["gold_id"]] = "test" if index < n_test else "train"

    split_rows, counts = [], defaultdict(Counter)
    for row in collapsed:
        split = assignments[row["gold_id"]]
        counts[row["category_code"]][split] += 1
        split_rows.append({
            "split": split, "gold_id": row["gold_id"], "category_code": row["category_code"],
            "text": row["text"], "text_sha256": hashlib.sha256(normalize(row["text"]).encode()).hexdigest(),
            "previously": previous_split.get(hashlib.sha256(normalize(row["text"]).encode()).hexdigest(), "new"),
        })
    with (OUT / "split.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(split_rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(sorted(split_rows, key=lambda r: (r["split"], r["category_code"], r["gold_id"])))

    train_texts = {normalize(r["text"]) for r in split_rows if r["split"] != "test"}
    leaked = [r["gold_id"] for r in split_rows if r["split"] == "test" and normalize(r["text"]) in train_texts]
    if leaked:
        raise SystemExit(f"test inputs also present in train: {leaked[:10]}")

    report = {
        "gold_rows": len(gold),
        "restored_from_v1_3_2": len(restored),
        "synthetic_rows": len(synthetic),
        "candidate_rows": len(rows),
        "direction_evidence": dict(evidence),
        "collapse": collapse_audit,
        "classes": len(by_class),
        "split_totals": dict(Counter(r["split"] for r in split_rows)),
        "test_rows_seen_by_v1_3_3_as_validation": sum(1 for r in split_rows if r["split"] == "test" and r["previously"] == "validation"),
        "classes_without_test_rows": sorted(code for code, c in counts.items() if not c["test"]),
        "per_class": {code: dict(c) for code, c in sorted(counts.items())},
    }
    (OUT / "build_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "per_class"}, indent=2))


if __name__ == "__main__":
    main()
