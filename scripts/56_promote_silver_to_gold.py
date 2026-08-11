#!/usr/bin/env python3
"""Re-promote audited silver rows to gold using a dedup key that matches the
model's actual input.

WHY THIS SCRIPT EXISTS
----------------------
The historical promotion script
(Data/stale/scripts_labeling_pipeline_2026_07_03/48_promote_starving_audit.py)
deduplicated promotions on:

    (normalized_item_text, category_code)

but the model's input is built from THREE fields:

    "item_text | description | provider"      (training/train_setfit.py::build_text)

So the key was blind to two fields that are inside the model's input. 47 milk-sale
rows with 47 genuinely distinct descriptions (different volumes, prices, tanks,
farms) collapsed to a single gold row. train_setfit.py then drops any class with
fewer than 2 examples, so ING-0.1 was never trained at all -> BUG-001.

Worse, that script pre-seeded its `seen` set with the EXISTING gold rows, so once
one milk row was in gold, no other milk row could ever be promoted.

THE FIX
-------
Dedup on (item_text, description, provider, category_code), normalized. This is
exactly the set of fields the model consumes, plus the label. See DECISIONS.md
D-001: a dedup key must contain every field the model consumes.

SAFETY
------
Dry run by default. --commit backs up _master_gold.csv first. Writes nothing
except Data/gold/_master_gold.csv. No network access.

Usage:
    .venv-train/bin/python scripts/56_promote_silver_to_gold.py            # dry run
    .venv-train/bin/python scripts/56_promote_silver_to_gold.py --commit
"""
from __future__ import annotations

import csv
import glob
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "Data" / "gold" / "_master_gold.csv"
SILVER_DIR = ROOT / "Data" / "silver"
TAXONOMY = ROOT / "Data" / "current_context_2026_06_30" / "taxonomy_from_plan.csv"

COMMIT = "--commit" in sys.argv


def norm(text: str | None) -> str:
    """Normalize for comparison only: lowercase, strip accents, collapse
    punctuation to spaces. The ORIGINAL text is what gets written to gold —
    this is purely a matching key."""
    s = "" if text is None else str(text).lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", s).strip()


def clean(text: str | None) -> str:
    """Collapse whitespace but preserve the original characters."""
    return re.sub(r"\s+", " ", "" if text is None else str(text)).strip()


