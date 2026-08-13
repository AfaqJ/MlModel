"""Nearest-neighbour familiarity gate for model-only predictions.

The v1.3.1 raw replay showed that SetFit confidence is not a probability. With
~1,300 training rows spread over 67 classes the logistic head is a closed-set
classifier: every input must be assigned to some class, so an item unlike
anything in training is still placed somewhere, often with high confidence.
Biscuits were filed as office supplies at 0.63 and a waist bag as food at a
comfortable margin. Raising the acceptance threshold cannot separate those
from the many correct high-confidence rows.

This gate answers a different question, which confidence cannot: *has the model
ever seen anything like this in the class it just chose?* It compares the row's
embedding against the stored training embeddings and measures how many of the
nearest neighbours carry the predicted label. Low agreement means the head
extrapolated, so the row goes to review.

The gate only ever downgrades a model auto-accept to review. It never assigns a
label, never overrides a deterministic lookup, and never promotes anything.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

INDEX_FILENAME = "familiarity_index.npz"
REVIEW_REASON = "unfamiliar_for_predicted_class"


def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.clip(norms, 1e-12, None)


@dataclass(frozen=True)
class FamiliarityVerdict:
    agreement: float
    nearest_label: str
    nearest_similarity: float


class FamiliarityIndex:
    """Cosine kNN over the training embeddings, keyed by training label."""

    def __init__(
        self,
        embeddings: np.ndarray,
        labels: np.ndarray,
        k: int,
        min_agreement: float,
    ):
        if len(embeddings) != len(labels):
            raise ValueError("familiarity index embeddings and labels differ in length")
        if not embeddings.size:
            raise ValueError("familiarity index is empty")
        self.embeddings = _normalize_rows(embeddings)
        self.labels = np.asarray(labels, dtype=object)
        self.k = int(k)
        self.min_agreement = float(min_agreement)

    @classmethod
    def load(cls, artifact_dir: Path) -> "FamiliarityIndex | None":
        path = Path(artifact_dir) / INDEX_FILENAME
        if not path.exists():
            return None
        with np.load(path, allow_pickle=False) as data:
            return cls(
                embeddings=data["embeddings"],
                labels=np.asarray([str(value) for value in data["labels"]], dtype=object),
                k=int(data["k"]),
                min_agreement=float(data["min_agreement"]),
            )

    def save(self, artifact_dir: Path) -> Path:
        path = Path(artifact_dir) / INDEX_FILENAME
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            # float16 halves the artifact size; the gate compares neighbour
            # ranks and a fractional agreement, neither of which is sensitive
            # to the last few bits of a cosine similarity.
            embeddings=self.embeddings.astype(np.float16),
            labels=np.asarray([str(value) for value in self.labels]),
            k=np.int32(self.k),
            min_agreement=np.float32(self.min_agreement),
        )
        return path

    def evaluate(self, embedding: np.ndarray, predicted_code: str) -> FamiliarityVerdict:
        vector = np.asarray(embedding, dtype=np.float32).reshape(-1)
        vector = vector / max(float(np.linalg.norm(vector)), 1e-12)
        similarities = self.embeddings @ vector
        k = min(self.k, len(similarities))
        top = np.argpartition(-similarities, k - 1)[:k]
        top = top[np.argsort(-similarities[top])]
        neighbour_labels = self.labels[top]
        return FamiliarityVerdict(
            agreement=float(np.mean(neighbour_labels == predicted_code)),
            nearest_label=str(neighbour_labels[0]),
            nearest_similarity=float(similarities[top[0]]),
        )

    def review_reason(self, embedding: np.ndarray, predicted_code: str) -> str | None:
        """Return the review reason when the prediction is unsupported, else None."""
        verdict = self.evaluate(embedding, predicted_code)
        return REVIEW_REASON if verdict.agreement < self.min_agreement else None

    def info(self) -> dict:
        return {
            "enabled": True,
            "rows": int(len(self.labels)),
            "k": self.k,
            "min_agreement": self.min_agreement,
        }
