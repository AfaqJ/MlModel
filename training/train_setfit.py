"""MCT-37 — SetFit training for the Antillanca invoice line-item classifier.

Architecture per docs/DECISIONS.md D-025 (superseded script; v1.3.3 used train_recovery_setfit.py):
  SetFit contrastive fine-tune of sentence-transformers/paraphrase-multilingual-mpnet-base-v2
  + LogisticRegression head (trained automatically inside trainer.train()).

Input construction (decided 2026-07-03 after raw-data field audit):
  item_text | description | provider [| giro]
  - description is BLANKED when numeric-only (client product codes like "10000026" carry no semantics)
  - giro = provider's registered business activity (GiroEmis in DTE XML); joined onto gold
    via training/provider_giro_map.csv. Present for ~65% of gold, ~100% at inference.
  - Two variants trained (--variant base|giro|both); pick winner by val macro-F1.

Usage:
  .venv-train/bin/python training/train_setfit.py --variant both
Outputs (per variant): models/setfit_<variant>/  (full PyTorch SetFit model)
                       models/setfit_<variant>/metrics.json
"""
from __future__ import annotations
import argparse, csv, json, re, random, time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "Data/gold/_master_gold.csv"
GIRO_MAP = ROOT / "training/provider_giro_map.csv"
TAXONOMY = ROOT / "Data/current_context_2026_06_30"  # not needed for training itself
SEED = 42
BASE_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
NUMERIC_RE = re.compile(r"[\d\s.,\-/]+$")


def clean_desc(d: str) -> str:
    d = (d or "").strip()
    return "" if not d or NUMERIC_RE.fullmatch(d) else d


def build_text(item: str, desc: str, prov: str, giro: str | None) -> str:
    parts = [item.strip(), clean_desc(desc), (prov or "").strip()]
    if giro:
        parts.append(giro.strip())
    return " | ".join(p for p in parts if p)


def _norm_text(value: str) -> str:
    import unicodedata
    s = (value or "").lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", s).strip()


def load_rows(use_giro: bool, dedup: bool = True):
    """Load gold, and by default collapse rows that produce an IDENTICAL model input.

    WHY
    ---
    Gold is a record of audited rows, so the same business fact can legitimately
    appear many times: 36 rows carry the identical text
    "administracion del servicio | cooperativa rural elect r buen" for EXP-11.1.

    Those duplicates are not extra information — after build_text() they are the
    same string. Keeping them does two kinds of damage:

      1. LEAKAGE. Copies land on both sides of the train/val split, so the model
         is tested on strings it memorised. Measured before this fix: 56 of 448
         validation rows (12.5%) had their exact text in training. Every
         validation number ever reported for this project, including v1.1.0's
         0.7441 accuracy, was inflated by it.
      2. SKEWED PRIORS. The LogisticRegression head sees ADM-1.7 as 117 examples
         when it has 57 distinct ones, and ADM-2.2 as 29 when it has 5.

    NOTE the difference from BUG-001. That bug deduped on item_text ALONE, which
    collapsed 47 genuinely different milk rows into 1 and deleted a category.
    This dedups on the exact string the model consumes, so it can only ever remove
    rows that carry zero additional signal. Verified: it starves no class below
    the 2-example floor and leaves every income category untouched.
    """
    giro_map = {}
    if use_giro:
        with open(GIRO_MAP) as f:
            giro_map = {r["provider"]: r["giro"] for r in csv.DictReader(f)}
    rows = []
    seen: set[tuple[str, str]] = set()
    dropped = 0
    with open(GOLD) as f:
        for r in csv.DictReader(f):
            prov = r["provider"].strip()
            giro = giro_map.get(prov.upper()) if use_giro else None
            text = build_text(r["item_text"], r["description"], prov, giro)
            label = r["category_code"].strip()
            if dedup:
                key = (_norm_text(text), label)
                if key in seen:
                    dropped += 1
                    continue
                seen.add(key)
            rows.append({
                "text": build_text(r["item_text"], r["description"], prov, giro),
                "label": r["category_code"].strip(),
                "gold_id": r["gold_id"],
                # 'holdout' rows are harvested real invoice lines deliberately
                # withheld from training so the metric on that class means
                # something (DECISIONS.md D-004).
                "split": (r.get("split") or "").strip(),
                # Synthetic rows exist only to clear the <2 training floor. They
                # must never validate anything (D-005).
                "source": (r.get("source") or "").strip(),
            })
    if dedup and dropped:
        print(f"[data] collapsed {dropped} rows that produce an identical model input "
              f"({len(rows)} distinct inputs remain) — prevents train/val leakage")
    return rows


