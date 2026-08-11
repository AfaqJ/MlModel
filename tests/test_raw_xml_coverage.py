from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_migration_module():
    path = ROOT / "Temp_Inference/migrate_to_company_item_schema.py"
    spec = importlib.util.spec_from_file_location("coverage_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_all_standard_and_liquidacion_xml_documents_are_parsed():
    module = load_migration_module()
    invoices, lines, stats, errors = module.parse_raw_xml()
    assert errors == []
    assert len(invoices) == 5195
    assert len(lines) == 12206
    assert stats["standard_document_invoices"] == 5166
    assert stats["liquidacion_invoices"] == 29
    assert sum(invoice.xml_document_kind == "Liquidacion" for invoice in invoices.values()) == 29
    liquidation_keys = {
        key for key, invoice in invoices.items() if invoice.xml_document_kind == "Liquidacion"
    }
    assert sum(line.invoice_key in liquidation_keys for line in lines.values()) == 103
