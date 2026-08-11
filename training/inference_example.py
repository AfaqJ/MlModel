"""MCT-37 — Standalone inference example for the deployment package.

Shows EXACTLY how production must run the model. Dependencies:
    pip install onnxruntime numpy scikit-learn joblib tokenizers transformers
(no PyTorch, no sentence-transformers, no setfit)

Run from inside an artifacts/<version>/ directory:
    python inference_example.py "VACUNA CLOSTRIBAC 8 GOLD X 50 DOS." --provider COOPRINSEM
"""
from __future__ import annotations
import argparse, csv, json, re
from pathlib import Path

import joblib
import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

HERE = Path(__file__).resolve().parent
NUMERIC_RE = re.compile(r"[\d\s.,\-/]+$")
class Classifier:
    def __init__(self, artifact_dir: Path = HERE):
        card = json.loads((artifact_dir / "model_card.json").read_text())
        self.card = card
        self.thresholds = card["thresholds"]
        self.max_length = int(card["input_construction"]["max_length"])
        self.tokenizer = AutoTokenizer.from_pretrained(str(artifact_dir / "tokenizer"),
                                                       fix_mistral_regex=False)
        self.session = ort.InferenceSession(str(artifact_dir / "model.onnx"),
                                            providers=["CPUExecutionProvider"])
        self.input_names = {i.name for i in self.session.get_inputs()}
        self.head = joblib.load(artifact_dir / "classifier.joblib")
        labels = json.loads((artifact_dir / "labels.json").read_text())
        self.names = {l["code"]: l["name"] for l in labels["labels"]}
        self.weak = {l["code"] for l in labels["labels"] if l["weak"]}
    def build_text(self, item_text: str, transaction_type: str,
                   description: str = "", provider: str = "") -> str:
        direction = transaction_type.strip().upper()
        if direction not in {"COMPRAS", "VENTAS"}:
            raise ValueError("transaction_type must be COMPRAS or VENTAS")
        d = (description or "").strip()
        if NUMERIC_RE.fullmatch(d or "0"):
            d = ""  # numeric-only descriptions are product codes — no semantics
        parts = [f"[{direction}]", item_text.strip(), d, (provider or "").strip()]
        return " | ".join(p for p in parts if p)

    def embed(self, texts: list[str], batch_size: int = 64) -> np.ndarray:
        out = []
        for i in range(0, len(texts), batch_size):
            enc = self.tokenizer(texts[i:i + batch_size], padding=True, truncation=True,
                                 max_length=self.max_length, return_tensors="np")
            feed = {k: v for k, v in enc.items() if k in self.input_names}
            hidden = self.session.run(None, feed)[0]  # last_hidden_state
            mask = enc["attention_mask"][..., None].astype(np.float32)
            out.append((hidden * mask).sum(1) / np.clip(mask.sum(1), 1e-9, None))  # mean pool, NO L2 norm
        return np.vstack(out)

    def predict(self, item_text: str, transaction_type: str,
                description: str = "", provider: str = "", top_k: int = 3) -> dict:
        text = self.build_text(item_text, transaction_type, description, provider)
        proba = self.head.predict_proba(self.embed([text]))[0]
        order = np.argsort(-proba)[:top_k]
        classes = self.head.classes_
        preds = [{"code": classes[i], "name": self.names.get(classes[i], ""),
                  "score": round(float(proba[i]), 4)} for i in order]
        top1, top2 = float(proba[order[0]]), float(proba[order[1]])
        code1 = classes[order[0]]
        t = self.thresholds
        if code1 in self.weak:
            decision, reason = "review_required", "weak_class"
        elif top1 < t["accept_top1"]:
            decision, reason = "review_required", "low_confidence"
        elif top1 - top2 < t["accept_margin"]:
            decision, reason = "review_required", "small_margin"
        elif t.get("model_auto_accept") is False:
            decision, reason = "review_required", "model_unseen_input"
        else:
            decision, reason = "auto_accept", None
        return {"predictions": preds, "confidence": {"top1": round(top1, 4),
                "margin": round(top1 - top2, 4)}, "decision": decision, "reason": reason,
                "model_version": self.card["model_version"]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("item_text")
    ap.add_argument("--transaction-type", choices=["COMPRAS", "VENTAS"], required=True)
    ap.add_argument("--description", default="")
    ap.add_argument("--provider", default="")
    a = ap.parse_args()
    clf = Classifier()
    print(json.dumps(clf.predict(a.item_text, a.transaction_type, a.description, a.provider),
                     indent=2, ensure_ascii=False))
