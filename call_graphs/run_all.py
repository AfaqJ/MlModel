"""Run every trace script in order and generate all PNGs into output/.

Usage (from the repo root):
    .venv-backend/bin/python call_graphs/run_all.py
"""
from __future__ import annotations

import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = [
    "trace_health.py",
    "trace_artifact_check.py",
    "trace_model_info.py",
    "trace_predict.py",
    "trace_predict_batch.py",
]

for script in SCRIPTS:
    print(f"\n=== running {script} ===")
    runpy.run_path(str(HERE / script), run_name="__main__")

print("\nDone. Open the PNGs in call_graphs/output/")
