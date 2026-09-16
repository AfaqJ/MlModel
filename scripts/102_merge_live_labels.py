#!/usr/bin/env python3
"""Merge the settled labels in Supabase into the retrain candidate.

Gold alone was never the whole labelled set: 215 lines carry categories gold has
no row for at all (ADM-3.1, EXP-15.7, EXP-15.8), and thousands more were settled
by client product rules, exact taxonomy phrases and audited cleanup passes.
Training on gold only left those categories unlearnable.

What is taken from live, per `docs/LABELING_RULES.md` trust order:

  user_selected   a person at Antillanca chose it in the dashboard     (highest)
  gold            audited rows in Data/gold/_master_gold.csv
  cleanup         our audited passes applying client conventions
  business_rule   exact client/taxonomy phrase matches
  product_lookup  row-level client product labels
  meter_lookup    decided by CdgIntRecep, NOT by the text              (lowest)

What is refused:

  model auto-accepts   the model's own guesses. Measured auto-accept precision
                       on the locked test set was 0.70, so feeding them back
                       would teach roughly a third of its own mistakes.
  contradictions       one model input carrying two labels. Gold wins; between
                       live sources the higher trust level wins; a tie is
                       dropped, because the text genuinely cannot decide it
                       (electricity by meter, petrol by plate — D-029, D-068).
"""
from __future__ import annotations

import csv
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

CANDIDATE = ROOT / "Data/candidates/retrain_2026_09_15/master_gold.csv"
LIVE_ITEMS = ROOT / "reports/retrain_2026_09_16/live_settled_items.json"
LIVE_INVOICES = ROOT / "reports/retrain_2026_09_16/live_invoices.json"
OUT = ROOT / "Data/candidates/retrain_2026_09_16"
TRUST = {"user_selected": 5, "gold": 4, "cleanup": 3, "business_rule": 2, "product_lookup": 2, "meter_lookup": 1}


