#!/usr/bin/env bash
# Regression check. Run this at every checkpoint, before moving on.
#
# Three virtualenvs mean neither pytest can collect the other's tests, so the
# suites run separately and this script is the single command that runs both.
#
#   ./check.sh          tests only, no network
#   ./check.sh --live   also re-reads Supabase and re-parses a real month
set -uo pipefail
cd "$(dirname "$0")"
fail=0
step() { printf '\n\033[1m== %s\033[0m\n' "$1"; }

step "classifier"
# A glob, not a hand-written list. The list version already rotted: two new
# yunt test files were silently collected by the classifier venv, so this step
# reported 116 tests and nobody would have noticed which suite ran what.
.venv-backend/bin/python -m pytest tests/ -q --ignore-glob='tests/test_yunt_*.py' || fail=1

step "yunt — service, parser, batch"
.venv-yunt/bin/python -m pytest tests/test_yunt_*.py -q || fail=1

step "yunt — corpus replay (offline, no network)"
.venv-yunt/bin/python - <<'PY' || fail=1
import glob, sys
sys.path.insert(0, ".")
from yunt import dte

files = sorted(glob.glob("Data/Raw_Data/dte_96685810_COMPRAS/2025*/*.xml"))
if not files:
    print("raw corpus not present — skipped"); raise SystemExit(0)

docs = raw = lines = dropped = bad = broken = 0
for path in files:
    try:
        parsed = dte.parse(open(path, "rb").read(), "COMPRAS")
    except Exception:
        broken += 1
        continue
    for doc in parsed:
        docs += 1
        raw += doc.raw_detalle_count
        lines += len(doc.lines)
        dropped += len(doc.dropped)
        bad += sum(1 for line in doc.lines if not line.reconciles)

rate = bad / lines if lines else 1
print(f"{len(files)} files -> {docs} documents, {lines} lines, {broken} unparseable")
print(f"reconciliation: {raw} raw <Detalle> = {lines} lines + {dropped} recorded drops")
print(f"lines that do not reconcile: {bad} ({100 * rate:.2f}%)")

ok = True
# Every raw line is accounted for. A silent drop is what left 357 unexplained.
if raw != lines + dropped:
    print("FAIL: raw <Detalle> count does not equal lines + recorded drops"); ok = False
# Was 10.9% before the decimal, discount, recargo and scaling fixes.
if rate > 0.02:
    print("FAIL: reconciliation rate regressed toward the pre-fix 10.9%"); ok = False
if broken:
    print(f"FAIL: {broken} files no longer parse"); ok = False
print("OK" if ok else "REGRESSION")
raise SystemExit(0 if ok else 1)
PY

if [ "${1:-}" = "--live" ]; then
  step "yunt — live re-send is a no-op (reads only)"
  .venv-yunt/bin/python - <<'PY' || fail=1
import glob, io, os, sys, zipfile
sys.path.insert(0, ".")
from yunt import batch

buf = io.BytesIO()
count = 0
with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
    for direction, root in (("COMPRAS", "Data/Raw_Data/dte_96685810_COMPRAS/202508"),
                            ("VENTAS",  "Data/Raw_Data/dte_96685810_VENTAS/202508")):
        for path in sorted(glob.glob(f"{root}/*.xml")):
            archive.write(path, f"{direction}/{os.path.basename(path)}")
            count += 1
if not count:
    print("raw corpus not present — skipped"); raise SystemExit(0)

result = batch.read_zip(buf.getvalue(), batch.existing_keys())
print(f"{count} files -> {len(result.documents)} new, {len(result.duplicates)} already held")
if result.documents or len(result.duplicates) != count:
    print("FAIL: a month already in the database must come back as all duplicates")
    raise SystemExit(1)
print("OK")
PY
fi

step "result"
[ "$fail" = 0 ] && echo "all green" || echo "SOMETHING FAILED"
exit $fail
