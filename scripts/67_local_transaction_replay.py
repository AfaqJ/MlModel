#!/usr/bin/env python3
"""Replay all 12,103 locally extracted XML lines through the v1.3.1 cascade.

No API, database, deployment, or network call is made. CdgIntRecep and
MontoItem are reparsed from the local XML because the old line_items.csv parser
discarded the amount (`MntItem` typo) and did not retain the electricity meter.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.inference.business_rules import BusinessRules, direction_mask
from app.inference.confidence import decide, entropy
from app.inference.meter_lookup import MeterLookup
from app.inference.model_input import build_model_text
from app.inference.product_lookup import ProductLookup
from app.inference.line_filters import zero_value_junk_reason
from app.inference.ambiguity_guard import model_review_guard_reason
from app.inference.onnx_encoder import OnnxEncoder
from app.inference.classifier import LogisticHead


ARTIFACT = ROOT / "artifacts/v1.3.1"
RAW = ROOT / "Data/processed/line_items.csv"
GOLD = ROOT / "Data/candidates/recovery_v1_3_1/master_gold.csv"
THRESHOLDS = ROOT / "reports/recovery_v1_3_1/selected_thresholds.json"
OUTPUT = ROOT / "reports/recovery_v1_3_1/local_replay"
RAW_ROOT = ROOT / "Data/Raw_Data"
FIELDS = [
    "row_id", "input_id", "source_file", "period", "folio", "nro_lin_det", "direction",
    "invoice_date", "document_type", "provider_rut", "provider_giro",
    "item_text", "description", "provider", "farm", "meter_code", "amount",
    "unit_price",
    "source", "prediction", "top1", "margin", "entropy", "decision", "reason", "top3",
    "model_prediction", "model_top1", "lookup_conflict", "exact_known_truth",
    "exact_known_consistent", "risk_flags",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def build_xml_index() -> dict[str, dict[str, Path]]:
    """Index the authoritative COMPRAS/VENTAS trees by unique XML filename.

    The folder month is not reliably the same as FchEmis/processed `period`.
    Deriving the path from that date made 1,497 valid documents look missing.
    Filenames are unique within each authoritative source tree, so filename plus
    transaction direction is the stable local join key.
    """
    roots = {
        "COMPRAS": RAW_ROOT / "dte_96685810_COMPRAS",
        "VENTAS": RAW_ROOT / "dte_96685810_VENTAS",
    }
    result: dict[str, dict[str, Path]] = {}
    for direction, root in roots.items():
        index: dict[str, Path] = {}
        duplicates: list[str] = []
        for path in sorted(root.rglob("*.xml")):
            if path.name in index:
                duplicates.append(path.name)
            index[path.name] = path
        if duplicates:
            raise RuntimeError(
                f"duplicate XML filenames in {direction}; cannot join safely: {duplicates[:5]}"
            )
        result[direction] = index
    return result


def node_text(node: ET.Element, local_name: str) -> str:
    found = node.find(f".//{{*}}{local_name}")
    return (found.text or "").strip() if found is not None else ""


def parse_local_xml(path: Path) -> ET.Element:
    raw = path.read_bytes()
    try:
        xml_text = raw.decode("utf-8")
    except UnicodeDecodeError:
        xml_text = raw.decode("latin-1")
    return ET.fromstring(xml_text.encode("utf-8"))


def parse_xml_context(path: Path) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    root = parse_local_xml(path)
    metadata = {
        "meter_code": node_text(root, "CdgIntRecep"),
        "provider_rut": re.sub(r"[^0-9Kk]", "", node_text(root, "RUTEmisor")).upper(),
        "provider_giro": node_text(root, "GiroEmis"),
        "invoice_date": node_text(root, "FchEmis"),
        "document_type": node_text(root, "TipoDTE"),
    }
    details = {}
    for detail in root.findall(".//{*}Detalle"):
        line = node_text(detail, "NroLinDet")
        # Correct SII tag is MontoItem. The old extractor requested MntItem.
        details[line] = {
            "amount": node_text(detail, "MontoItem"),
            "unit_price": node_text(detail, "PrcItem"),
        }
    return metadata, details


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, default=ARTIFACT)
    parser.add_argument("--raw", type=Path, default=RAW)
    parser.add_argument("--gold", type=Path, default=GOLD)
    parser.add_argument("--thresholds", type=Path, default=THRESHOLDS)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--batch-size", type=int, default=128)
    args = parser.parse_args()

    raw_rows = read_csv(args.raw)
    if len(raw_rows) != 12103:
        raise RuntimeError(f"expected 12,103 local raw rows, found {len(raw_rows)}")
    gold_rows = read_csv(args.gold)
    model_card = json.loads((args.artifact / "model_card.json").read_text())
    thresholds = model_card["thresholds"]

    taxonomy = {
        row["new_code"]: row["leaf"]
        for row in read_csv(ROOT / "Data/current_context_2026_06_30/taxonomy_from_plan.csv")
    }
    rules = BusinessRules(ROOT / "app/data/business_rules.csv")
    products = ProductLookup(ROOT / "app/data/product_lookup.csv")
    meters = MeterLookup(ROOT / "app/data/electricity_meter_map.csv")
    xml_index = build_xml_index()

    body = OnnxEncoder(args.artifact)
    head = LogisticHead(args.artifact)
    classes = np.asarray([str(value) for value in head.classes_])
    model_version = model_card["model_version"]

    distinct_by_label: defaultdict[str, set[str]] = defaultdict(set)
    exact_truth: defaultdict[str, set[str]] = defaultdict(set)
    item_truth: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    client_authoritative_sources = {
        "client_product_rule", "direct_client_example", "client_service_rule",
        "client_product_family_resolution", "direct_client_family_resolution",
    }
    for row in gold_rows:
        text = build_model_text(row["item_text"], row["description"], row["provider"], row["direction"])
        key = normalize(text)
        distinct_by_label[row["category_code"]].add(key)
        if row["source"] in client_authoritative_sources:
            exact_truth[key].add(row["category_code"])
            item_truth[(row["direction"], normalize(row["item_text"]))].add(row["category_code"])
    weak_classes = {code for code, values in distinct_by_label.items() if len(values) < 15}
    weak_classes.update(set(distinct_by_label) - set(classes))

    xml_cache = {}
    missing_xml = []
    excluded_zero_junk = []
    prepared = []
    to_embed = []
    embed_indices = []
    for raw in raw_rows:
        path = xml_index.get(raw["source"], {}).get(raw["source_file"])
        if path is None:
            missing_xml.append(f'{raw["source"]}/{raw["source_file"]}')
            metadata, details = {}, {}
        else:
            cache_key = str(path)
            if cache_key not in xml_cache:
                xml_cache[cache_key] = parse_xml_context(path)
            metadata, details = xml_cache[cache_key]

        direction = raw["source"]
        item_text = raw["nmb_item"]
        description = raw["dsc_item"]
        provider = raw["rzn_soc_emisor"]
        detail = details.get(raw["nro_lin_det"], {})
        meter_code = metadata.get("meter_code", "")
        provider_rut = metadata.get("provider_rut", "")
        input_id = f"{direction}|{provider_rut}|{raw['folio']}|{raw['nro_lin_det']}"
        amount = detail.get("amount", "")
        unit_price = detail.get("unit_price", "")
        junk_reason = zero_value_junk_reason(
            item_text,
            description,
            amount=amount,
            unit_price=unit_price,
        )
        if junk_reason:
            excluded_zero_junk.append({
                "row_id": raw["row_id"],
                "source_file": raw["source_file"],
                "period": raw["period"],
                "folio": raw["folio"],
                "nro_lin_det": raw["nro_lin_det"],
                "direction": direction,
                "item_text": item_text,
                "description": description,
                "provider": provider,
                "amount": amount,
                "unit_price": unit_price,
                "audit_rationale": junk_reason,
            })
            continue
        meter = meters.match(meter_code) if meter_code and direction == "COMPRAS" else None
        rule = rules.match(item_text, direction) if not meter else None
        product = products.match(item_text, provider) if not meter and not rule and direction == "COMPRAS" else None
        model_text = build_model_text(item_text, description, provider, direction)
        row = {
            "row_id": raw["row_id"],
            "input_id": input_id,
            "source_file": raw["source_file"],
            "period": raw["period"],
            "folio": raw["folio"],
            "nro_lin_det": raw["nro_lin_det"],
            "direction": direction,
            "invoice_date": metadata.get("invoice_date", ""),
            "document_type": metadata.get("document_type", ""),
            "provider_rut": provider_rut,
            "provider_giro": metadata.get("provider_giro", ""),
            "item_text": item_text,
            "description": description,
            "provider": provider,
            "farm": raw["farm"],
            "meter_code": meter_code,
            "amount": amount,
            "unit_price": unit_price,
            "meter_hit": meter,
            "rule_hit": rule,
            "product_hit": product,
            "model_text": model_text,
        }
        prepared.append(row)
        if not meter and not rule and not product:
            embed_indices.append(len(prepared) - 1)
            to_embed.append(model_text)

    if missing_xml:
        raise RuntimeError(f"missing {len(missing_xml)} primary XML files; sample: {missing_xml[:5]}")

    embeddings = body.embed(to_embed, batch_size=args.batch_size)
    probabilities = np.asarray(head.predict_proba(embeddings))
    for position, row_index in enumerate(embed_indices):
        row = prepared[row_index]
        proba = probabilities[position].copy()
        masked = direction_mask(classes, row["direction"])
        if masked:
            proba[masked] = 0
            if proba.sum() > 0:
                proba /= proba.sum()
        order = np.argsort(-proba)
        row["model_prediction"] = str(classes[order[0]])
        row["model_top1"] = float(proba[order[0]])
        row["model_margin"] = float(proba[order[0]] - proba[order[1]]) if len(order) > 1 else 1.0
        row["model_entropy"] = entropy(proba)
        row["model_top3"] = [(str(classes[i]), float(proba[i])) for i in order[:3]]

    results = []
    for row in prepared:
        meter = row["meter_hit"]
        rule = row["rule_hit"]
        product = row["product_hit"]
        lookup_conflict = False
        if meter:
            source, prediction, top1, margin, top3 = "meter_lookup", meter.category_code, 1.0, 1.0, [(meter.category_code, 1.0)]
            result_entropy = 0.0
            decision, reason = "auto_accept", ""
        elif rule:
            source, prediction, top1, margin, top3 = "business_rule", rule.category_code, 1.0, 1.0, [(rule.category_code, 1.0)]
            result_entropy = 0.0
            decision, reason = "auto_accept", ""
        elif product:
            source, prediction, top1, margin, top3 = "product_lookup", product.category_code, 1.0, 1.0, [(product.category_code, 1.0)]
            result_entropy = 0.0
            decision, reason = "auto_accept", ""
        else:
            source = "model"
            prediction = row["model_prediction"]
            top1 = row["model_top1"]
            margin = row["model_margin"]
            top3 = row["model_top3"]
            result_entropy = row["model_entropy"]
            result = decide(
                source=source,
                code1=prediction,
                top1=top1,
                margin=margin,
                weak_classes=weak_classes,
                thresholds=thresholds,
            )
            decision, reason = result.decision, result.reason or ""
            ambiguity_reason = model_review_guard_reason(row["item_text"], row["description"]) if source == "model" else None
            if ambiguity_reason:
                decision, reason = "review_required", ambiguity_reason
            if row["direction"] == "VENTAS":
                decision, reason = "review_required", "unknown_sales_item"

        exact_labels = exact_truth.get(normalize(row["model_text"]), set())
        exact_label = next(iter(exact_labels)) if len(exact_labels) == 1 else ""
        risks = []
        if row["direction"] == "COMPRAS" and prediction.startswith("ING-"):
            risks.append("cross_direction_income_on_purchase")
        if row["direction"] == "VENTAS" and not prediction.startswith("ING-"):
            risks.append("cross_direction_expense_on_sale")
        if decision == "auto_accept" and exact_label and prediction != exact_label:
            if source == "meter_lookup":
                risks.append("meter_context_overrides_text_only_client_example")
            else:
                risks.append("contradicts_exact_client_example")
        item_labels = item_truth.get((row["direction"], normalize(row["item_text"])), set())
        if decision == "auto_accept" and source == "model" and item_labels and prediction not in item_labels:
            risks.append("model_item_name_seen_under_other_client_label")
        if decision == "auto_accept" and source == "model" and not exact_label:
            risks.append("novel_model_auto_accept")

        results.append({
            **{key: row[key] for key in [
                "row_id", "input_id", "source_file", "period", "folio", "nro_lin_det", "direction",
                "invoice_date", "document_type", "provider_rut", "provider_giro",
                "item_text", "description", "provider", "farm", "meter_code", "amount",
                "unit_price",
            ]},
            "source": source,
            "prediction": prediction,
            "top1": round(top1, 6),
            "margin": round(margin, 6),
            "entropy": round(result_entropy, 6),
            "decision": decision,
            "reason": reason,
            "top3": ";".join(f"{code}:{score:.4f}" for code, score in top3),
            "model_prediction": row.get("model_prediction", ""),
            "model_top1": round(row.get("model_top1", 0.0), 6) if row.get("model_prediction") else "",
            "lookup_conflict": lookup_conflict,
            "exact_known_truth": exact_label,
            "exact_known_consistent": "" if not exact_label else prediction == exact_label,
            "risk_flags": ";".join(risks),
        })

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "all_predictions.csv", results, FIELDS)
    write_csv(args.output_dir / "excluded_zero_junk.csv", excluded_zero_junk, [
        "row_id", "source_file", "period", "folio", "nro_lin_det", "direction",
        "item_text", "description", "provider", "amount", "unit_price", "audit_rationale",
    ])
    risk_rows = [row for row in results if row["decision"] == "auto_accept" and row["risk_flags"]]
    write_csv(args.output_dir / "auto_accept_risk_flags.csv", risk_rows, FIELDS)

    # Offline intermediate rows keyed by invoice business identifiers. These
    # are intentionally NOT called upload-ready: the production Supabase schema
    # uses five related tables whose UUIDs must be resolved at import time.
    supabase_rows = []
    for row in results:
        top3 = []
        for pair in row["top3"].split(";"):
            code, score = pair.rsplit(":", 1)
            top3.append({"code": code, "name": taxonomy.get(code, ""), "score": float(score)})
        supabase_rows.append({
            "input_id": row["input_id"],
            "transaction_type": row["direction"],
            "provider_rut": row["provider_rut"],
            "invoice_folio": row["folio"],
            "invoice_line_number": int(row["nro_lin_det"]),
            "invoice_date": row["invoice_date"],
            "document_type": row["document_type"],
            "item_text": row["item_text"],
            "description": row["description"] or None,
            "provider": row["provider"],
            "provider_giro": row["provider_giro"] or None,
            "meter_code": row["meter_code"] or None,
            "amount": float(row["amount"]) if row["amount"] else None,
            "model_version": model_version,
            "prediction_source": row["source"],
            "predicted_code": row["prediction"],
            "predicted_name": taxonomy.get(row["prediction"], ""),
            "top1_score": float(row["top1"]),
            "margin": float(row["margin"]),
            "entropy": float(row["entropy"]),
            "top3": top3,
            "decision": row["decision"],
            "reviewed": False,
            "final_code": row["prediction"] if row["decision"] == "auto_accept" else None,
        })
    write_jsonl(args.output_dir / "inference_rows_with_natural_keys.jsonl", supabase_rows)

    grouped = defaultdict(list)
    for row in results:
        if row["decision"] == "review_required":
            grouped[(row["reason"], row["prediction"], row["direction"], normalize(row["item_text"]))].append(row)
    review_groups = []
    for (reason, prediction, direction, item_key), group in grouped.items():
        review_groups.append({
            "rows": len(group),
            "reason": reason,
            "prediction": prediction,
            "prediction_name": taxonomy.get(prediction, ""),
            "direction": direction,
            "normalized_item": item_key,
            "example_item": group[0]["item_text"],
            "example_description": group[0]["description"],
            "example_provider": group[0]["provider"],
            "mean_top1": round(float(np.mean([float(row["top1"]) for row in group])), 4),
        })
    review_groups.sort(key=lambda row: (-row["rows"], row["reason"], row["prediction"], row["normalized_item"]))
    write_csv(args.output_dir / "review_groups.csv", review_groups, [
        "rows", "reason", "prediction", "prediction_name", "direction", "normalized_item",
        "example_item", "example_description", "example_provider", "mean_top1",
    ])

    accepted = [row for row in results if row["decision"] == "auto_accept"]
    review = [row for row in results if row["decision"] == "review_required"]
    sales = [row for row in results if row["direction"] == "VENTAS"]
    known_sales = [row for row in sales if row["source"] == "business_rule"]
    unknown_sales = [row for row in sales if row["source"] != "business_rule"]
    exact_known_accepted = [row for row in accepted if row["exact_known_truth"]]
    exact_known_false = [
        row for row in exact_known_accepted
        if row["source"] != "meter_lookup" and row["prediction"] != row["exact_known_truth"]
    ]
    meter_context_overrides = [
        row for row in exact_known_accepted
        if row["source"] == "meter_lookup" and row["prediction"] != row["exact_known_truth"]
    ]
    serious_flags = {
        "cross_direction_income_on_purchase",
        "cross_direction_expense_on_sale",
        "contradicts_exact_client_example",
    }
    serious_risks = [
        row for row in risk_rows
        if serious_flags.intersection(row["risk_flags"].split(";"))
    ]

    summary = {
        "local_only": True,
        "raw_rows": len(raw_rows),
        "rows_after_audited_zero_junk_filter": len(results),
        "excluded_zero_junk_rows": len(excluded_zero_junk),
        "xml_files_parsed": len(xml_cache),
        "amount_fields_recovered": sum(row["amount"] != "" for row in results),
        "meter_codes_recovered": sum(bool(row["meter_code"]) for row in results),
        "thresholds": thresholds,
        "weak_classes_lt15_distinct": sorted(weak_classes),
        "source_counts": dict(sorted(Counter(row["source"] for row in results).items())),
        "decision_counts": dict(sorted(Counter(row["decision"] for row in results).items())),
        "auto_accept_rate": round(len(accepted) / len(results), 4),
        "reason_counts": dict(sorted(Counter(row["reason"] or "accepted" for row in results).items())),
        "sales": {
            "rows": len(sales),
            "known_exact_auto_accept": len(known_sales),
            "unknown_review_required": len(unknown_sales),
            "unknown_items": dict(sorted(Counter(row["item_text"] for row in unknown_sales).items())),
        },
        "direction_safety": {
            "purchase_predicted_income": sum(row["direction"] == "COMPRAS" and row["prediction"].startswith("ING-") for row in results),
            "sale_predicted_expense": sum(row["direction"] == "VENTAS" and not row["prediction"].startswith("ING-") for row in results),
        },
        "exact_known_auto_accept_audit": {
            "rows": len(exact_known_accepted),
            "false_positives": len(exact_known_false),
            "meter_context_overrides_text_only_examples": len(meter_context_overrides),
            "precision_excluding_authoritative_meter_context": round(
                (len(exact_known_accepted) - len(meter_context_overrides) - len(exact_known_false))
                / (len(exact_known_accepted) - len(meter_context_overrides)), 4
            ) if len(exact_known_accepted) > len(meter_context_overrides) else None,
        },
        "auto_accept_risk_flags": {
            "all_flagged_including_novel_model": len(risk_rows),
            "serious_rule_or_known_label_conflicts": len(serious_risks),
            "flag_counts": dict(sorted(Counter(flag for row in risk_rows for flag in row["risk_flags"].split(";") if flag).items())),
        },
        "review_by_reason": dict(sorted(Counter(row["reason"] for row in review).items())),
        "review_by_predicted_category": dict(Counter(row["prediction"] for row in review).most_common()),
        "auto_accept_by_category": dict(Counter(row["prediction"] for row in accepted).most_common()),
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