def main() -> None:
    with CANDIDATE.open(encoding="utf-8-sig", newline="") as handle:
        gold = list(csv.DictReader(handle))
    fields = list(gold[0].keys())

    items = json.loads(LIVE_ITEMS.read_text())
    invoices = {row["invoice_id"]: row for row in json.loads(LIVE_INVOICES.read_text())}

    kept, skipped = [], Counter()
    for row in items:
        source = row["prediction_source"]
        if source == "model":
            skipped["model_self_label"] += 1
            continue
        if source not in TRUST:
            skipped[f"unknown_source_{source}"] += 1
            continue
        invoice = invoices[row["invoice_id"]]
        if str(invoice.get("document_type") or "").lstrip("0") == "43":
            skipped["dte43_liquidacion"] += 1  # always review, no client category yet
            continue
        kept.append({
            **{field: "" for field in fields},
            "gold_id": f"LV-{row['item_id'][:8]}",
            "category_code": row["final_code"],
            "source": f"live_{source}",
            "item_text": row["item_text"] or "",
            "description": row["description"] or "",
            "provider": invoice["seller_name"] or "",
            "direction": invoice["transaction_type"],
            "direction_evidence": "live_invoice",
            "audit_reason": f"Supabase settled line, prediction_source={source}",
        })

    by_text: dict[str, list[dict]] = defaultdict(list)
    for row in gold:
        row["_trust"] = TRUST["gold"]
        by_text[normalize(build_text(row))].append(row)
    for row in kept:
        row["_trust"] = TRUST[row["source"].removeprefix("live_")]
        by_text[normalize(build_text(row))].append(row)

    merged, report = [], Counter()
    conflicts = []
    for text, rows in sorted(by_text.items()):
        labels = {row["category_code"] for row in rows}
        if len(labels) == 1:
            best = max(rows, key=lambda r: r["_trust"])
            merged.append(best)
            report["single_label" if len(rows) == 1 else "agreeing_duplicates"] += 1
            continue
        if all(row.get("verify_flag") == "conflict" for row in rows):
            for label in sorted(labels):  # D-029 plate pairs: keep both
                merged.append(max((r for r in rows if r["category_code"] == label), key=lambda r: r["_trust"]))
            report["plate_conflict_kept"] += 1
            continue
        top = max(row["_trust"] for row in rows)
        winners = {row["category_code"] for row in rows if row["_trust"] == top}
        if len(winners) == 1:
            merged.append(next(row for row in rows if row["_trust"] == top))
            report["conflict_resolved_by_trust"] += 1
            conflicts.append({"text": text, "kept": next(iter(winners)), "dropped": sorted(labels - winners), "trust": top})
        else:
            report["conflict_dropped_tie"] += 1
            conflicts.append({"text": text, "kept": None, "dropped": sorted(labels), "trust": top})

    OUT.mkdir(parents=True, exist_ok=True)
    for row in merged:
        row.pop("_trust", None)
    with (OUT / "master_gold.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(merged)
    (OUT / "conflicts.json").write_text(json.dumps(conflicts, indent=2, ensure_ascii=False) + "\n")

    # Both earlier splits are honoured, so no model being compared was ever
    # trained on a row that is now a test row (D-098).
    previous = {}
    for path, column in ((ROOT / "Data/candidates/recovery_v1_3_2/split_seed42.csv", "split"),
                         (ROOT / "Data/candidates/retrain_2026_09_15/split.csv", "split")):
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                seen = row[column]
                seen = "validation" if seen == "test" else seen
                # train wins over test: a row any compared model trained on can
                # never become a test row.
                if previous.get(row["text_sha256"], "").startswith("train") :
                    continue
                previous[row["text_sha256"]] = seen

    import hashlib

    def sha(text: str) -> str:
        return hashlib.sha256(normalize(text).encode()).hexdigest()

    by_class: dict[str, list[dict]] = defaultdict(list)
    for row in merged:
        by_class[row["category_code"]].append(row)

    assignments, split_rows = {}, []
    for code, class_rows in sorted(by_class.items()):
        fresh = []
        for row in class_rows:
            before = previous.get(sha(build_text(row)))
            if row.get("verify_flag") in {"synthetic", "conflict"} or row["source"].startswith("synthetic_"):
                assignments[row["gold_id"]] = "train"
            elif len(class_rows) < 5:
                assignments[row["gold_id"]] = "train_weak"
            elif before == "validation":
                assignments[row["gold_id"]] = "test"
            elif before in {"train", "train_weak"}:
                assignments[row["gold_id"]] = "train"
            else:
                fresh.append(row)
        fresh.sort(key=lambda r: hashlib.sha256(f"42\0{r['gold_id']}".encode()).hexdigest())
        n_test = round(len(fresh) * 0.20)
        if n_test == 0 and fresh and not any(assignments.get(r["gold_id"]) == "test" for r in class_rows):
            n_test = 1
        for index, row in enumerate(fresh):
            assignments[row["gold_id"]] = "test" if index < n_test else "train"

    for row in merged:
        split_rows.append({
            "split": assignments[row["gold_id"]], "gold_id": row["gold_id"],
            "category_code": row["category_code"], "text": build_text(row),
            "text_sha256": sha(build_text(row)),
            "previously": previous.get(sha(build_text(row)), "new"),
        })
    train_texts = {normalize(r["text"]) for r in split_rows if r["split"] != "test"}
    leaked = [r["gold_id"] for r in split_rows if r["split"] == "test" and normalize(r["text"]) in train_texts]
    if leaked:
        raise SystemExit(f"test inputs also present in train: {leaked[:10]}")
    with (OUT / "split.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(split_rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(sorted(split_rows, key=lambda r: (r["split"], r["category_code"], r["gold_id"])))
    with (OUT / "split_compat.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["gold_sha256", "seed", "split", "gold_id", "category_code", "text", "text_sha256"], lineterminator="\n")
        writer.writeheader()
        for row in split_rows:
            writer.writerow({"gold_sha256": "", "seed": "42", "split": "validation" if row["split"] == "test" else row["split"],
                             "gold_id": row["gold_id"], "category_code": row["category_code"],
                             "text": row["text"], "text_sha256": row["text_sha256"]})

    counts = Counter(row["category_code"] for row in merged)
    summary = {
        "gold_rows": len(gold),
        "live_settled_rows": len(items),
        "live_rows_taken": len(kept),
        "live_skipped": dict(skipped),
        "merge": dict(report),
        "distinct_model_inputs": len(merged),
        "classes": len(counts),
        "classes_under_15": sorted(code for code, n in counts.items() if n < 15),
        "classes_under_5": {code: n for code, n in sorted(counts.items()) if n < 5},
        "split_totals": dict(Counter(r["split"] for r in split_rows)),
        "test_rows_from_v1_3_3_validation": sum(1 for r in split_rows if r["split"] == "test" and r["previously"] == "validation"),
        "classes_without_test_rows": sorted({r["category_code"] for r in split_rows} - {r["category_code"] for r in split_rows if r["split"] == "test"}),
        "per_class": dict(sorted(counts.items())),
    }
    (OUT / "build_report.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "per_class"}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