def read_csv(path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def dedup_key(item: str, desc: str, prov: str, code: str) -> tuple:
    """THE key. Mirrors training/train_setfit.py::build_text field-for-field.
    If the model's input template ever changes, this changes with it."""
    return (norm(item), norm(desc), norm(prov), code)


def text_key(item: str, desc: str, prov: str) -> tuple:
    """The same fields WITHOUT the label.

    Two rows sharing this key are the *same model input*. If they carry
    different category codes, the model is being shown one input with two
    correct answers — an unlearnable contradiction that teaches it to be
    uncertain in that region of embedding space.

    dedup_key alone does NOT catch this: because the code is part of that key,
    a row with the same text but a different code produces a *different* key,
    passes the duplicate check, and is appended next to the row it contradicts.
    Gold had zero such contradictions before this script first ran and 46
    afterwards, affecting 96 rows. Hence this second key."""
    return (norm(item), norm(desc), norm(prov))


def load_silver_ledger() -> list[dict]:
    """Data/silver/ holds THREE different file schemas. Only the per-category
    audit ledger (the one with a `verdict` column) carries human-confirmed
    labels. The 4,135-row _candidate_pool / _pool_classified files are raw
    Ollama output and are NOT gold material. _index.csv is a summary.

    Summing all files in this directory gives a meaningless number — that
    mistake has already been made once on this project."""
    ledger: list[dict] = []
    for path in sorted(glob.glob(str(SILVER_DIR / "*.csv"))):
        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            if "verdict" not in (reader.fieldnames or []):
                continue
            for row in reader:
                row["_source_file"] = os.path.basename(path)
                ledger.append(row)
    return ledger


def main() -> None:
    taxonomy = {r["new_code"]: r for r in read_csv(TAXONOMY)}
    gold = read_csv(GOLD)
    gold_fields = list(gold[0].keys())
    ledger = load_silver_ledger()

    print(f"gold rows              : {len(gold)}")
    print(f"silver audit ledger    : {len(ledger)}")

    # --- Stage 1: what is usable at all -------------------------------------
    usable = []
    dropped = Counter()
    for r in ledger:
        verdict = (r.get("verdict") or "").strip()
        if not verdict:
            dropped["no verdict (never audited)"] += 1
            continue
        if verdict.upper().startswith("REJECT"):
            dropped["REJECT verdict"] += 1
            continue
        if not (r.get("item_text") or "").strip():
            dropped["empty item_text"] += 1
            continue
        if verdict not in taxonomy:
            dropped[f"verdict not in taxonomy ({verdict})"] += 1
            continue
        usable.append(r)

    print(f"usable audited rows    : {len(usable)}")
    for reason, n in dropped.most_common():
        print(f"    dropped {n:5d}  {reason}")

    # --- Stage 2: quarantine contradictory names ----------------------------
    # If the same item name was audited into two different categories, we do not
    # get to guess which is right. Hold them back for manual resolution.
    verdicts_by_name: dict[str, set[str]] = defaultdict(set)
    for r in usable:
        verdicts_by_name[norm(r["item_text"])].add(r["verdict"].strip())
    conflicting = {n for n, v in verdicts_by_name.items() if len(v) > 1}

    clean_rows = [r for r in usable if norm(r["item_text"]) not in conflicting]
    held = len(usable) - len(clean_rows)
    print(f"\nconflicting item names : {len(conflicting)}  -> {held} rows held back")

    # --- Stage 3: promote with the FIXED key --------------------------------
    seen = {dedup_key(r["item_text"], r["description"], r["provider"], r["category_code"])
            for r in gold}

    # Established gold wins. A bulk-approved silver row may never overrule a
    # client-supplied example, a file audit, or an earlier vetted silver row.
    gold_label_of = {}
    for r in gold:
        gold_label_of.setdefault(
            text_key(r["item_text"], r["description"], r["provider"]), r["category_code"])

    promoted = []
    skipped_dupe = 0
    contradictions = []
    for r in clean_rows:
        code = r["verdict"].strip()
        tkey = text_key(r["item_text"], r["description"], r["provider"])

        established = gold_label_of.get(tkey)
        if established is not None and established != code:
            contradictions.append((r, established, code))
            continue

        key = dedup_key(r["item_text"], r["description"], r["provider"], code)
        if key in seen:
            skipped_dupe += 1
            continue
        seen.add(key)
        # Claim the text so two *new* rows can't contradict each other either.
        gold_label_of.setdefault(tkey, code)
        promoted.append(r)

    print(f"already in gold (by key): {skipped_dupe}")
    print(f"CONTRADICTED gold       : {len(contradictions)}  (skipped — established gold wins)")
    for r, old, new in contradictions[:8]:
        print(f"    gold says {old:9s} / silver says {new:9s}  <- {r['item_text'][:44]}")
    if len(contradictions) > 8:
        print(f"    ... and {len(contradictions)-8} more (full list written on --commit)")
    print(f"NEW rows to promote     : {len(promoted)}")

    # Audit-quality split: how much of this was individually reasoned vs
    # accepted in a per-category batch. Recorded so the caveat stays visible.
    quality = Counter()
    for r in promoted:
        reason = (r.get("audit_reason") or "").strip()
        quality["individually reasoned" if reason not in ("2step_review", "wave2_review", "")
                else "bulk batch tag"] += 1
    for k, n in quality.most_common():
        print(f"    {n:5d}  {k}")

    # --- Stage 4: report the effect per category ----------------------------
    before = Counter(r["category_code"] for r in gold)
    added = Counter(r["verdict"].strip() for r in promoted)
    after = before + added

    print(f"\n{'code':10s} {'before':>7s} {'after':>7s}  {'delta':>6s}  status        leaf")
    print("-" * 88)
    for code in sorted(taxonomy):
        b, a = before.get(code, 0), after.get(code, 0)
        if a == 0:
            status = "NO EXAMPLES"
        elif a < 2:
            status = "UNTRAINABLE"
        elif a < 15:
            status = "weak"
        else:
            status = "ok"
        mark = "  <-- " if a != b else "      "
        print(f"{code:10s} {b:7d} {a:7d}  {a-b:+6d}{mark}{status:12s}  {taxonomy[code]['leaf'][:34]}")

    def bucket(counter):
        return (sum(1 for c in taxonomy if counter.get(c, 0) == 0),
                sum(1 for c in taxonomy if counter.get(c, 0) == 1),
                sum(1 for c in taxonomy if counter.get(c, 0) >= 2),
                sum(1 for c in taxonomy if counter.get(c, 0) >= 15))

    b0, b1, b2, b15 = bucket(before)
    a0, a1, a2, a15 = bucket(after)
    print(f"\n{'':22s} before  after")
    print(f"{'categories with 0':22s} {b0:6d} {a0:6d}")
    print(f"{'categories with 1':22s} {b1:6d} {a1:6d}   (untrainable: <2)")
    print(f"{'categories trainable':22s} {b2:6d} {a2:6d}   (>=2 examples)")
    print(f"{'categories >=15':22s} {b15:6d} {a15:6d}")
    print(f"{'total gold rows':22s} {len(gold):6d} {len(gold)+len(promoted):6d}")

    if not COMMIT:
        print("\n[DRY RUN] nothing written. Re-run with --commit to apply.")
        return

    # --- Stage 5: write, with a backup first ---------------------------------
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = GOLD.parent / f"_master_gold.backup_{stamp}.csv"
    with open(backup, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=gold_fields)
        w.writeheader()
        w.writerows(gold)
    print(f"\nbackup written: {backup.name}")

    # Persist the contradictions: each one is a real disagreement between an
    # established label and an audited silver verdict, and deserves a human look.
    if contradictions:
        cpath = GOLD.parent / f"_contradicted_not_promoted_{stamp}.csv"
        with open(cpath, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["item_text", "description", "provider",
                        "established_gold_code", "silver_verdict_code", "audit_reason"])
            for r, old, new in contradictions:
                w.writerow([clean(r["item_text"]), clean(r.get("description")),
                            clean(r.get("provider")), old, new, clean(r.get("audit_reason"))])
        print(f"contradiction log: {cpath.name}  ({len(contradictions)} rows for human review)")

    start = max([int(m.group(1)) for r in gold
                 if (m := re.match(r"SP-(\d+)$", r.get("gold_id", "")))] + [0])

    new_rows = []
    for i, r in enumerate(promoted, start + 1):
        code = r["verdict"].strip()
        new_rows.append({
            "gold_id": f"SP-{i:05d}",
            "category_code": code,
            "leaf": taxonomy[code]["leaf"],
            "source": "silver_audit_v2",
            "item_text": clean(r["item_text"]),
            "description": clean(r.get("description")),
            "provider": clean(r.get("provider")),
            "farm": "",
            "audit_reason": f"[re-promoted with dedup key incl. description+provider] "
                            f"{clean(r.get('audit_reason')) or 'audited silver'}",
            "verify_flag": "",
        })

    with open(GOLD, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=gold_fields)
        w.writeheader()
        w.writerows(gold)
        w.writerows([{k: r.get(k, "") for k in gold_fields} for r in new_rows])

    print(f"wrote {len(gold) + len(new_rows)} rows to {GOLD.name} (+{len(new_rows)})")
    print("next: scripts/55_contradiction_audit.py, then scripts/50_build_gold_views.py")


if __name__ == "__main__":
    main()
