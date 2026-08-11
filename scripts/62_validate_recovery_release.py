#!/usr/bin/env python3
"""Fail-closed local release audit for the focused recovery candidate."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from app.inference.business_rules import BusinessRules


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "Data/candidates/recovery_v1_2_0"
MODEL = ROOT / "models/setfit_base_recovery_v1_2_0"
REPORT = ROOT / "reports/recovery_v1_2_0/final_validation.json"
RAW = ROOT / "Data/processed/line_items.csv"
RULES = ROOT / "app/data/business_rules.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    manifest = json.loads((CANDIDATE / "manifest.json").read_text())
    for filename, expected in manifest["outputs"].items():
        require(sha256(CANDIDATE / filename) == expected, f"candidate hash mismatch: {filename}")

    master = read_csv(CANDIDATE / "master_gold.csv")
    require(len(master) == manifest["counts"]["final_rows"] == 1835, "unexpected master row count")
    require(not any(row["source"].startswith("synthetic") for row in master), "synthetic row present")
    require(
        not ({"SA-00757", "SA-00758", "SA-00874"} & {row["gold_id"] for row in master}),
        "quarantined purchase-as-income row present",
    )

    split = read_csv(CANDIDATE / "split_seed42.csv")
    train_hashes = {row["text_sha256"] for row in split if row["split"].startswith("train")}
    validation_hashes = {row["text_sha256"] for row in split if row["split"] == "validation"}
    require(not (train_hashes & validation_hashes), "train/validation model-input leakage")
    split_counts = Counter(row["split"] for row in split)
    require(split_counts == {"train": 1247, "train_weak": 21, "validation": 311, "excluded_lt2": 1},
            f"unexpected split counts: {dict(split_counts)}")

    rules = BusinessRules(RULES)
    raw_sales = [row for row in read_csv(RAW) if row["source"] == "VENTAS"]
    matched = []
    unmatched = []
    for row in raw_sales:
        hit = rules.match(row["nmb_item"], "VENTAS")
        (matched if hit else unmatched).append((row, hit))
    require(len(matched) == 118, f"expected 118 verified exact sales matches, got {len(matched)}")
    require(len(unmatched) == 7, f"expected 7 unknown sales for review, got {len(unmatched)}")
    require(
        Counter(row["nmb_item"] for row, _ in unmatched)
        == {"VENTA CAMIONETA": 3, "VENTA DE ACTIVO FIJO": 2, "OTROS INGRESOS": 1, "maquinaria": 1},
        "unexpected unknown VENTAS phrases",
    )
    require(all(rules.match(row["nmb_item"], "COMPRAS") is None for row, _ in matched),
            "VENTAS rule matched under COMPRAS direction")

    run = json.loads((MODEL / "run_manifest.json").read_text())
    require(run["full_encoder_trainable"] is True, "encoder was not fully trainable")
    require(run["trainable_encoder_parameters"] == run["total_encoder_parameters"], "frozen parameters")
    require(run["tracked_token_embedding_max_abs_delta"] > 0, "token embeddings did not change")
    require(run["unbounded_mps_watermark"] is False, "unbounded MPS watermark used")
    require(run["optimizer_observed"].endswith("AdamW"), "release optimizer was not AdamW")
    require(run["fixed_length_padding"] is True, "fixed-length MPS memory repair disabled")

    comparison_path = REPORT.parent / "model_comparison_fair.json"
    comparison = json.loads(comparison_path.read_text())
    failed_checks = [name for name, passed in comparison["release_checks"].items() if not passed]
    require(not failed_checks, f"model comparison release checks failed: {failed_checks}")

    report = {
        "status": "pass",
        "local_only": True,
        "candidate_manifest_sha256": sha256(CANDIDATE / "manifest.json"),
        "split_manifest_sha256": sha256(CANDIDATE / "split_seed42.csv"),
        "model_run_manifest_sha256": sha256(MODEL / "run_manifest.json"),
        "model_comparison_sha256": sha256(comparison_path),
        "gold": manifest["counts"],
        "income_counts": manifest["income_counts"],
        "split_counts": dict(split_counts),
        "exact_sales_lookup": {
            "verified_matches": len(matched),
            "unknown_for_review": len(unmatched),
            "unknown_item_counts": dict(Counter(row["nmb_item"] for row, _ in unmatched)),
        },
        "training": {
            "optimizer": run["optimizer_observed"],
            "full_encoder_trainable": run["full_encoder_trainable"],
            "token_embedding_delta": run["tracked_token_embedding_max_abs_delta"],
            "fixed_length_padding": run["fixed_length_padding"],
            "unbounded_mps_watermark": run["unbounded_mps_watermark"],
        },
        "model_release_checks": comparison["release_checks"],
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