def stratified_split(rows, min_train_only=5, val_frac=0.2):
    """Split gold into train/validation.

    Rules, in priority order:
      1. split=='holdout'      -> ALWAYS validation, never trained.
      2. source starts with    -> ALWAYS train. A synthetic row cannot validate
         'synthetic'              anything; scoring against one is self-deception.
      3. <2 examples           -> excluded entirely (SetFit needs a positive pair).
      4. 2..min_train_only-1   -> all to train (too few to spare a val row).
      5. otherwise             -> 80/20 with >=1 val example.

    Rules 3 and 4 are what hid BUG-001: ING-0.1 (1 example) took rule 3 and was
    silently dropped from the model; ING-0.2 (3) and ING-0.4 (2) took rule 4 and
    were trained but invisible to every metric. Both are now reported loudly by
    the caller, and the export gate refuses a class with no validation row."""
    rng = random.Random(SEED)
    by_class = defaultdict(list)
    for r in rows:
        by_class[r["label"]].append(r)
    train, val, excluded = [], [], []
    for label, items in sorted(by_class.items()):
        forced_val = [r for r in items if r["split"] == "holdout"]
        pool = [r for r in items if r["split"] != "holdout"]
        synthetic = [r for r in pool if r["source"].startswith("synthetic")]
        pool = [r for r in pool if not r["source"].startswith("synthetic")]

        rng.shuffle(pool)
        val += forced_val

        if len(items) < 2:
            excluded.append(label)
            continue
        if forced_val:
            # Validation coverage already guaranteed by the holdout slice.
            train += pool + synthetic
            continue
        if len(pool) < min_train_only:
            train += pool + synthetic
            continue
        n_val = max(1, round(len(pool) * val_frac))
        val += pool[:n_val]
        train += pool[n_val:] + synthetic
    return train, val, excluded


def evaluate(model, val_rows, labels_order):
    texts = [r["text"] for r in val_rows]
    y_true = [r["label"] for r in val_rows]
    proba = model.predict_proba(texts)
    proba = np.asarray(proba)
    idx_sorted = np.argsort(-proba, axis=1)
    classes = list(model.labels) if getattr(model, "labels", None) else labels_order
    top1 = [classes[i] for i in idx_sorted[:, 0]]
    top3 = [[classes[j] for j in row[:3]] for row in idx_sorted]

    from sklearn.metrics import accuracy_score, f1_score, classification_report
    acc = accuracy_score(y_true, top1)
    macro_f1 = f1_score(y_true, top1, average="macro", zero_division=0)
    top3_acc = float(np.mean([t in c for t, c in zip(y_true, top3)]))
    report = classification_report(y_true, top1, zero_division=0, output_dict=True)

    # confidence buckets + threshold sweep (auto-accept policy calibration)
    top1_scores = proba[np.arange(len(proba)), idx_sorted[:, 0]]
    top2_scores = proba[np.arange(len(proba)), idx_sorted[:, 1]]
    margins = top1_scores - top2_scores
    correct = np.array([t == p for t, p in zip(y_true, top1)])
    buckets = {}
    for lo in np.arange(0.0, 1.0, 0.1):
        m = (top1_scores >= lo) & (top1_scores < lo + 0.1)
        if m.sum():
            buckets[f"{lo:.1f}-{lo + 0.1:.1f}"] = {"n": int(m.sum()), "acc": round(float(correct[m].mean()), 3)}
    sweep = []
    for t1 in [0.5, 0.6, 0.7, 0.8]:
        for mg in [0.1, 0.2, 0.3]:
            m = (top1_scores >= t1) & (margins >= mg)
            if m.sum():
                sweep.append({"top1": t1, "margin": mg,
                              "accept_rate": round(float(m.mean()), 3),
                              "accepted_acc": round(float(correct[m].mean()), 3)})
    # Income slice, reported SEPARATELY from the aggregate.
    # v1.1.0 shipped on 0.7441 aggregate accuracy over a validation set with
    # ZERO income rows. The aggregate number was real and said nothing about the
    # client's core revenue lines. Never release on aggregate alone. (D-008)
    income_idx = [i for i, t in enumerate(y_true) if t.startswith("ING-")]
    income = {
        "n": len(income_idx),
        "accuracy": round(float(np.mean([y_true[i] == top1[i] for i in income_idx])), 4)
        if income_idx else None,
        "top3_accuracy": round(float(np.mean([y_true[i] in top3[i] for i in income_idx])), 4)
        if income_idx else None,
        "per_row": [{"true": y_true[i], "pred": top1[i],
                     "score": round(float(top1_scores[i]), 4)} for i in income_idx],
    }

    return {
        "val_n": len(val_rows), "accuracy": round(acc, 4), "macro_f1": round(macro_f1, 4),
        "top3_accuracy": round(top3_acc, 4),
        "income_slice": income,
        "confidence_buckets": buckets, "threshold_sweep": sweep,
        "per_class": {k: {"precision": round(v["precision"], 3), "recall": round(v["recall"], 3),
                          "f1": round(v["f1-score"], 3), "support": int(v["support"])}
                      for k, v in report.items() if isinstance(v, dict) and k not in ("macro avg", "weighted avg")},
    }


