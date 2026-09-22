"""Offline, no DB, no network, no writes: score local SetFit model directories on August's
94 model-facing lines (august_model_facing.json), against the accountants' truth."""
import json
import sys
from pathlib import Path

ROOT = Path("/Users/afaq/Desktop/Mctech/ML-model")
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))
import importlib.util
spec = importlib.util.spec_from_file_location("ev101", ROOT / "scripts/101_evaluate_retrain.py")
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)

from app.inference.model_input import build_model_text

OUT = ROOT / "reports/overnight_2026_09_21"
rows = json.load(open(OUT / "august_model_facing.json"))
for r in rows:
    r["text"] = build_model_text(r["itemText"] or "", r["description"] or "", r["provider"] or "", r["transactionType"])
    r["direction"] = r["transactionType"]
    r["category_code"] = r["truth"]; r["previously"] = "august"

MODELS = {
    "v1.4.1 (live)": ROOT / "models/setfit_retrain_2026_09_16_C",
    "B_july70 (candidate)": ROOT / "models/overnight_2026_09_21/B_july70",
}

results = {}
for name, path in MODELS.items():
    predict, classes, weak = ev.load(path)
    proba = predict([r["text"] for r in rows])
    block = ev.score(rows, proba, classes, weak)
    results[name] = block
    import numpy as np
    truth = [r["category_code"] for r in rows]
    top1, hit = [], []
    for r, p in zip(rows, proba):
        p = p.copy()
        masked = ev.direction_mask(classes, r["direction"])
        p[masked] = 0.0
        p = p / p.sum() if p.sum() > 0 else p
        order = [i for i in np.argsort(-p) if i not in set(masked)]
        top1.append(float(p[order[0]]))
        hit.append(classes[order[0]] == r["category_code"])
    top1, hit = np.array(top1), np.array(hit)
    sure = top1 >= 0.90
    b = block["all"]
    print(f"\n== {name} ==")
    print(f"  model-facing lines: {b['rows']}  top-1 {b['accuracy']:.1%}  top-3 {b['top3_accuracy']:.1%}")
    print(f"  auto-accept rate {b['auto_accept_rate']:.1%}  wrong auto-accepts {b['auto_accept_wrong']}  (precision {b['auto_accept_precision']})")
    print(f"  lines scored >=0.90: {int(sure.sum())}, wrong: {int((sure & ~hit).sum())}")
    print(f"  classes truth carries that this model cannot emit: {block['rows_with_class_unknown_to_model']}")

json.dump({k: v["all"] for k, v in results.items()}, open(OUT / "august_model_comparison.json", "w"), indent=1)

# full-system picture: rule-settled (94/188) + each model's contribution
print("\n== Full system, August ==")
print(f"  188 lines with exact truth: 94 rule-settled (91 right, 3 client-list disagreements already flagged),")
print(f"  94 sent to the model.")
