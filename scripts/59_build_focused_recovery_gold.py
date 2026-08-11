#!/usr/bin/env python3
"""Build the focused, reversible gold candidate for the milk-sales repair.

This deliberately starts from the last pre-Claude gold snapshot. It removes
three verified COMPRAS rows that were mislabeled as income and adds only raw
VENTAS rows whose item text exactly names an existing income category. It does
not import Claude's broad silver promotion and it never creates synthetic data.

The source files are read-only. Output goes to Data/candidates/recovery_v1_2_0
and is refused if it already exists unless --overwrite is supplied.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = ROOT / "Data/gold/_master_gold.backup_20260811_104643.csv"
DEFAULT_RAW = ROOT / "Data/processed/line_items.csv"
DEFAULT_OUTPUT = ROOT / "Data/candidates/recovery_v1_2_0"

# These rows were found in COMPRAS, not VENTAS. Their existing income labels
# teach the exact opposite transaction direction.
QUARANTINE = {
    "SA-00757": ("ING-0.2", "vacas"),
    "SA-00758": ("ING-0.2", "vacas preñadas"),
    "SA-00874": ("ING-0.6", "leña"),
}

# Exact normalized item-name matches only. Asset disposals and "other income"
# are intentionally absent because the taxonomy has no verified destination.
SALES_MAP = {
    "venta de leche": ("ING-0.1", "VENTA DE LECHE"),
    "venta de vacas": ("ING-0.2", "VENTA DE VACAS"),
    "venta de vaquillas": ("ING-0.3", "VENTA VAQUILLAS"),
    "ventas terneros": ("ING-0.4", "VENTA TERNEROS"),
    "venta de terneras": ("ING-0.4", "VENTA TERNEROS"),
}

OUTPUT_FIELDS = [
    "gold_id", "category_code", "leaf", "source", "item_text",
    "description", "provider", "farm", "audit_reason", "verify_flag",
    "direction", "raw_row_id",
]
NUMERIC_DESCRIPTION_RE = re.compile(r"[\d\s.,\-/]+$")


def norm(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", (value or "").lower())
    value = value.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def model_description(value: str | None) -> str:
    value = clean(value)
    return "" if not value or NUMERIC_DESCRIPTION_RE.fullmatch(value) else value


def model_key(row: dict[str, str]) -> str:
    """Normalized form of the exact joined string consumed by the base model."""
    text = " | ".join(
        part
        for part in (
            clean(row["item_text"]),
            model_description(row["description"]),
            clean(row["provider"]),
        )
        if part
    )
    return norm(text)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def validate_quarantine(base_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_id = {row["gold_id"]: row for row in base_rows}
    missing = sorted(set(QUARANTINE) - set(by_id))
    if missing:
        raise RuntimeError(f"quarantine rows missing from base snapshot: {missing}")
    selected = []
    for gold_id, (expected_code, expected_item) in QUARANTINE.items():
        row = by_id[gold_id]
        observed = (row["category_code"], norm(row["item_text"]))
        expected = (expected_code, norm(expected_item))
        if observed != expected:
            raise RuntimeError(
                f"quarantine guard failed for {gold_id}: expected {expected}, got {observed}"
            )
        selected.append(row)
    return selected


def assert_no_cross_label_contradictions(rows: list[dict[str, str]]) -> None:
    labels_by_input: defaultdict[str, set[str]] = defaultdict(set)
    ids_by_input: defaultdict[str, list[str]] = defaultdict(list)
    for row in rows:
        key = model_key(row)
        labels_by_input[key].add(row["category_code"])
        ids_by_input[key].append(row["gold_id"])
    conflicts = {
        key: sorted(labels)
        for key, labels in labels_by_input.items()
        if len(labels) > 1
    }
    if conflicts:
        sample = [
            {"input": key, "labels": labels, "gold_ids": ids_by_input[key]}
            for key, labels in list(sorted(conflicts.items()))[:10]
        ]
        raise RuntimeError(f"cross-label model-input contradictions: {sample}")


def build(base_rows: list[dict[str, str]], raw_rows: list[dict[str, str]]):
    quarantined = validate_quarantine(base_rows)
    quarantine_ids = set(QUARANTINE)

    kept: list[dict[str, str]] = []
    for original in base_rows:
        if original["gold_id"] in quarantine_ids:
            continue
        row = {field: clean(original.get(field, "")) for field in OUTPUT_FIELDS}
        if norm(row["item_text"]) in SALES_MAP and row["category_code"].startswith("ING-"):
            row["direction"] = "VENTAS"
        kept.append(row)

    seen = {(model_key(row), row["category_code"]) for row in kept}
    label_by_input: dict[str, str] = {}
    for row in kept:
        label_by_input.setdefault(model_key(row), row["category_code"])

    harvested: list[dict[str, str]] = []
    skipped_existing = 0
    for raw in raw_rows:
        if clean(raw.get("source")) != "VENTAS":
            continue
        mapped = SALES_MAP.get(norm(raw.get("nmb_item")))
        if mapped is None:
            continue
        code, leaf = mapped
        candidate = {
            "gold_id": f"RV-{int(raw['row_id']):05d}",
            "category_code": code,
            "leaf": leaf,
            "source": "raw_ventas_exact",
            "item_text": clean(raw.get("nmb_item")),
            "description": clean(raw.get("dsc_item")),
            "provider": clean(raw.get("rzn_soc_emisor")),
            "farm": "",
            "audit_reason": (
                "Exact canonical item name on the client's own VENTAS invoice; "
                "label and transaction direction are explicit."
            ),
            "verify_flag": "",
            "direction": "VENTAS",
            "raw_row_id": clean(raw.get("row_id")),
        }
        key = model_key(candidate)
        established = label_by_input.get(key)
        if established is not None and established != code:
            raise RuntimeError(
                f"raw row {raw['row_id']} contradicts established label {established} with {code}"
            )
        labeled_key = (key, code)
        if labeled_key in seen:
            skipped_existing += 1
            continue
        seen.add(labeled_key)
        label_by_input.setdefault(key, code)
        harvested.append(candidate)

    final_rows = kept + harvested
    assert_no_cross_label_contradictions(final_rows)
    return final_rows, quarantined, harvested, skipped_existing


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_rows = read_csv(args.base)
    raw_rows = read_csv(args.raw)
    final_rows, quarantined, harvested, skipped_existing = build(base_rows, raw_rows)

    if args.output_dir.exists():
        if not args.overwrite:
            raise SystemExit(f"refusing to overwrite {args.output_dir}; pass --overwrite")
        shutil.rmtree(args.output_dir)
    args.output_dir.mkdir(parents=True)

    master_path = args.output_dir / "master_gold.csv"
    quarantine_path = args.output_dir / "quarantined_purchase_as_income.csv"
    harvest_path = args.output_dir / "harvested_raw_ventas.csv"
    write_csv(master_path, final_rows, OUTPUT_FIELDS)
    write_csv(quarantine_path, quarantined, list(base_rows[0]))
    write_csv(harvest_path, harvested, OUTPUT_FIELDS)

    income_counts = Counter(
        row["category_code"] for row in final_rows if row["category_code"].startswith("ING-")
    )
    manifest = {
        "candidate": "recovery_v1_2_0",
        "policy": "pre-Claude gold minus 3 verified direction errors plus exact canonical raw VENTAS; no synthetic data",
        "inputs": {
            str(args.base.relative_to(ROOT)): sha256(args.base),
            str(args.raw.relative_to(ROOT)): sha256(args.raw),
        },
        "counts": {
            "base_rows": len(base_rows),
            "quarantined_rows": len(quarantined),
            "harvested_rows": len(harvested),
            "raw_rows_already_present": skipped_existing,
            "final_rows": len(final_rows),
            "normalized_distinct_model_inputs": len({model_key(row) for row in final_rows}),
            "synthetic_rows": 0,
        },
        "income_counts": dict(sorted(income_counts.items())),
        "quarantined_gold_ids": sorted(QUARANTINE),
        "canonical_sales_map": {key: value[0] for key, value in SALES_MAP.items()},
        "outputs": {},
    }
    for path in (master_path, quarantine_path, harvest_path):
        manifest["outputs"][path.name] = sha256(path)
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

    print(json.dumps(manifest["counts"], indent=2))
    print(f"income counts: {dict(sorted(income_counts.items()))}")
    print(f"wrote focused candidate to {args.output_dir}")


if __name__ == "__main__":
    main()