class MPSCacheCleaner:
    """Return PyTorch's cached GPU memory to the system every N steps.

    WHY THIS EXISTS
    ---------------
    PyTorch's MPS allocator requests memory from Metal in large blocks and keeps
    them after the tensors using them are freed, so re-allocation is fast. Over a
    training run that reserve grows without bound. Measured on this project:

        allocate a 200 MiB tensor -> pytorch tensors 200 MiB, driver holds 1024 MiB
        delete that tensor        -> pytorch tensors   0 MiB, driver holds 1024 MiB
        torch.mps.empty_cache()   -> pytorch tensors   0 MiB, driver holds    0.5 MiB

    The result was an OOM at
        5.35 GiB live + 14.34 GiB cached + 0.73 GiB needed = 20.42 > 20.13 limit
    i.e. the process starved inside its own budget while sitting on 14 GiB it was
    not using — and, worse, holding that memory away from every other process on
    a 16 GB shared-memory machine.

    Raising the ceiling (PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0) also "works", but
    it removes the safety limit and lets the hoard grow larger still. Emptying
    the cache periodically fixes the cause instead. (DECISIONS.md D-011)

    Cost: empty_cache() forces the next allocations to go back to Metal, so
    calling it too often slows training. Every 50 steps is a reasonable trade.
    """

    def __init__(self, every: int = 50, verbose: bool = False):
        self.every = every
        self.verbose = verbose
        self.peak_reserved = 0

    def on_step_end(self, args, state, control, **kwargs):
        import torch
        if not torch.backends.mps.is_available():
            return
        reserved = torch.mps.driver_allocated_memory()
        self.peak_reserved = max(self.peak_reserved, reserved)
        if state.global_step and state.global_step % self.every == 0:
            torch.mps.empty_cache()
            if self.verbose:
                gib = 1024 ** 3
                print(f"    [step {state.global_step}] reserved "
                      f"{reserved/gib:.2f} -> {torch.mps.driver_allocated_memory()/gib:.2f} GiB")

    # TrainerCallback protocol: the handler calls every hook, so no-op the rest.
    def __getattr__(self, item):
        if item.startswith("on_"):
            return lambda *a, **k: None
        raise AttributeError(item)


