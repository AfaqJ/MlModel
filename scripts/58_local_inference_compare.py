#!/usr/bin/env python3
"""Re-run inference locally with a new SetFit model and compare, row by row,
against the preserved v1.1.0 baseline.

LOCAL ONLY. Reads the preserved baseline snapshot and writes a CSV + summary to
Data/stale/. No Supabase, no network, no writes to any production path.
(CONSTRAINTS.md)

WHAT IT COMPARES
----------------
The baseline is the stored v1.1.0 prediction run over 12,071 invoice line items
(preserved under Data/stale/inference_v1.1.0_baseline_*). Each row already
carries item_text, description, meter_code, the v1.1.0 prediction, its
confidence, and the invoice amount. Provider comes from the invoice's
seller_name, which is the same field the training gold uses.

The new run reproduces the production cascade so the comparison is like-for-like:

    meter lookup  ->  product lookup  ->  SetFit model

Meter and product hits bypass the model in BOTH runs, so those rows are expected
to be unchanged; they are counted, not hidden.

DECISION POLICY
---------------
The stored baseline used the temporary loader's stricter policy (top1 >= 0.80),
while the backend artifact uses 0.70. Comparing a 0.70-gated new run against an
0.80-gated old run would attribute a policy difference to the model. So ONE
policy is applied to both sides here, and it is stated in the output.

Usage:
    .venv-train/bin/python scripts/58_local_inference_compare.py \
        --model models/setfit_base_v1_2_0
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SNAPSHOT = ROOT / "Temp_Inference" / "snapshots" / "normalized_before_company_item_split"
TAXONOMY = ROOT / "Data" / "current_context_2026_06_30" / "taxonomy_from_plan.csv"

# One policy applied to BOTH sides. Matches the loader policy used for the
# production backfill so the auto-accept counts stay comparable to what the
# client actually saw.
ACCEPT_TOP1 = 0.80
ACCEPT_MARGIN = 0.10


def read_csv(path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def decide(code: str, top1: float, margin: float, source: str, weak: set[str]) -> str:
    """Same shape as app/inference/confidence.decide, inlined so this script has
    no dependency on the app's loaded model bundle."""
    if source in ("meter_lookup", "product_lookup"):
        return "auto_accept"
    if code in weak:
        return "review_required"
    if top1 < ACCEPT_TOP1 or margin < ACCEPT_MARGIN:
        return "review_required"
    return "auto_accept"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="path to the new SetFit model dir")
    ap.add_argument("--baseline", default=None,
                    help="baseline dir under Data/stale (default: newest)")
    ap.add_argument("--batch", type=int, default=256)
    args = ap.parse_args()

    # --- locate the preserved baseline --------------------------------------
    if args.baseline:
        base_dir = Path(args.baseline).resolve()
    else:
        candidates = sorted((ROOT / "Data" / "stale").glob("inference_v1.1.0_baseline_*"))
        if not candidates:
            raise SystemExit("no preserved baseline found under Data/stale/")
        base_dir = candidates[-1]
    print(f"baseline : {base_dir.relative_to(ROOT)}")

    items = json.loads((base_dir / "invoice_items.json").read_text())
    invoices = {r["invoice_id"]: r for r in json.loads((SNAPSHOT / "invoices.json").read_text())}
    taxonomy = {r["new_code"]: r for r in read_csv(TAXONOMY)}
    print(f"rows     : {len(items)}")

    # --- load the new model --------------------------------------------------
    # Load the body and head directly rather than via SetFitModel.from_pretrained.
    # from_pretrained runs model-card inference that requires a base-model id in
    # the saved config; for a locally-trained model that field is absent and it
    # raises TypeError deep inside huggingface_hub. Loading the two components is
    # also closer to what the served app actually does (ONNX encoder + joblib head).
    import joblib
    from sentence_transformers import SentenceTransformer

    # resolve() so a relative --model path still works with relative_to(ROOT)
    model_dir = Path(args.model).resolve()
    print(f"model    : {model_dir.relative_to(ROOT)}")
    body = SentenceTransformer(str(model_dir))
    head = joblib.load(model_dir / "model_head.pkl")
    classes = list(head.classes_)
    print(f"           {len(classes)} classes, "
          f"ING-0.1 {'PRESENT' if 'ING-0.1' in classes else 'ABSENT'}, "
          f"class_weight={head.class_weight}")

    class _M:
        """Minimal shim so the batching loop below stays unchanged."""
        @staticmethod
        def predict_proba(texts):
            return head.predict_proba(body.encode(texts, show_progress_bar=False))

    model = _M()

    metrics_path = model_dir / "metrics.json"
    weak_new = set(json.loads(metrics_path.read_text()).get("weak_classes_lt15", [])) \
        if metrics_path.exists() else set()

    # v1.1.0's weak set, for applying the same rule to the baseline side.
    v110_card = ROOT / "artifacts" / "v1.1.0" / "model_card.json"
    weak_old = set(json.loads(v110_card.read_text()).get("weak_classes_lt15_gold", [])) \
        if v110_card.exists() else set()

    # --- lookups (same as production cascade) --------------------------------
    from app.inference.product_lookup import ProductLookup
    from app.inference.meter_lookup import MeterLookup
    products = ProductLookup(ROOT / "app" / "data" / "product_lookup.csv")
    meters = MeterLookup(ROOT / "app" / "data" / "electricity_meter_map.csv")

    import re
    NUMERIC_RE = re.compile(r"[\d\s.,\-/]+$")

    def build_text(item, desc, prov):
        d = (desc or "").strip()
        if NUMERIC_RE.fullmatch(d or "0"):
            d = ""
        return " | ".join(p for p in [(item or "").strip(), d, (prov or "").strip()] if p)

    # --- resolve source + build model inputs ---------------------------------
    rows, to_embed, embed_idx = [], [], []
    for i, it in enumerate(items):
        inv = invoices.get(it["invoice_id"], {})
        provider = inv.get("seller_name", "") or ""
        direction = inv.get("transaction_type", "") or ""

        source, fixed_code = "model", None
        mh = meters.match(it["meter_code"]) if it.get("meter_code") else None
        if mh:
            source, fixed_code = "meter_lookup", mh.category_code
        else:
            ph = products.match(it["item_text"], provider)
            if ph:
                source, fixed_code = "product_lookup", ph.category_code

        rows.append({
            "item_id": it["item_id"], "item_text": it["item_text"],
            "description": it.get("description", ""), "provider": provider,
            "direction": direction, "amount": it.get("amount"),
            "old_code": it.get("predicted_code"), "old_top1": it.get("top1_score"),
            "old_margin": it.get("margin"), "old_source": it.get("prediction_source"),
            "old_decision": it.get("decision"),
            "source": source, "fixed_code": fixed_code,
        })
        # The model runs on every row (production does too — it is the conflict
        # check for lookup hits), except meter hits which return early.
        if source != "meter_lookup":
            to_embed.append(build_text(it["item_text"], it.get("description", ""), provider))
            embed_idx.append(i)

    print(f"model inputs: {len(to_embed)} (meter lookups skip the model: "
          f"{len(rows) - len(to_embed)})")

    # --- batched inference ---------------------------------------------------
    probas = []
    for s in range(0, len(to_embed), args.batch):
        chunk = to_embed[s:s + args.batch]
        probas.append(np.asarray(model.predict_proba(chunk)))
        done = min(s + args.batch, len(to_embed))
        print(f"\r  {done}/{len(to_embed)}", end="", flush=True)
    print()
    proba = np.vstack(probas) if probas else np.zeros((0, len(classes)))

    order = np.argsort(-proba, axis=1)
    for k, i in enumerate(embed_idx):
        r = rows[i]
        c1, c2 = order[k, 0], order[k, 1]
        r["model_code"] = classes[c1]
        r["model_top1"] = float(proba[k, c1])
        r["model_margin"] = float(proba[k, c1] - proba[k, c2])
        r["model_top3"] = [(classes[j], round(float(proba[k, j]), 4)) for j in order[k, :3]]

    # --- resolve final new prediction ----------------------------------------
    for r in rows:
        if r["source"] == "meter_lookup":
            r.update(new_code=r["fixed_code"], new_top1=1.0, new_margin=1.0)
        elif r["source"] == "product_lookup":
            r.update(new_code=r["fixed_code"], new_top1=1.0, new_margin=1.0)
        else:
            r.update(new_code=r.get("model_code"), new_top1=r.get("model_top1", 0.0),
                     new_margin=r.get("model_margin", 0.0))
        r["new_decision"] = decide(r["new_code"], r["new_top1"], r["new_margin"],
                                   r["source"], weak_new)
        # Recompute the OLD decision under the SAME policy, so decision deltas
        # reflect the model, not a threshold difference between the two runs.
        r["old_decision_same_policy"] = decide(
            r["old_code"], float(r["old_top1"] or 0), float(r["old_margin"] or 0),
            r["old_source"], weak_old)

    # --- report ---------------------------------------------------------------
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "Data" / "stale" / f"inference_compare_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    changed = [r for r in rows if r["old_code"] != r["new_code"]]
    model_rows = [r for r in rows if r["source"] == "model"]
    sales = [r for r in rows if r["direction"] == "VENTAS"]

    def pct(n, d):
        return f"{n/d*100:5.1f}%" if d else "  n/a"

    print("\n" + "=" * 74)
    print(f"POLICY APPLIED TO BOTH SIDES: top1 >= {ACCEPT_TOP1}, margin >= {ACCEPT_MARGIN}, "
          f"weak class -> review")
    print("=" * 74)
    print(f"\ntotal rows            : {len(rows)}")
    print(f"  resolved by meter   : {sum(1 for r in rows if r['source']=='meter_lookup')}")
    print(f"  resolved by product : {sum(1 for r in rows if r['source']=='product_lookup')}")
    print(f"  resolved by model   : {len(model_rows)}")
    print(f"\npredicted code CHANGED: {len(changed)}  ({pct(len(changed), len(rows))})")

    old_acc = sum(1 for r in rows if r["old_decision_same_policy"] == "auto_accept")
    new_acc = sum(1 for r in rows if r["new_decision"] == "auto_accept")
    print(f"\nauto_accept  old {old_acc:6d} ({pct(old_acc,len(rows))})  ->  "
          f"new {new_acc:6d} ({pct(new_acc,len(rows))})   delta {new_acc-old_acc:+d}")

    promoted = [r for r in rows if r["old_decision_same_policy"] == "review_required"
                and r["new_decision"] == "auto_accept"]
    demoted = [r for r in rows if r["old_decision_same_policy"] == "auto_accept"
               and r["new_decision"] == "review_required"]
    print(f"  review -> auto_accept : {len(promoted)}")
    print(f"  auto_accept -> review : {len(demoted)}    <- regressions, inspect these")

    if model_rows:
        o = np.array([float(r["old_top1"] or 0) for r in model_rows])
        n = np.array([float(r["new_top1"] or 0) for r in model_rows])
        print(f"\nmodel-decided rows, mean top1: {o.mean():.4f} -> {n.mean():.4f} "
              f"({n.mean()-o.mean():+.4f})")
        print(f"                    median top1: {np.median(o):.4f} -> {np.median(n):.4f}")

    # --- the incident rows ----------------------------------------------------
    print("\n" + "=" * 74)
    print(f"SALES LINES (transaction_type = VENTAS) — n={len(sales)}")
    print("=" * 74)
    by_name = defaultdict(list)
    for r in sales:
        by_name[r["item_text"].strip()].append(r)

    print(f"\n{'item':<24} {'n':>3}  {'v1.1.0':<10} {'->':2} {'v1.2.0':<10} "
          f"{'old t1':>7} {'new t1':>7}  {'now'}")
    print("-" * 92)
    for name in sorted(by_name, key=lambda k: -len(by_name[k])):
        rs = by_name[name]
        oc = Counter(r["old_code"] for r in rs).most_common(1)[0][0]
        nc = Counter(r["new_code"] for r in rs).most_common(1)[0][0]
        ot = np.mean([float(r["old_top1"] or 0) for r in rs])
        nt = np.mean([float(r["new_top1"] or 0) for r in rs])
        acc = sum(1 for r in rs if r["new_decision"] == "auto_accept")
        flag = "OK " if nc.startswith("ING-") else "!! "
        print(f"{flag}{name[:22]:<22} {len(rs):>3}  {oc:<10} -> {nc:<10} "
              f"{ot:7.4f} {nt:7.4f}  {acc}/{len(rs)} auto")

    sales_ing_old = sum(1 for r in sales if (r["old_code"] or "").startswith("ING-"))
    sales_ing_new = sum(1 for r in sales if (r["new_code"] or "").startswith("ING-"))
    print(f"\nsales rows predicted as income: {sales_ing_old} -> {sales_ing_new} "
          f"(of {len(sales)})")

    # --- direction violations -------------------------------------------------
    bad_old = sum(1 for r in rows if r["direction"] == "COMPRAS"
                  and (r["old_code"] or "").startswith("ING-"))
    bad_new = sum(1 for r in rows if r["direction"] == "COMPRAS"
                  and (r["new_code"] or "").startswith("ING-"))
    print(f"purchase rows predicted as income (should be 0): {bad_old} -> {bad_new}")

    # --- write the full row-level diff ---------------------------------------
    csv_path = out_dir / "row_comparison.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["item_id", "direction", "item_text", "description", "provider",
                    "amount", "source", "old_code", "old_top1", "old_decision_same_policy",
                    "new_code", "new_top1", "new_decision", "changed"])
        for r in rows:
            w.writerow([r["item_id"], r["direction"], r["item_text"], r["description"],
                        r["provider"], r["amount"], r["source"], r["old_code"],
                        r["old_top1"], r["old_decision_same_policy"], r["new_code"],
                        round(float(r["new_top1"] or 0), 4), r["new_decision"],
                        int(r["old_code"] != r["new_code"])])
    print(f"\nrow-level diff written: {csv_path.relative_to(ROOT)}")

    summary = {
        "generated": stamp, "model": str(model_dir.relative_to(ROOT)),
        "baseline": str(base_dir.relative_to(ROOT)),
        "policy": {"accept_top1": ACCEPT_TOP1, "accept_margin": ACCEPT_MARGIN},
        "rows": len(rows), "changed": len(changed),
        "auto_accept_old": old_acc, "auto_accept_new": new_acc,
        "review_to_auto": len(promoted), "auto_to_review": len(demoted),
        "sales_rows": len(sales),
        "sales_as_income_old": sales_ing_old, "sales_as_income_new": sales_ing_new,
        "purchases_as_income_old": bad_old, "purchases_as_income_new": bad_new,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"summary written       : {(out_dir / 'summary.json').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
