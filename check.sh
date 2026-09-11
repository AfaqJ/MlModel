#!/usr/bin/env bash
# Regression check. Run this at every checkpoint, before moving on.
#
# Classifier tests only, with no network. The Yunt runs in ../milk-company;
# its TypeScript checks live in that repository's check.sh.
set -uo pipefail
cd "$(dirname "$0")"
fail=0
step() { printf '\n\033[1m== %s\033[0m\n' "$1"; }

step "classifier"
.venv-backend/bin/python -m pytest tests/ -q || fail=1

step "result"
[ "$fail" = 0 ] && echo "all green" || echo "SOMETHING FAILED"
exit $fail
