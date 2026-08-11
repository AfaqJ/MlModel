#!/usr/bin/env python3
"""Train the transaction-aware recovery candidate with the full SetFit encoder.

This is intentionally separate from train_setfit.py, whose outputs and behavior
belong to the previous experiments. The defaults here keep every encoder
parameter trainable and use SetFit's standard AdamW optimizer. The material MPS
memory fix is fixed-length padding: dynamic batch shapes caused Apple's graph
backend to retain a separate compiled graph allocation for each observed length.
Adafactor remains available as a lower-memory diagnostic option, but is not the
release default.

Nothing in this script deploys, exports, uploads, or overwrites the v1.1 model.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.inference.model_input import build_model_text


DEFAULT_GOLD = ROOT / "Data/candidates/recovery_v1_3_1/master_gold.csv"
DEFAULT_SPLIT = ROOT / "Data/candidates/recovery_v1_3_1/split_seed42.csv"
DEFAULT_OUTPUT = ROOT / "models/setfit_base_recovery_v1_3_1"
DEFAULT_SMOKE_REPORT = ROOT / "reports/recovery_v1_3_1/memory_smoke.json"
BASE_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
NUMERIC_RE = re.compile(r"[\d\s.,\-/]+$")
SEED = 42


def normalize(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", (value or "").lower())
    value = value.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def clean_description(value: str | None) -> str:
    value = (value or "").strip()
    return "" if not value or NUMERIC_RE.fullmatch(value) else value


def build_text(row: dict[str, str]) -> str:
    return build_model_text(
        row.get("item_text") or "",
        row.get("description") or "",
        row.get("provider") or "",
        row.get("direction"),
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_and_collapse(path: Path) -> tuple[list[dict[str, str]], dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        source_rows = list(csv.DictReader(handle))

    grouped: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in source_rows:
        text = build_text(row)
        grouped[normalize(text)].append({**row, "text": text})

    contradictions = []
    collapsed = []
    for input_key, rows in sorted(grouped.items()):
        labels = sorted({row["category_code"].strip() for row in rows})
        if len(labels) > 1:
            contradictions.append({
                "normalized_input": input_key,
                "labels": labels,
                "gold_ids": sorted(row["gold_id"] for row in rows),
            })
            continue
        # Stable representative: the source-of-truth keeps every invoice row,
        # while training sees one copy of an identical normalized model input.
        representative = min(rows, key=lambda row: row["gold_id"])
        collapsed.append(representative)

    if contradictions:
        raise RuntimeError(
            "refusing to train on cross-label model-input contradictions: "
            + json.dumps(contradictions[:10], ensure_ascii=False)
        )

    audit = {
        "source_rows": len(source_rows),
        "normalized_distinct_inputs": len(collapsed),
        "same_label_duplicates_collapsed": len(source_rows) - len(collapsed),
        "cross_label_contradictions": 0,
    }
    return collapsed, audit


def deterministic_split(
    rows: list[dict[str, str]], seed: int = SEED, val_fraction: float = 0.20
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    by_label: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_label[row["category_code"].strip()].append(row)

    train, validation, excluded = [], [], []
    for label, label_rows in sorted(by_label.items()):
        ordered = sorted(
            label_rows,
            key=lambda row: sha256_bytes(
                f"{seed}\0{row['gold_id']}\0{normalize(row['text'])}".encode()
            ),
        )
        if len(ordered) < 2:
            for row in ordered:
                row["split"] = "excluded_lt2"
            excluded.extend(ordered)
            continue
        if len(ordered) < 5:
            for row in ordered:
                row["split"] = "train_weak"
            train.extend(ordered)
            continue
        n_validation = max(1, round(len(ordered) * val_fraction))
        for row in ordered[:n_validation]:
            row["split"] = "validation"
        for row in ordered[n_validation:]:
            row["split"] = "train"
        validation.extend(ordered[:n_validation])
        train.extend(ordered[n_validation:])

    return train, validation, excluded


def write_or_verify_split(
    path: Path,
    all_rows: list[dict[str, str]],
    gold_sha256: str,
    overwrite: bool,
) -> str:
    fields = ["gold_sha256", "seed", "split", "gold_id", "category_code", "text", "text_sha256"]
    output_rows = []
    for row in sorted(all_rows, key=lambda item: (item["split"], item["category_code"], item["gold_id"])):
        output_rows.append({
            "gold_sha256": gold_sha256,
            "seed": str(SEED),
            "split": row["split"],
            "gold_id": row["gold_id"],
            "category_code": row["category_code"],
            "text": row["text"],
            "text_sha256": sha256_bytes(normalize(row["text"]).encode()),
        })

    import io
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(output_rows)
    rendered = buffer.getvalue()

    if path.exists() and not overwrite:
        existing = path.read_text(encoding="utf-8")
        if existing != rendered:
            raise RuntimeError(
                f"locked split differs from deterministic result: {path}; "
                "inspect before using --overwrite-split"
            )
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
    return sha256_bytes(rendered.encode())


class MPSMemoryMonitor:
    """Record allocator behavior and periodically release reusable MPS blocks."""

    def __init__(self, every: int):
        self.every = every
        self.samples: list[dict] = []
        self.optimizer_class = None

    def on_step_end(self, args, state, control, optimizer=None, **kwargs):
        import torch

        if optimizer is not None:
            observed = optimizer
            wrappers = [observed.__class__.__name__]
            while hasattr(observed, "optimizer"):
                observed = observed.optimizer
                wrappers.append(observed.__class__.__name__)
            self.optimizer_class = " -> ".join(wrappers)
        if not torch.backends.mps.is_available():
            return control
        sample = {
            "step": int(state.global_step),
            "current_allocated_gib": round(torch.mps.current_allocated_memory() / 1024**3, 4),
            "driver_allocated_gib": round(torch.mps.driver_allocated_memory() / 1024**3, 4),
        }
        self.samples.append(sample)
        if self.every > 0 and state.global_step % self.every == 0:
            torch.mps.empty_cache()
            sample["driver_after_empty_cache_gib"] = round(
                torch.mps.driver_allocated_memory() / 1024**3, 4
            )
        return control

    def __getattr__(self, name):
        if name.startswith("on_"):
            return lambda *args, **kwargs: kwargs.get("control")
        raise AttributeError(name)


def evaluate(model, rows: list[dict[str, str]]) -> dict:
    from sklearn.metrics import accuracy_score, classification_report, f1_score

    texts = [row["text"] for row in rows]
    truth = [row["category_code"] for row in rows]
    probabilities = np.asarray(model.predict_proba(texts))
    classes = list(model.labels)
    ranked = np.argsort(-probabilities, axis=1)
    predictions = [classes[index] for index in ranked[:, 0]]
    top3 = [[classes[index] for index in indices[:3]] for indices in ranked]
    report = classification_report(truth, predictions, output_dict=True, zero_division=0)
    income_indices = [i for i, label in enumerate(truth) if label.startswith("ING-")]
    return {
        "validation_rows": len(rows),
        "accuracy": round(float(accuracy_score(truth, predictions)), 4),
        "macro_f1": round(float(f1_score(truth, predictions, average="macro", zero_division=0)), 4),
        "top3_accuracy": round(float(np.mean([t in p for t, p in zip(truth, top3)])), 4),
        "income": {
            "rows": len(income_indices),
            "accuracy": round(float(np.mean([truth[i] == predictions[i] for i in income_indices])), 4)
            if income_indices else None,
            "top3_accuracy": round(float(np.mean([truth[i] in top3[i] for i in income_indices])), 4)
            if income_indices else None,
        },
        "per_class": {
            label: {
                "precision": round(values["precision"], 4),
                "recall": round(values["recall"], 4),
                "f1": round(values["f1-score"], 4),
                "support": int(values["support"]),
            }
            for label, values in report.items()
            if label not in {"accuracy", "macro avg", "weighted avg"}
        },
    }


def resolve_device(requested: str) -> str:
    import torch

    if requested != "auto":
        if requested == "mps" and not torch.backends.mps.is_available():
            raise RuntimeError("--device mps requested but MPS is unavailable")
        return requested
    return "mps" if torch.backends.mps.is_available() else "cpu"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--split-manifest", type=Path, default=DEFAULT_SPLIT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--initial-model",
        type=Path,
        help="Continue full-encoder training from a local SetFit candidate instead of the cached base model.",
    )
    parser.add_argument("--device", choices=["auto", "mps", "cpu"], default="auto")
    parser.add_argument("--optimizer", choices=["adafactor", "adamw_torch"], default="adamw_torch")
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument(
        "--max-steps",
        type=int,
        default=1500,
        help="SetFit embedding steps; 1500 matches the v1.1 training budget",
    )
    parser.add_argument("--empty-cache-every", type=int, default=10)
    parser.add_argument(
        "--dynamic-padding",
        action="store_true",
        help="use per-batch sequence lengths; disabled by default because MPS caches a graph per shape",
    )
    parser.add_argument("--no-gradient-checkpointing", action="store_true")
    parser.add_argument("--overwrite-split", action="store_true")
    parser.add_argument("--overwrite-output", action="store_true")
    parser.add_argument("--memory-smoke", action="store_true")
    parser.add_argument("--smoke-report", type=Path, default=DEFAULT_SMOKE_REPORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.memory_smoke and args.max_steps > 30:
        raise SystemExit("--memory-smoke requires --max-steps <= 30")
    if args.output.exists() and not args.memory_smoke and not args.overwrite_output:
        raise SystemExit(f"refusing to overwrite {args.output}; choose a new path")

    random.seed(SEED)
    np.random.seed(SEED)
    # This recovery is intentionally local-only. Resolve the already cached
    # base snapshot before SentenceTransformer is constructed; passing the hub
    # id with local_files_only still triggered metadata HEAD retries in the
    # installed SetFit/SentenceTransformers combination.
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    from huggingface_hub import snapshot_download

    base_model_path = snapshot_download(BASE_MODEL, local_files_only=True)
    import torch
    from datasets import Dataset
    # SetFit 1.1.x still imports this helper from its Transformers 4.x
    # location. Transformers 5 moved it to integration_utils. Keep the shim
    # local to this training process; no site-package or global environment is
    # modified.
    import transformers.training_args as transformers_training_args
    if not hasattr(transformers_training_args, "default_logdir"):
        from transformers.integrations.integration_utils import default_logdir
        transformers_training_args.default_logdir = default_logdir
    from setfit import SetFitModel, Trainer, TrainingArguments
    from transformers.training_args import OptimizerNames

    torch.manual_seed(SEED)
    device = resolve_device(args.device)
    if device == "mps" and os.environ.get("PYTORCH_MPS_HIGH_WATERMARK_RATIO") == "0.0":
        raise SystemExit(
            "refusing unbounded MPS watermark; unset PYTORCH_MPS_HIGH_WATERMARK_RATIO"
        )

    rows, data_audit = load_and_collapse(args.gold)
    train_rows, validation_rows, excluded_rows = deterministic_split(rows)
    split_sha256 = write_or_verify_split(
        args.split_manifest,
        train_rows + validation_rows + excluded_rows,
        sha256_file(args.gold),
        args.overwrite_split,
    )

    train_counts = Counter(row["category_code"] for row in train_rows)
    validation_counts = Counter(row["category_code"] for row in validation_rows)
    weak_classes = sorted(label for label, count in train_counts.items() if count < 5)
    excluded_classes = sorted({row["category_code"] for row in excluded_rows})
    print(
        f"data: source={data_audit['source_rows']} distinct={len(rows)} "
        f"train={len(train_rows)} validation={len(validation_rows)}"
    )
    print(f"weak train-only classes: {weak_classes}")
    print(f"excluded <2 classes: {excluded_classes}")

    labels = sorted(train_counts)
    initial_model = args.initial_model.resolve() if args.initial_model else base_model_path
    model = SetFitModel.from_pretrained(
        str(initial_model),
        labels=labels,
        head_params={"class_weight": "balanced", "max_iter": 2000},
        local_files_only=True,
    )
    model.model_body.max_seq_length = 64
    model.to(device)

    auto_model = model.model_body[0].auto_model
    if not args.no_gradient_checkpointing:
        auto_model.gradient_checkpointing_enable()
        auto_model.config.use_cache = False

    token_embeddings = auto_model.embeddings.word_embeddings.weight
    if not token_embeddings.requires_grad:
        raise RuntimeError("token embeddings are frozen; full SetFit training is required")
    trainable_parameters = sum(p.numel() for p in auto_model.parameters() if p.requires_grad)
    total_parameters = sum(p.numel() for p in auto_model.parameters())
    if trainable_parameters != total_parameters:
        raise RuntimeError(
            f"encoder is partly frozen: {trainable_parameters:,}/{total_parameters:,} trainable"
        )

    tokenizer = model.model_body.tokenizer
    tracked_ids = sorted({
        token_id
        for row in train_rows[:64]
        for token_id in tokenizer(row["text"], truncation=True, max_length=64)["input_ids"]
    })[:128]
    before_embeddings = token_embeddings[tracked_ids].detach().cpu().clone()

    train_dataset = Dataset.from_dict({
        "text": [row["text"] for row in train_rows],
        "label": [row["category_code"] for row in train_rows],
    })
    training_args = TrainingArguments(
        output_dir=str(ROOT / "models/_checkpoints_recovery_v1_3_1"),
        batch_size=args.batch_size,
        num_epochs=1,
        body_learning_rate=2e-5,
        sampling_strategy="oversampling",
        max_steps=args.max_steps,
        seed=SEED,
        save_strategy="no",
        report_to="none",
        logging_steps=10,
    )
    trainer = Trainer(model=model, args=training_args, train_dataset=train_dataset)
    trainer.st_trainer.args.optim = OptimizerNames(args.optimizer)
    if not args.dynamic_padding:
        transformer_module = model.model_body._first_module()
        trainer.st_trainer.data_collator.tokenize_fn = (
            lambda texts: transformer_module.tokenize(texts, padding="max_length")
        )
    monitor = MPSMemoryMonitor(args.empty_cache_every)
    trainer.add_callback(monitor)

    started = time.time()
    trainer.train()
    elapsed_minutes = round((time.time() - started) / 60, 2)
    after_embeddings = token_embeddings[tracked_ids].detach().cpu()
    embedding_delta = float(torch.max(torch.abs(after_embeddings - before_embeddings)))
    if embedding_delta == 0.0:
        raise RuntimeError("tracked token embeddings did not change during training")

    run = {
        "mode": "memory_smoke" if args.memory_smoke else "candidate_training",
        "base_model": BASE_MODEL,
        "base_model_local_snapshot": str(base_model_path),
        "initial_model": str(initial_model),
        "device": device,
        "optimizer_requested": args.optimizer,
        "optimizer_observed": monitor.optimizer_class,
        "full_encoder_trainable": True,
        "trainable_encoder_parameters": trainable_parameters,
        "total_encoder_parameters": total_parameters,
        "tracked_token_embedding_max_abs_delta": embedding_delta,
        "gradient_checkpointing": not args.no_gradient_checkpointing,
        "fixed_length_padding": not args.dynamic_padding,
        "unbounded_mps_watermark": False,
        "transaction_type_in_model_input": True,
        "model_input_template": "[transaction_type] | item_text | description | provider",
        "batch_size": args.batch_size,
        "max_steps": args.max_steps,
        "elapsed_minutes": elapsed_minutes,
        "data_audit": data_audit,
        "train_rows": len(train_rows),
        "validation_rows": len(validation_rows),
        "train_class_counts": dict(sorted(train_counts.items())),
        "validation_class_counts": dict(sorted(validation_counts.items())),
        "weak_train_only_classes": weak_classes,
        "excluded_lt2_classes": excluded_classes,
        "gold_sha256": sha256_file(args.gold),
        "split_sha256": split_sha256,
        "mps_memory_samples": monitor.samples,
    }

    if args.memory_smoke:
        args.smoke_report.parent.mkdir(parents=True, exist_ok=True)
        args.smoke_report.write_text(json.dumps(run, indent=2) + "\n")
        print(json.dumps({
            "optimizer": monitor.optimizer_class,
            "embedding_delta": embedding_delta,
            "steps": args.max_steps,
            "elapsed_minutes": elapsed_minutes,
            "report": str(args.smoke_report),
        }, indent=2))
        return

    run["metrics"] = evaluate(model, validation_rows)
    if args.output.exists() and args.overwrite_output:
        # Deliberately avoid recursive deletion. SetFit can replace individual
        # files in an explicitly selected candidate directory, while baseline
        # paths remain protected by the distinct default name.
        if args.output.resolve() in {
            (ROOT / "models/setfit_base").resolve(),
            (ROOT / "artifacts/v1.1.0").resolve(),
        }:
            raise RuntimeError("refusing to overwrite a protected v1.1 path")
    args.output.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(args.output))
    (args.output / "run_manifest.json").write_text(json.dumps(run, indent=2) + "\n")
    print(json.dumps(run["metrics"], indent=2))
    print(f"saved local candidate: {args.output}")


if __name__ == "__main__":
    main()
