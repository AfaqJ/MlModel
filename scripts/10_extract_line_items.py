"""Extract invoice line items from SII DTE XML files into a flat CSV.

Reads all XML files under data/raw/COMPRAS and data/raw/VENTAS (or the legacy
dte_96685810_COMPRAS / dte_96685810_VENTAS folders at root), extracts each
Detalle (line item) block, and writes data/processed/line_items.csv.

This CSV is the starting point for the silver labeling pipeline.

Usage:
  python3 scripts/10_extract_line_items.py

Output columns:
  row_id, source, period, source_file, folio, nro_lin_det,
  nmb_item, dsc_item, mnt_item, rzn_soc_emisor, giro_emisor, farm
"""

from __future__ import annotations

import csv
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[1]
OUT_CSV     = ROOT / "data" / "processed" / "line_items.csv"

# Accept both old root-level folders and new data/raw/ structure.
COMPRAS_DIRS = [
    ROOT / "data" / "raw" / "COMPRAS",
    ROOT / "data" / "Raw_Data" / "dte_96685810_COMPRAS",
    ROOT / "Data" / "Raw_Data" / "dte_96685810_COMPRAS",
    ROOT / "dte_96685810_COMPRAS",
]
VENTAS_DIRS = [
    ROOT / "data" / "raw" / "VENTAS",
    ROOT / "data" / "Raw_Data" / "dte_96685810_VENTAS",
    ROOT / "Data" / "Raw_Data" / "dte_96685810_VENTAS",
    ROOT / "dte_96685810_VENTAS",
]

OUTPUT_FIELDS = [
    "row_id", "source", "period", "source_file", "folio", "nro_lin_det",
    "nmb_item", "dsc_item", "mnt_item", "rzn_soc_emisor", "giro_emisor", "farm",
]


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


def text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return re.sub(r"\s+", " ", (element.text or "")).strip()


def parse_xml(path: Path, source: str) -> list[dict]:
    raw = path.read_bytes()
    try:
        xml_text = raw.decode("utf-8")
    except UnicodeDecodeError:
        xml_text = raw.decode("latin-1")

    try:
        root = ET.fromstring(xml_text.encode("utf-8"))
    except ET.ParseError:
        print(f"  [SKIP] parse error: {path.name}")
        return []

    rows = []

    # SII DTEs can be namespaced, un-namespaced, or wrapped in an envelope.
    for dte in iter_named(root, "DTE"):
        doc = find_deep_named(dte, "Documento")
        if doc is None:
            continue

        encab = find_named(doc, "Encabezado")
        if encab is None:
            continue

        id_doc   = find_named(encab, "IdDoc")
        emisor   = find_named(encab, "Emisor")
        folio    = text(find_named(id_doc, "Folio"))     if id_doc is not None  else ""
        rzn_soc  = text(find_named(emisor, "RznSoc"))    if emisor is not None  else ""
        giro     = text(find_named(emisor, "GiroEmis"))  if emisor is not None  else ""

        # Extract period from FchEmis (YYYY-MM-DD).
        fch_emis = text(find_named(id_doc, "FchEmis")) if id_doc is not None else ""
        period   = fch_emis[:7] if fch_emis else ""

        for detalle in iter_named(doc, "Detalle"):
            nmb  = text(find_named(detalle, "NmbItem"))
            dsc  = text(find_named(detalle, "DscItem"))
            mnt  = text(find_named(detalle, "MntItem"))
            nro  = text(find_named(detalle, "NroLinDet"))

            if not nmb and not dsc:
                continue

            rows.append({
                "row_id":        "",          # filled later
                "source":        source,
                "period":        period,
                "source_file":   path.name,
                "folio":         folio,
                "nro_lin_det":   nro,
                "nmb_item":      nmb,
                "dsc_item":      dsc,
                "mnt_item":      mnt,
                "rzn_soc_emisor": rzn_soc,
                "giro_emisor":   giro,
                "farm":          "",          # not determinable from XML alone
            })

    return rows


def collect_xmls(dirs: list[Path], source_label: str) -> list[dict]:
    rows = []
    seen_dirs: set[tuple[int, int]] = set()
    seen_files: set[tuple[int, int]] = set()
    for d in dirs:
        if not d.exists():
            continue
        dir_stat = os.stat(d)
        dir_key = (dir_stat.st_dev, dir_stat.st_ino)
        if dir_key in seen_dirs:
            continue
        seen_dirs.add(dir_key)
        print(f"  Scanning {d} ...")
        xml_files = sorted(d.rglob("*.xml"))
        print(f"    Found {len(xml_files):,} XML files.")
        for path in xml_files:
            file_stat = os.stat(path)
            file_key = (file_stat.st_dev, file_stat.st_ino)
            if file_key in seen_files:
                continue
            seen_files.add(file_key)
            rows.extend(parse_xml(path, source_label))
    return rows


def main() -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    print("Extracting COMPRAS ...")
    compras = collect_xmls(COMPRAS_DIRS, "COMPRAS")
    print(f"  {len(compras):,} line items from COMPRAS.")

    print("Extracting VENTAS ...")
    ventas = collect_xmls(VENTAS_DIRS, "VENTAS")
    print(f"  {len(ventas):,} line items from VENTAS.")

    all_rows = compras + ventas

    # Assign stable row_ids.
    for i, row in enumerate(all_rows):
        row["row_id"] = i + 1

    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nWrote {len(all_rows):,} rows → {OUT_CSV}")
    print("Next: run scripts/21_ollama_silver_label.py")


if __name__ == "__main__":
    main()
