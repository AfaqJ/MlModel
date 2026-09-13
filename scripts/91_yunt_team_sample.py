"""Prepare a real, reversible handover sample. No model calls.

prepare: fresh full row snapshot + five original XML invoices and answer key.
detach --apply: recheck snapshot, remove ONLY those invoices and their lines.
restore --apply: restore original rows while sample remains absent; refuse if
the team has already reimported it (their dependent review records need review).
Never run the older blanket Yunt cleanup after team testing starts.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

from supabase_rest import Rest, load_env, quote_in

ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / "backups/yunt_team_handover_20260913"
OUTPUT = ROOT / "handover/yunt-team-test"
spec = importlib.util.spec_from_file_location("undo", ROOT / "scripts/90_yunt_live_test_undo.py")
undo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(undo)


def digest(rows):
    return hashlib.sha256(json.dumps(sorted(rows, key=lambda r: json.dumps(r, sort_keys=True)),
                                     sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def read_all(db):
    with ThreadPoolExecutor(max_workers=5) as pool:
        return dict(zip(undo.WATCHED, pool.map(lambda t: db.get(t, "*"), undo.WATCHED)))


def key(row):
    return (row["seller_rut"], str(row["document_type"]), str(row["invoice_folio"]))


def sources():
    found = {}
    for path in sorted((ROOT / "Data/Raw_Data/dte_96685810_COMPRAS").rglob("*.xml")):
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            continue
        for node in root.iter():
            node.tag = node.tag.split("}")[-1]
        docs = list(root.iter("Documento"))
        if len(docs) != 1:
            continue
        doc = docs[0]
        rut = (doc.findtext("./Encabezado/Emisor/RUTEmisor") or "").replace("-", "").replace(".", "").upper()
        kind = doc.findtext("./Encabezado/IdDoc/TipoDTE")
        folio = doc.findtext("./Encabezado/IdDoc/Folio")
        found[(rut, kind, folio)] = (path, doc.findall("Detalle"))
    return found


def prepare(db):
    if BACKUP.exists():
        raise SystemExit("Snapshot already exists; refusing to overwrite it.")
    tables = read_all(db)
    baseline = json.loads(undo.SNAPSHOT.read_text())
    for table, rows in tables.items():
        assert len(rows) == baseline[table], f"Not baseline: {table}"
    by_invoice = defaultdict(list)
    for row in tables["invoice_items"]:
        by_invoice[row["invoice_id"]].append(row)
    xml = sources()
    selected, selected_lines, picked_categories = [], [], set()
    counts = Counter(r["catalog_item_id"] for r in tables["invoice_items"])
    for invoice in sorted(tables["invoices"], key=lambda r: (r["invoice_date"], r["invoice_id"])):
        lines = sorted(by_invoice[invoice["invoice_id"]], key=lambda r: r["invoice_line_number"])
        if invoice["transaction_type"] != "COMPRAS" or len(lines) not in (2, 3) or key(invoice) not in xml:
            continue
        _, details = xml[key(invoice)]
        if len(details) != len(lines) or any(not r["final_code"] for r in lines):
            continue
        # Leave precedent rows for every selected catalog item.
        local = Counter(r["catalog_item_id"] for r in selected_lines + lines)
        if any(counts[c] <= n for c, n in local.items()):
            continue
        codes = {r["final_code"] for r in lines}
        if not codes - picked_categories:
            continue
        # Verify each source XML line against its stored amount and line number.
        xml_amounts = {int(d.findtext("NroLinDet")): float(d.findtext("MontoItem")) for d in details}
        if any(xml_amounts.get(r["invoice_line_number"]) != float(r["amount"]) for r in lines):
            continue
        selected.append(invoice)
        selected_lines.extend(lines)
        picked_categories.update(codes)
        if len(selected) == 5:
            break
    assert len(selected) == 5, "Could not find five safe complete invoices"
    BACKUP.mkdir(parents=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for table, rows in tables.items():
        (BACKUP / f"{table}.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    manifest = {"invoices": selected, "invoice_items": selected_lines,
                "baseline": {t: {"count": len(r), "sha256": digest(r)} for t, r in tables.items()}, "files": []}
    with zipfile.ZipFile(OUTPUT / "yunt-unseen-invoices.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for invoice in selected:
            path, _ = xml[key(invoice)]
            filename = "COMPRAS/" + "_".join(key(invoice)) + ".xml"
            archive.write(path, filename)
            manifest["files"].append({"filename": filename, "source": str(path.relative_to(ROOT)),
                                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    (BACKUP / "sample.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    answer = ["# Reference classifications before the test", "",
              "These are saved database labels, not a promise of identical new predictions. Compare final classifications with this reference. Original Spanish item names are identifiers.", "",
              "| Supplier / folio | Line | Original item | Saved category | Amount CLP |",
              "|---|---:|---|---|---:|"]
    for invoice in selected:
        for r in selected_lines:
            if r["invoice_id"] == invoice["invoice_id"]:
                answer.append(f"| {invoice['seller_name']} / {invoice['invoice_folio']} | {r['invoice_line_number']} | {r['item_text'].replace('|', '/')} | {r['final_code']} | {r['amount']} |")
    (OUTPUT / "REFERENCE.md").write_text("\n".join(answer) + "\n", encoding="utf-8")
    print(f"Prepared {len(selected)} original invoices, {len(selected_lines)} lines. Database unchanged.")
    print("Snapshot:", BACKUP)
    print("ZIP:", OUTPUT / "yunt-unseen-invoices.zip")
    print("Reference categories:", sorted(picked_categories))


def change(db, mode, apply):
    manifest = json.loads((BACKUP / "sample.json").read_text())
    original = {t: json.loads((BACKUP / f"{t}.json").read_text()) for t in undo.WATCHED}
    ids = {r["invoice_id"] for r in manifest["invoices"]}
    item_ids = {r["item_id"] for r in manifest["invoice_items"]}
    detached = {**original,
                "invoices": [r for r in original["invoices"] if r["invoice_id"] not in ids],
                "invoice_items": [r for r in original["invoice_items"] if r["item_id"] not in item_ids]}
    expected_before, expected_after = (original, detached) if mode == "detach" else (detached, original)
    for table, rows in read_all(db).items():
        assert digest(rows) == digest(expected_before[table]), f"{table} changed: refusing writes; inspect first"
    with zipfile.ZipFile(OUTPUT / "yunt-unseen-invoices.zip") as archive:
        for entry in manifest["files"]:
            assert hashlib.sha256(archive.read(entry["filename"])).hexdigest() == entry["sha256"]
    print(f"{mode}: {len(ids)} exact invoices and {len(item_ids)} exact lines; full baseline hashes verified.")
    if not apply:
        print("DRY RUN. No writes. Add --apply to execute.")
        return
    def restore():
        db.upsert("invoices", [{k: v for k, v in r.items() if k != "invoice_period"} for r in manifest["invoices"]], "invoice_id", allow_writes=True)
        db.upsert("invoice_items", [{k: v for k, v in r.items() if k != "needs_review"} for r in manifest["invoice_items"]], "item_id", allow_writes=True)
    if mode == "detach":
        try:
            db.delete("invoice_items", f"item_id=in.{quote_in(sorted(item_ids))}", allow_writes=True)
            db.delete("invoices", f"invoice_id=in.{quote_in(sorted(ids))}", allow_writes=True)
        except Exception:
            restore()
            raise
    else:
        restore()
    for table, rows in read_all(db).items():
        assert digest(rows) == digest(expected_after[table]), f"Post-write mismatch: {table}"
    (BACKUP / "status.json").write_text(json.dumps({"state": mode, "verified": True}), encoding="utf-8")
    print("VERIFIED: every row in every tracked table equals the expected snapshot.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "detach", "restore"])
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    db = Rest(*load_env())
    prepare(db) if args.mode == "prepare" else change(db, args.mode, args.apply)
