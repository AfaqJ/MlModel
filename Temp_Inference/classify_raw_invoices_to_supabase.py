#!/usr/bin/env python3
"""Legacy raw-DTE parser retained for historical reproducibility.

Remote writes are deliberately disabled because this code targets the dropped
flat ``line_item_predictions`` table. It may only be used with ``--dry-run``.
The v1.3.1 release builds a reviewed five-table import bundle instead.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.inference.line_filters import zero_value_junk_reason

RAW_DIRS = {
    "COMPRAS": ROOT / "Data" / "Raw_Data" / "dte_96685810_COMPRAS",
    "VENTAS": ROOT / "Data" / "Raw_Data" / "dte_96685810_VENTAS",
}

DEFAULT_PREDICT_API_URL = "http://127.0.0.1:8000"
DEFAULT_TABLE = "line_item_predictions"
DEFAULT_BATCH_SIZE = 500
DEFAULT_AUTO_ACCEPT_TOP1 = 0.75
DEFAULT_AUTO_ACCEPT_MARGIN = 0.50

API_ITEM_MAX = 512
API_DESCRIPTION_MAX = 512
API_PROVIDER_MAX = 256
API_INPUT_ID_MAX = 128

@dataclass(frozen=True)
class InvoiceLine:
    input_id: str
    transaction_type: str
    provider_rut: str
    invoice_folio: str
    invoice_line_number: int
    invoice_date: str
    document_type: str
    item_text: str
    description: str | None
    provider: str
    provider_giro: str | None
    meter_code: str | None
    amount: int | float | None
    unit_price: int | float | None
    source_file: str


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def env_value(key: str, file_values: dict[str, str], default: str | None = None) -> str | None:
    return os.environ.get(key) or file_values.get(key) or default


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def iter_named(element: ET.Element, name: str):
    for child in element.iter():
        if local_name(child.tag) == name:
            yield child


def find_named(element: ET.Element | None, name: str) -> ET.Element | None:
    if element is None:
        return None
    for child in list(element):
        if local_name(child.tag) == name:
            return child
    return None


def find_deep_named(element: ET.Element | None, name: str) -> ET.Element | None:
    if element is None:
        return None
    for child in element.iter():
        if local_name(child.tag) == name:
            return child
    return None


def clean_text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return re.sub(r"\s+", " ", (element.text or "")).strip()


def none_if_blank(value: str) -> str | None:
    value = value.strip()
    return value or None


def normalize_rut(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())


def parse_number(value: str) -> int | float | None:
    value = value.strip().replace(",", ".")
    if not value:
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    if number.is_integer():
        return int(number)
    return number


def api_truncate(value: str | None, max_len: int) -> str:
    value = (value or "").strip()
    if len(value) <= max_len:
        return value
    return value[:max_len]


def is_junk_line(
    item_text: str,
    description: str,
    *,
    amount: int | float | None = None,
    unit_price: int | float | None = None,
) -> bool:
    combined = " ".join(part for part in [item_text.strip(), description.strip()] if part)
    if not combined:
        return True
    return zero_value_junk_reason(
        item_text,
        description,
        amount=amount,
        unit_price=unit_price,
    ) is not None


def parse_xml(path: Path, transaction_type: str) -> tuple[list[InvoiceLine], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    raw = path.read_bytes()
    try:
        xml_text = raw.decode("utf-8")
    except UnicodeDecodeError:
        xml_text = raw.decode("latin-1", errors="replace")

    try:
        root = ET.fromstring(xml_text.encode("utf-8"))
    except ET.ParseError as exc:
        return [], [{"source_file": str(path), "error": f"parse_error: {exc}"}]

    rows: list[InvoiceLine] = []
    for dte in iter_named(root, "DTE"):
        doc = find_deep_named(dte, "Documento")
        if doc is None:
            continue

        encab = find_named(doc, "Encabezado")
        id_doc = find_named(encab, "IdDoc")
        emisor = find_named(encab, "Emisor")
        receptor = find_named(encab, "Receptor")

        document_type = clean_text(find_named(id_doc, "TipoDTE"))
        invoice_folio = clean_text(find_named(id_doc, "Folio"))
        invoice_date = clean_text(find_named(id_doc, "FchEmis"))
        provider_rut = normalize_rut(clean_text(find_named(emisor, "RUTEmisor")))
        provider = clean_text(find_named(emisor, "RznSoc"))
        provider_giro = none_if_blank(clean_text(find_named(emisor, "GiroEmis")))
        meter_code = none_if_blank(clean_text(find_named(receptor, "CdgIntRecep")))

        for detalle in iter_named(doc, "Detalle"):
            item_text = clean_text(find_named(detalle, "NmbItem"))
            description = clean_text(find_named(detalle, "DscItem"))
            line_number_text = clean_text(find_named(detalle, "NroLinDet"))
            unit_price = parse_number(clean_text(find_named(detalle, "PrcItem")))
            amount = parse_number(clean_text(find_named(detalle, "MontoItem")))

            if is_junk_line(
                item_text,
                description,
                amount=amount,
                unit_price=unit_price,
            ):
                continue

            try:
                invoice_line_number = int(line_number_text)
            except ValueError:
                errors.append(
                    {
                        "source_file": str(path),
                        "folio": invoice_folio,
                        "line_number": line_number_text,
                        "error": "invalid_or_missing_line_number",
                    }
                )
                continue

            input_id = f"{transaction_type}|{provider_rut}|{invoice_folio}|{invoice_line_number}"
            required = {
                "document_type": document_type,
                "invoice_folio": invoice_folio,
                "invoice_date": invoice_date,
                "provider_rut": provider_rut,
                "provider": provider,
                "item_text": item_text,
            }
            missing = [name for name, value in required.items() if not value]
            if missing:
                errors.append(
                    {
                        "source_file": str(path),
                        "input_id": input_id,
                        "error": f"missing_required_fields: {','.join(missing)}",
                    }
                )
                continue
            if len(input_id) > API_INPUT_ID_MAX:
                errors.append(
                    {
                        "source_file": str(path),
                        "input_id": input_id,
                        "error": f"input_id_exceeds_api_limit_{API_INPUT_ID_MAX}",
                    }
                )
                continue

            rows.append(
                InvoiceLine(
                    input_id=input_id,
                    transaction_type=transaction_type,
                    provider_rut=provider_rut,
                    invoice_folio=invoice_folio,
                    invoice_line_number=invoice_line_number,
                    invoice_date=invoice_date,
                    document_type=document_type,
                    item_text=item_text,
                    description=none_if_blank(description),
                    provider=provider,
                    provider_giro=provider_giro,
                    meter_code=meter_code,
                    amount=amount,
                    unit_price=unit_price,
                    source_file=str(path.relative_to(ROOT)),
                )
            )

    return rows, errors


def iter_invoice_lines(sources: list[str]) -> tuple[list[InvoiceLine], list[dict[str, Any]]]:
    rows: list[InvoiceLine] = []
    errors: list[dict[str, Any]] = []
    for source in sources:
        root = RAW_DIRS[source]
        if not root.exists():
            errors.append({"source": source, "path": str(root), "error": "raw_dir_missing"})
            continue
        for path in sorted(root.rglob("*.xml")):
            parsed, parse_errors = parse_xml(path, source)
            rows.extend(parsed)
            errors.extend(parse_errors)
    return rows, errors


def to_predict_request(row: InvoiceLine) -> dict[str, Any]:
    payload = {
        "input_id": row.input_id,
        "item_text": api_truncate(row.item_text, API_ITEM_MAX),
        "description": api_truncate(row.description, API_DESCRIPTION_MAX),
        "provider": api_truncate(row.provider, API_PROVIDER_MAX),
        "transaction_type": row.transaction_type,
        "invoice_metadata": {"document_type": row.document_type},
        "top_k": 3,
    }
    if row.meter_code:
        payload["meter_code"] = api_truncate(row.meter_code, 64)
    return payload


def request_with_retries(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    retries: int,
    **kwargs: Any,
) -> httpx.Response:
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = client.request(method, url, **kwargs)
            if response.status_code < 500:
                response.raise_for_status()
                return response
            response.raise_for_status()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_exc = exc
            if attempt >= retries:
                break
            time.sleep(min(2**attempt, 8))
    assert last_exc is not None
    raise last_exc


def check_predict_api(client: httpx.Client, predict_api_url: str, retries: int) -> None:
    health = request_with_retries(client, "GET", f"{predict_api_url}/health", retries=retries)
    status = health.json().get("status")
    if status != "ok":
        raise RuntimeError(f"Unexpected /health response: {health.text}")

    artifact = request_with_retries(client, "GET", f"{predict_api_url}/artifact-check", retries=retries)
    files = artifact.json().get("files", {})
    bad = [
        name
        for name, info in files.items()
        if not info.get("exists") or info.get("looks_like_lfs_pointer")
    ]
    if bad:
        raise RuntimeError(f"Artifact check failed for: {', '.join(bad)}")


def predict_batch(
    client: httpx.Client,
    predict_api_url: str,
    rows: list[InvoiceLine],
    *,
    retries: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    payload = {"items": [to_predict_request(row) for row in rows], "top_k": 3}
    response = request_with_retries(
        client,
        "POST",
        f"{predict_api_url}/predict-batch",
        retries=retries,
        json=payload,
    )
    body = response.json()
    predictions: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    row_by_id = {row.input_id: row for row in rows}
    for result in body.get("results", []):
        if "error" in result:
            errors.append(
                {
                    "input_id": result.get("input_id"),
                    "source_file": getattr(row_by_id.get(result.get("input_id")), "source_file", None),
                    "error": result.get("error"),
                }
            )
        else:
            predictions.append(result)
    return predictions, errors


def final_decision(
    result: dict[str, Any],
    *,
    auto_accept_top1: float,
    auto_accept_margin: float,
) -> str:
    source = result["source"]
    if source in {"meter_lookup", "product_lookup", "business_rule"}:
        return "auto_accept"
    if result["decision"] == "review_required":
        return "review_required"
    confidence = result.get("confidence", {})
    top1 = float(confidence.get("top1", 0.0))
    margin = float(confidence.get("margin", 0.0))
    if top1 >= auto_accept_top1 and margin >= auto_accept_margin:
        return "auto_accept"
    return "review_required"


def to_supabase_row(
    row: InvoiceLine,
    result: dict[str, Any],
    *,
    auto_accept_top1: float,
    auto_accept_margin: float,
) -> dict[str, Any]:
    predictions = result.get("predictions") or []
    if not predictions:
        raise ValueError(f"No predictions for {row.input_id}")
    top_prediction = predictions[0]
    confidence = result.get("confidence") or {}
    decision = final_decision(
        result,
        auto_accept_top1=auto_accept_top1,
        auto_accept_margin=auto_accept_margin,
    )
    return {
        "input_id": row.input_id,
        "transaction_type": row.transaction_type,
        "provider_rut": row.provider_rut,
        "invoice_folio": row.invoice_folio,
        "invoice_line_number": row.invoice_line_number,
        "invoice_date": row.invoice_date,
        "document_type": row.document_type,
        "item_text": row.item_text,
        "description": row.description,
        "provider": row.provider,
        "provider_giro": row.provider_giro,
        "meter_code": row.meter_code,
        "amount": row.amount,
        "model_version": result["model_version"],
        "prediction_source": result["source"],
        "predicted_code": top_prediction["code"],
        "predicted_name": top_prediction.get("name") or None,
        "top1_score": float(confidence.get("top1", top_prediction.get("score", 0.0))),
        "margin": float(confidence.get("margin", 0.0)),
        "entropy": float(confidence.get("entropy", 0.0)),
        "top3": predictions,
        "decision": decision,
        "reviewed": False,
        "final_code": top_prediction["code"] if decision == "auto_accept" else None,
    }


def upsert_supabase(
    client: httpx.Client,
    supabase_url: str,
    secret_key: str,
    table: str,
    rows: list[dict[str, Any]],
    *,
    retries: int,
) -> None:
    if not rows:
        return
    url = f"{supabase_url.rstrip('/')}/rest/v1/{table}?on_conflict=input_id"
    headers = {
        "apikey": secret_key,
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    request_with_retries(client, "POST", url, retries=retries, headers=headers, json=rows)


def chunks(items: list[Any], size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_threshold_report(output_dir: Path, supabase_rows: list[dict[str, Any]]) -> None:
    top1_thresholds = [0.70, 0.75, 0.80, 0.85, 0.90]
    margin_thresholds = [0.10, 0.15, 0.20, 0.30]
    report_path = output_dir / "threshold_report.csv"
    with report_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "top1_threshold",
                "margin_threshold",
                "auto_accept_count",
                "review_required_count",
                "auto_accept_percent",
                "review_required_percent",
            ],
        )
        writer.writeheader()
        total = len(supabase_rows) or 1
        for top1 in top1_thresholds:
            for margin in margin_thresholds:
                auto_accept = 0
                for row in supabase_rows:
                    if row["prediction_source"] in {"meter_lookup", "product_lookup", "business_rule"}:
                        auto_accept += 1
                    elif (
                        row.get("backend_decision") == "auto_accept"
                        and row["top1_score"] >= top1
                        and row["margin"] >= margin
                    ):
                        auto_accept += 1
                review = len(supabase_rows) - auto_accept
                writer.writerow(
                    {
                        "top1_threshold": top1,
                        "margin_threshold": margin,
                        "auto_accept_count": auto_accept,
                        "review_required_count": review,
                        "auto_accept_percent": round(auto_accept / total * 100, 2),
                        "review_required_percent": round(review / total * 100, 2),
                    }
                )

    samples = sorted(
        [
            row
            for row in supabase_rows
            if row["prediction_source"] == "model" and row["decision"] == "review_required"
        ],
        key=lambda row: (row["margin"], -row["top1_score"]),
    )[:100]
    sample_path = output_dir / "review_samples.csv"
    with sample_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "input_id",
                "transaction_type",
                "invoice_date",
                "item_text",
                "provider",
                "predicted_code",
                "predicted_name",
                "top1_score",
                "margin",
                "top3",
            ],
        )
        writer.writeheader()
        for row in samples:
            writer.writerow(
                {
                    "input_id": row["input_id"],
                    "transaction_type": row["transaction_type"],
                    "invoice_date": row["invoice_date"],
                    "item_text": row["item_text"],
                    "provider": row["provider"],
                    "predicted_code": row["predicted_code"],
                    "predicted_name": row["predicted_name"],
                    "top1_score": row["top1_score"],
                    "margin": row["margin"],
                    "top3": json.dumps(row["top3"], ensure_ascii=False),
                }
            )


def reset_run_outputs(output_dir: Path, *, threshold_report: bool) -> None:
    paths = [output_dir / "loader_errors.jsonl"]
    if threshold_report:
        paths.extend(
            [
                output_dir / "threshold_report.csv",
                output_dir / "review_samples.csv",
                output_dir / "smoke_predictions.jsonl",
            ]
        )
    for path in paths:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", choices=sorted(RAW_DIRS), help="Restrict to one source. Repeat to include both.")
    parser.add_argument("--input-id", action="append", help="Process only this exact input_id. Repeat for multiple rows.")
    parser.add_argument("--limit", type=int, help="Limit parsed line items before inference.")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="Line items per /predict-batch call. Max 500.")
    parser.add_argument("--dry-run", action="store_true", help="Legacy local parser only; remote writes are disabled.")
    parser.add_argument("--threshold-report", action="store_true", help="Write threshold_report.csv and review_samples.csv.")
    parser.add_argument("--auto-accept-top1", type=float, default=DEFAULT_AUTO_ACCEPT_TOP1)
    parser.add_argument("--auto-accept-margin", type=float, default=DEFAULT_AUTO_ACCEPT_MARGIN)
    parser.add_argument("--predict-api-url", default=None)
    parser.add_argument("--env-file", type=Path, default=HERE / ".env.loader")
    parser.add_argument("--table", default=DEFAULT_TABLE)
    parser.add_argument("--output-dir", type=Path, default=HERE)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=120.0)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if not args.dry_run:
        print(
            "ERROR: legacy remote writer is disabled because it targets the dropped "
            "line_item_predictions table. Use --dry-run only; build the reviewed "
            "five-table import bundle before any future upload.",
            file=sys.stderr,
        )
        return 2
    if args.batch_size < 1 or args.batch_size > DEFAULT_BATCH_SIZE:
        print(f"ERROR: --batch-size must be between 1 and {DEFAULT_BATCH_SIZE}", file=sys.stderr)
        return 2
    if args.limit is not None and args.limit < 1:
        print("ERROR: --limit must be positive", file=sys.stderr)
        return 2

    env_values = load_env_file(args.env_file)
    predict_api_url = (args.predict_api_url or env_value("PREDICT_API_URL", env_values, DEFAULT_PREDICT_API_URL)).rstrip("/")
    supabase_url = env_value("SUPABASE_URL", env_values)
    supabase_key = env_value("SUPABASE_SECRET_KEY", env_values) or env_value("SUPABASE_SERVICE_ROLE_KEY", env_values)

    if not args.dry_run:
        missing = [name for name, value in [("SUPABASE_URL", supabase_url), ("SUPABASE_SECRET_KEY", supabase_key)] if not value]
        if missing:
            print(f"ERROR: missing required Supabase env values: {', '.join(missing)}", file=sys.stderr)
            return 2

    sources = args.source or ["COMPRAS", "VENTAS"]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    reset_run_outputs(args.output_dir, threshold_report=args.threshold_report)

    rows, parse_errors = iter_invoice_lines(sources)
    if args.input_id:
        wanted_input_ids = set(args.input_id)
        rows = [row for row in rows if row.input_id in wanted_input_ids]
        found_input_ids = {row.input_id for row in rows}
        missing_input_ids = sorted(wanted_input_ids - found_input_ids)
        if missing_input_ids:
            print(f"ERROR: input_id not found in parsed raw XMLs: {', '.join(missing_input_ids)}", file=sys.stderr)
            return 2
    if args.limit:
        rows = rows[: args.limit]

    error_path = args.output_dir / "loader_errors.jsonl"
    if parse_errors:
        write_jsonl(error_path, parse_errors)

    print(f"Parsed {len(rows):,} line items from {', '.join(sources)}.")
    if parse_errors:
        print(f"Captured {len(parse_errors):,} parse/skipped-row errors in {error_path}.")
    if not rows:
        return 0

    all_supabase_rows: list[dict[str, Any]] = []
    counters = {
        "predicted": 0,
        "auto_accept": 0,
        "review_required": 0,
        "row_errors": 0,
        "upserted": 0,
    }
    all_report_rows: list[dict[str, Any]] = []

    with httpx.Client(timeout=args.timeout) as client:
        check_predict_api(client, predict_api_url, args.retries)
        for index, batch_rows in enumerate(chunks(rows, args.batch_size), start=1):
            predictions, row_errors = predict_batch(client, predict_api_url, batch_rows, retries=args.retries)
            counters["row_errors"] += len(row_errors)
            write_jsonl(error_path, row_errors)

            row_by_id = {row.input_id: row for row in batch_rows}
            supabase_rows: list[dict[str, Any]] = []
            transform_errors: list[dict[str, Any]] = []
            for result in predictions:
                input_id = result.get("input_id")
                source_row = row_by_id.get(input_id)
                if source_row is None:
                    transform_errors.append({"input_id": input_id, "error": "prediction_without_source_row"})
                    continue
                try:
                    out_row = to_supabase_row(
                        source_row,
                        result,
                        auto_accept_top1=args.auto_accept_top1,
                        auto_accept_margin=args.auto_accept_margin,
                    )
                except Exception as exc:
                    transform_errors.append({"input_id": input_id, "error": f"transform_failed: {exc}"})
                    continue
                supabase_rows.append(out_row)
                report_row = dict(out_row)
                report_row["backend_decision"] = result.get("decision")
                report_row["backend_reason"] = result.get("reason")
                all_report_rows.append(report_row)
                counters["predicted"] += 1
                counters[out_row["decision"]] += 1

            if transform_errors:
                counters["row_errors"] += len(transform_errors)
                write_jsonl(error_path, transform_errors)

            all_supabase_rows.extend(supabase_rows)
            if not args.dry_run:
                assert supabase_url is not None and supabase_key is not None
                upsert_supabase(
                    client,
                    supabase_url,
                    supabase_key,
                    args.table,
                    supabase_rows,
                    retries=args.retries,
                )
                counters["upserted"] += len(supabase_rows)

            action = "dry-run" if args.dry_run else "upserted"
            print(
                f"Batch {index}: predicted={len(supabase_rows):,}, "
                f"errors={len(row_errors) + len(transform_errors):,}, {action}={0 if args.dry_run else len(supabase_rows):,}"
            )

    if args.threshold_report:
        write_threshold_report(args.output_dir, all_report_rows)
        smoke_path = args.output_dir / "smoke_predictions.jsonl"
        write_jsonl(smoke_path, all_report_rows)
        print(f"Wrote threshold report to {args.output_dir / 'threshold_report.csv'}.")
        print(f"Wrote review samples to {args.output_dir / 'review_samples.csv'}.")
        print(f"Wrote smoke predictions to {smoke_path}.")

    print(
        "Summary: "
        f"predicted={counters['predicted']:,}, "
        f"auto_accept={counters['auto_accept']:,}, "
        f"review_required={counters['review_required']:,}, "
        f"row_errors={counters['row_errors']:,}, "
        f"upserted={counters['upserted']:,}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
