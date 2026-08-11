#!/usr/bin/env python3
"""Build a compact, reproducible release audit from local v1.3 outputs.

This script does not train, call an API, access a database, or use the network.
It validates the important release invariants, inventories the ignored model
artifacts by hash, and writes the manually reviewed diagnosis of the largest
review queues.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import joblib


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/recovery_v1_3_1"
REPLAY = REPORT / "local_replay"
GOLD = ROOT / "Data/candidates/recovery_v1_3_1/master_gold.csv"
TAXONOMY = ROOT / "Data/current_context_2026_06_30/taxonomy_from_plan.csv"
MODEL = ROOT / "models/setfit_base_recovery_v1_3_1"
ARTIFACT = ROOT / "artifacts/v1.3.1"


MANUAL_DIAGNOSIS = {
    "ADM-1.6": (
        "mixed: model overgeneralization plus generic invoice text",
        "Many SALFA/retail rows say only 'Item'; descriptions include machinery filters, oil, water and telecom. "
        "The text is not office-specific, so this is not a safe lookup candidate.",
    ),
    "EXP-9.2": (
        "semantic ambiguity and model error",
        "Irrigation parts and repairs overlap with water/purine, road, installation and machinery maintenance. "
        "Use/site context is often missing even though this class itself is not starving.",
    ),
    "EXP-14.3": (
        "semantic ambiguity and broad hardware wording",
        "Pumps, hoses and fittings can serve water, purine, irrigation or buildings. Generic hardware descriptions "
        "cannot reliably identify their farm use.",
    ),
    "ADM-1.7": (
        "coverage gap under conservative policy",
        "Repeated bank commissions, monitoring and toll wording is often clear, but the raw phrases were not exact "
        "client examples. They are good candidates for client-confirmed aliases, not silent gold promotion.",
    ),
    "EXP-14.1": (
        "coverage gap plus service ambiguity",
        "Earthworks and material transport often appear as generic service/hours/freight lines. The destination/use "
        "is needed to distinguish roads from irrigation, machinery rental and general freight.",
    ),
    "EXP-11.4": (
        "client-context conflict and conservative policy",
        "Gasolina 93/G93 is operational fuel for some providers but administration mobilization for another client "
        "mapping. Provider-free exact fallback is therefore intentionally disabled.",
    ),
    "EXP-7.0": (
        "mostly clear repeated phrases, but not client-authorized for auto-accept",
        "Control de roedores is semantically strong and repeatedly predicted as agrochemicals. It should become an "
        "exact alias only after the client confirms the accounting treatment.",
    ),
    "EXP-10.4": (
        "undertrained and abbreviated dairy-equipment wording",
        "Only nine distinct gold inputs. GEA service-kit and milking-machine parts overlap with dairy-room maintenance.",
    ),
    "ADM-1.2": (
        "undertrained",
        "Only ten distinct gold inputs. Telecom, internet, mobile, TV and decoder sub-lines vary heavily by provider.",
    ),
    "EXP-14.2": (
        "semantic ambiguity",
        "Wire, posts, tools and generic hardware may be for fences, buildings, irrigation or machinery. The item alone "
        "often cannot prove its actual use.",
    ),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized_distinct_by_category(rows: list[dict[str, str]]) -> dict[str, int]:
    def normalize(value: str) -> str:
        value = unicodedata.normalize("NFKD", value.lower()).encode("ascii", "ignore").decode()
        return re.sub(r"[^a-z0-9]+", " ", value).strip()

    values: defaultdict[str, set[str]] = defaultdict(set)
    for row in rows:
        description = row["description"].strip()
        if description and all(character in "0123456789 .,/-" for character in description):
            description = ""
        model_text = " | ".join(part for part in (
            f'[{row["direction"].strip().upper()}]',
            row["item_text"].strip(),
            description,
            row["provider"].strip(),
        ) if part)
        values[row["category_code"]].add(normalize(model_text))
    return {code: len(items) for code, items in values.items()}


def main() -> None:
    gold = read_csv(GOLD)
    taxonomy = read_csv(TAXONOMY)
    predictions = read_csv(REPLAY / "all_predictions.csv")
    replay = json.loads((REPLAY / "summary.json").read_text())
    calibration = json.loads((REPORT / "calibration_and_validation_audit.json").read_text())
    candidate = json.loads((GOLD.parent / "manifest.json").read_text())
    zero = json.loads((REPORT / "zero_value_audit/inventory_summary.json").read_text())
    card = json.loads((ARTIFACT / "model_card.json").read_text())
    bundle = json.loads((REPORT / "supabase_five_table_bundle/manifest.json").read_text())
    head = joblib.load(MODEL / "model_head.pkl")

    assert len(taxonomy) == 71
    assert len(head.classes_) == 67
    assert candidate["active_not_model_eligible"] == ["ADM-1.9", "ADM-2.3", "ING-0.5", "ING-0.6"]
    assert replay["raw_rows"] == 12206
    assert replay["rows_after_audited_zero_junk_filter"] == 11766
    assert replay["liquidacion_dte43_rows"] == 103
    assert replay["excluded_zero_junk_rows"] == 440
    assert replay["direction_safety"] == {
        "purchase_predicted_income": 0,
        "sale_predicted_expense": 0,
    }
    assert replay["auto_accept_risk_flags"]["serious_rule_or_known_label_conflicts"] == 0
    assert calibration["cascade"]["auto_accept_false_positives"] == 0
    assert calibration["inference_backend"] == "onnx_int8"
    assert card["thresholds"]["model_auto_accept"] is True
    assert card["parity_gate"]["threshold_decision_disagreement"] == 0
    assert all(bundle["invariants"].values())

    distinct = normalized_distinct_by_category(gold)
    review = [row for row in predictions if row["decision"] == "review_required"]
    review_by_category = Counter(row["prediction"] for row in review)
    reasons: defaultdict[str, Counter] = defaultdict(Counter)
    for row in review:
        reasons[row["prediction"]][row["reason"]] += 1

    diagnosis_rows = []
    names = {row["new_code"]: row["leaf"] for row in taxonomy}
    for code, count in review_by_category.most_common():
        diagnosis, explanation = MANUAL_DIAGNOSIS.get(
            code,
            (
                "review required; no single cause assigned",
                "See review_groups.csv for repeated raw phrases; predicted category is not verified truth.",
            ),
        )
        diagnosis_rows.append({
            "predicted_category": code,
            "category_name": names.get(code, ""),
            "review_rows": count,
            "distinct_gold_inputs": distinct.get(code, 0),
            "weak_lt15_distinct": distinct.get(code, 0) < 15,
            "reason_counts": json.dumps(dict(reasons[code].most_common()), ensure_ascii=False),
            "manual_diagnosis": diagnosis,
            "manual_explanation": explanation,
        })

    diagnosis_path = REPORT / "review_category_diagnosis.csv"
    with diagnosis_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=diagnosis_rows[0].keys())
        writer.writeheader()
        writer.writerows(diagnosis_rows)

    artifact_files = {
        str(path.relative_to(ROOT)): {"bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in sorted(ARTIFACT.rglob("*")) if path.is_file()
    }
    model_files = {
        str(path.relative_to(ROOT)): {"bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in sorted(MODEL.rglob("*")) if path.is_file()
    }
    manifest = {
        "release": "v1.3.1-local-only",
        "status": "not deployed, not pushed, no remote API tested",
        "authority_order": [
            "client meter context",
            "client taxonomy exact name and curated aliases",
            "client product lookup",
            "SetFit auto-accept only at top1 >= 0.75 and margin >= 0.50 outside weak/ambiguous cases",
        ],
        "validated_invariants": {
            "active_categories": len(taxonomy),
            "model_classes": len(head.classes_),
            "active_not_model_eligible": candidate["active_not_model_eligible"],
            "gold_rows": len(gold),
            "gold_transaction_distinct": candidate["counts"]["normalized_distinct_transaction_aware_inputs"],
            "gold_cross_label_contradictions": candidate["counts"]["cross_label_contradictions"],
            "raw_xml_item_lines": replay["raw_rows"],
            "retained_item_lines": replay["rows_after_audited_zero_junk_filter"],
            "liquidacion_dte43_review_rows": replay["liquidacion_dte43_rows"],
            "zero_value_junk_excluded": zero["audit_verdict_counts"]["EXCLUDE_JUNK"],
            "zero_value_genuine_or_uncertain_kept": zero["audit_verdict_counts"]["KEEP_GENUINE_OR_UNCERTAIN"],
            "local_auto_accept_rows": replay["decision_counts"]["auto_accept"],
            "local_review_rows": replay["decision_counts"]["review_required"],
            "heldout_auto_accept_false_positives": calibration["cascade"]["auto_accept_false_positives"],
            "raw_serious_auto_accept_conflicts": replay["auto_accept_risk_flags"]["serious_rule_or_known_label_conflicts"],
            "purchase_to_income_errors": replay["direction_safety"]["purchase_predicted_income"],
            "sale_to_expense_errors": replay["direction_safety"]["sale_predicted_expense"],
            "onnx_validation_accuracy": card["parity_gate"]["val_accuracy_int8_onnx"],
            "onnx_validation_macro_f1": card["parity_gate"]["val_macro_f1_int8_onnx"],
            "onnx_threshold_decision_disagreement": card["parity_gate"]["threshold_decision_disagreement"],
            "supabase_invoice_headers": bundle["counts"]["invoices"],
            "supabase_retained_invoice_items": bundle["counts"]["invoice_items"],
            "supabase_explicit_junk_reconciliation_keys": bundle["counts"]["reconcile_delete_junk_lines"],
        },
        "artifact_files": artifact_files,
        "training_model_files": model_files,
        "source_hashes": {
            str(GOLD.relative_to(ROOT)): sha256(GOLD),
            str((GOLD.parent / "split_seed42.csv").relative_to(ROOT)): sha256(GOLD.parent / "split_seed42.csv"),
            str((REPLAY / "summary.json").relative_to(ROOT)): sha256(REPLAY / "summary.json"),
            str(diagnosis_path.relative_to(ROOT)): sha256(diagnosis_path),
        },
    }
    (REPORT / "local_release_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest["validated_invariants"], indent=2))


if __name__ == "__main__":
    main()
