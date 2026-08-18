#!/usr/bin/env python3
"""Full read-only export of the five live tables, taken before any write.

Every column is captured, including the generated primary keys, so a restore can
recreate the exact rows the database held. Each table is written to JSONL with a
row count and a SHA-256 over the sorted payload, and the export refuses to
declare success unless the file count matches the server's own `count=exact`
figure for that table.

This is a **logical** backup: rows only. It does not capture schema, indexes,
constraints, policies or triggers. Take a Supabase snapshot as well if you want
a restore path that rebuilds the structure too.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from supabase_rest import Rest, load_env  # noqa: E402

TABLES = ("categories", "companies", "item_catalog", "invoices", "invoice_items")
DEFAULT_DIR = ROOT / "backups"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.output or (DEFAULT_DIR / f"supabase_{stamp}")
    output.mkdir(parents=True, exist_ok=True)

    rest = Rest(*load_env())
    manifest: dict = {
        "taken_at": datetime.now(timezone.utc).isoformat(),
        "kind": "logical row export via PostgREST (no schema/indexes/policies)",
        "tables": {},
    }
    failures = []

    for table in TABLES:
        expected = rest.count(table)
        rows = rest.get(table, "*")
        path = output / f"{table}.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        ok = len(rows) == expected
        if not ok:
            failures.append(f"{table}: exported {len(rows)} but server reports {expected}")
        manifest["tables"][table] = {
            "rows_exported": len(rows),
            "rows_reported_by_server": expected,
            "complete": ok,
            "sha256": digest,
            "bytes": path.stat().st_size,
        }
        print(f"  {'ok  ' if ok else 'FAIL'} {table:15s} {len(rows):>6} rows  {digest[:16]}…")

    manifest["complete"] = not failures
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"\nbackup: {output.relative_to(ROOT)}")
    if failures:
        raise SystemExit("BACKUP INCOMPLETE — do not upload:\n  " + "\n  ".join(failures))
    print("all tables exported and row counts verified against the server")


if __name__ == "__main__":
    main()
