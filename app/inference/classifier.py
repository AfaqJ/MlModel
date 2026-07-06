from __future__ import annotations

from pathlib import Path
import warnings
import joblib
import numpy as np


class LogisticHead:
    def __init__(self, artifact_dir: Path):
        self.model = joblib.load(artifact_dir / "classifier.joblib")
        self.classes_ = list(self.model.classes_)

    def predict_proba(self, embeddings: np.ndarray) -> np.ndarray:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=RuntimeWarning, module="sklearn")
            return self.model.predict_proba(embeddings)