def train_variant(name: str, use_giro: bool, args_cli):
    import torch
    from setfit import SetFitModel, Trainer, TrainingArguments
    from datasets import Dataset

    random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)

    rows = load_rows(use_giro)
    train_rows, val_rows, excluded = stratified_split(rows)
    counts = Counter(r["label"] for r in train_rows)
    val_counts = Counter(r["label"] for r in val_rows)

    print(f"[{name}] train={len(train_rows)} val={len(val_rows)} classes={len(counts)}")

    # Loud, not a log line buried in the output. A class silently vanishing from
    # the model is exactly how BUG-001 shipped.
    if excluded:
        print(f"[{name}] !! EXCLUDED (<2 examples, NOT in the model): {excluded}")
    blind = sorted(c for c in counts if val_counts.get(c, 0) == 0)
    if blind:
        print(f"[{name}] !! TRAINED BUT UNVALIDATED (no val row, invisible to metrics): {blind}")

    labels = sorted(counts)
    # class_weight='balanced' — v1.1.0 oversampled contrastive pairs but left the
    # LR head unweighted, so rare classes were balanced during body fine-tuning
    # and disadvantaged again at the head. (D-007)
    model = SetFitModel.from_pretrained(
        BASE_MODEL, labels=labels, head_params={"class_weight": "balanced"}
    )
    # invoice lines are short (~15-50 tokens even with giro); 64 halves MPS memory vs 128
    # measured on the v1.2.0 gold set: p50=25, p95=50, p99=62 tokens, so 64
    # truncates 0.8% of rows. Do not lower to 48 (6.1%) or 32 (24%).
    model.model_body.max_seq_length = 64

    if args_cli.gradient_checkpointing:
        # Standard memory-for-compute trade: instead of keeping every layer's
        # activations for the backward pass, keep a few checkpoints and recompute
        # the rest. Cuts activation memory substantially at ~20-30% slower steps.
        #
        # This is the principled fix for the MPS OOM on a 16 GB machine. The
        # alternatives are worse: raising PYTORCH_MPS_HIGH_WATERMARK_RATIO removes
        # the safety ceiling, and freezing the token embeddings changes what is
        # actually learned. Checkpointing changes neither the maths nor the result
        # — the same gradients are computed, just recomputed rather than stored.
        auto = model.model_body[0].auto_model
        auto.gradient_checkpointing_enable()
        auto.config.use_cache = False
        print(f"[{name}] gradient checkpointing ON (lower memory, ~25% slower)")

    if args_cli.freeze_embeddings:
        # The token-embedding matrix is 250,002 x 768. Its gradient is a single
        # 732.43 MiB allocation, and it is BATCH-INDEPENDENT — which is why
        # lowering --batch-size never helped the MPS OOM on a 16GB machine.
        #
        # Freezing it is also defensible on its own terms: contrastive
        # fine-tuning on ~1,850 short domain texts has no business rewriting a
        # 250k-token multilingual vocabulary, and the encoder blocks above it
        # still train normally. (DECISIONS.md D-011)
        emb = model.model_body[0].auto_model.embeddings.word_embeddings
        emb.weight.requires_grad_(False)
        frozen = emb.weight.numel() * 4 / 1048576
        print(f"[{name}] froze token embeddings: {emb.weight.shape[0]:,} x "
              f"{emb.weight.shape[1]} ({frozen:.0f} MiB of gradient not allocated)")
    train_ds = Dataset.from_dict({"text": [r["text"] for r in train_rows],
                                  "label": [r["label"] for r in train_rows]})
    targs = TrainingArguments(
        output_dir=str(ROOT / f"models/_checkpoints_{name}"),
        # batch 8 fit 16GB unified memory when v1.1.0 was trained, but only with
        # the machine relatively idle. With browsers/Electron apps resident it
        # OOMs on the backward pass. --batch-size 4 halves activation memory.
        batch_size=args_cli.batch_size, num_epochs=1,
        body_learning_rate=2e-5,
        sampling_strategy="oversampling",
        max_steps=args_cli.max_steps,
        seed=SEED,
    )
    trainer = Trainer(model=model, args=targs, train_dataset=train_ds)
    # Keep PyTorch's MPS reserve from growing unbounded. Without this the run
    # OOMs inside its own budget and starves every other process on the machine.
    cleaner = MPSCacheCleaner(every=args_cli.empty_cache_every,
                              verbose=args_cli.log_memory)
    if args_cli.empty_cache_every > 0:
        trainer.add_callback(cleaner)
        print(f"[{name}] MPS cache cleared every {args_cli.empty_cache_every} steps")
    t0 = time.time()
    trainer.train()
    train_min = round((time.time() - t0) / 60, 1)
    if torch.backends.mps.is_available():
        print(f"[{name}] peak MPS memory reserved: "
              f"{cleaner.peak_reserved / 1024**3:.2f} GiB")
        torch.mps.empty_cache()
    print(f"[{name}] trained in {train_min} min")

    metrics = evaluate(model, val_rows, labels)
    metrics.update({
        "variant": name, "use_giro": use_giro, "base_model": BASE_MODEL,
        "train_n": len(train_rows), "trained_classes": len(labels),
        "excluded_classes": excluded, "train_minutes": train_min, "seed": SEED,
        "unvalidated_classes": blind,
        "head_class_weight": "balanced",
        "frozen_token_embeddings": bool(args_cli.freeze_embeddings),
        "batch_size": args_cli.batch_size,
        "max_seq_length": 64,
        "gold_rows": len(rows),
        "weak_classes_lt15": sorted(k for k, v in Counter(r["label"] for r in rows).items() if v < 15),
    })
    # NEVER write into models/setfit_base while v1.1.0 is the deployed reference
    # and the comparison baseline. --tag forces a distinct directory.
    # (CONSTRAINTS.md "Artifacts and models")
    out = ROOT / f"models/setfit_{name}{args_cli.tag}"
    if out.exists() and not args_cli.overwrite:
        raise SystemExit(
            f"refusing to overwrite existing {out.relative_to(ROOT)} — "
            f"pass a different --tag, or --overwrite if you really mean it"
        )
    model.save_pretrained(str(out))
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False))
    # persist the exact split for reproducible calibration later
    with open(out / "val_split.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["gold_id", "text", "label"])
        for r in val_rows: w.writerow([r["gold_id"], r["text"], r["label"]])
    print(f"[{name}] acc={metrics['accuracy']} macroF1={metrics['macro_f1']} top3={metrics['top3_accuracy']}")
    del trainer, model
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()
    return metrics


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=["base", "giro", "both"], default="both")
    ap.add_argument("--max-steps", type=int, default=4000, dest="max_steps")
    ap.add_argument("--tag", default="_v1_2_0",
                    help="suffix for the output dir, e.g. models/setfit_base_v1_2_0. "
                         "Empty string would overwrite the v1.1.0 model — don't.")
    ap.add_argument("--overwrite", action="store_true",
                    help="allow writing over an existing model directory")
    ap.add_argument("--batch-size", type=int, default=8, dest="batch_size",
                    help="lower to 4 or 2 if MPS runs out of memory")
    ap.add_argument("--freeze-embeddings", action="store_true", default=False,
                    dest="freeze_embeddings",
                    help="freeze the 250k-token embedding matrix, saving a "
                         "732 MiB batch-independent gradient allocation. Default "
                         "OFF: with --empty-cache-every the memory is available, "
                         "and leaving embeddings trainable matches v1.1.0.")
    ap.add_argument("--no-freeze-embeddings", action="store_false",
                    dest="freeze_embeddings")
    ap.add_argument("--empty-cache-every", type=int, default=50,
                    dest="empty_cache_every",
                    help="release PyTorch's cached MPS memory every N steps "
                         "(0 disables). Prevents the reserve growing unbounded "
                         "and starving other processes on shared memory.")
    ap.add_argument("--log-memory", action="store_true", dest="log_memory",
                    help="print reserved memory before/after each cache clear")
    ap.add_argument("--gradient-checkpointing", action="store_true", default=False,
                    dest="gradient_checkpointing",
                    help="recompute activations in the backward pass instead of "
                         "storing them. MEASURED on this machine: reduces the "
                         "allocator reserve 14.34 -> 13.63 GiB, which is NOT "
                         "enough to fit the 732 MiB embedding gradient. Costs "
                         "~25%% speed. Default off because it does not solve the "
                         "OOM on its own.")
    ap.add_argument("--no-gradient-checkpointing", action="store_false",
                    dest="gradient_checkpointing")
    a = ap.parse_args()
    results = {}
    if a.variant in ("base", "both"):
        results["base"] = train_variant("base", use_giro=False, args_cli=a)
    if a.variant in ("giro", "both"):
        results["giro"] = train_variant("giro", use_giro=True, args_cli=a)
    if len(results) == 2:
        b, g = results["base"], results["giro"]
        print("\n=== VARIANT COMPARISON ===")
        for k in ("accuracy", "macro_f1", "top3_accuracy"):
            print(f"{k}: base={b[k]} giro={g[k]}")
