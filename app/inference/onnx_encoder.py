from __future__ import annotations

import os
from pathlib import Path
import numpy as np
import onnxruntime as ort

os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

from transformers import AutoTokenizer
import json


class OnnxEncoder:
    def __init__(self, artifact_dir: Path, max_length: int | None = None):
        card = json.loads((artifact_dir / "model_card.json").read_text())
        self.max_length = max_length or int(card["input_construction"]["max_length"])
        self.tokenizer = AutoTokenizer.from_pretrained(
            str(artifact_dir / "tokenizer"),
            # This is XLM-R, not Mistral. Transformers 4.57 emits a false
            # detector warning; enabling the Mistral rewrite changes the
            # tokenizer and breaks parity with training.
            fix_mistral_regex=False,
        )
        self.session = ort.InferenceSession(
            str(artifact_dir / "model.onnx"),
            providers=["CPUExecutionProvider"],
        )
        self.input_names = {item.name for item in self.session.get_inputs()}

    def embed(self, texts: list[str], batch_size: int = 64) -> np.ndarray:
        batches: list[np.ndarray] = []
        for start in range(0, len(texts), batch_size):
            enc = self.tokenizer(
                texts[start : start + batch_size],
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="np",
            )
            feed = {key: value for key, value in enc.items() if key in self.input_names}
            hidden = self.session.run(None, feed)[0]
            mask = enc["attention_mask"][..., None].astype(np.float32)
            pooled = (hidden * mask).sum(1) / np.clip(mask.sum(1), 1e-9, None)
            batches.append(pooled)
        return np.vstack(batches)
