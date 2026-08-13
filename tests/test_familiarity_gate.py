import numpy as np
import pytest

from app.inference.familiarity import REVIEW_REASON, FamiliarityIndex


def build_index(k=3, min_agreement=0.6):
    # Two well-separated training clusters, so "near" and "far" are unambiguous.
    embeddings = np.array([
        [1.0, 0.0, 0.0],
        [0.99, 0.1, 0.0],
        [0.98, 0.2, 0.0],
        [0.0, 1.0, 0.0],
        [0.1, 0.99, 0.0],
        [0.2, 0.98, 0.0],
    ])
    labels = np.array(["ADM-1.6", "ADM-1.6", "ADM-1.6", "EXP-7.0", "EXP-7.0", "EXP-7.0"], dtype=object)
    return FamiliarityIndex(embeddings, labels, k=k, min_agreement=min_agreement)


def test_supported_prediction_passes():
    index = build_index()
    assert index.review_reason(np.array([1.0, 0.05, 0.0]), "ADM-1.6") is None


def test_prediction_unsupported_by_neighbours_is_reviewed():
    """The v1.3.1 failure shape: high confidence, no nearby example of that class."""
    index = build_index()
    assert index.review_reason(np.array([1.0, 0.05, 0.0]), "EXP-7.0") == REVIEW_REASON


def test_row_far_from_everything_is_reviewed_for_either_class():
    index = build_index()
    far = np.array([0.0, 0.0, 1.0])
    # Ties are broken by whichever cluster happens to be nearer, so at least
    # one of the two classes must be rejected; a row unlike all training data
    # must never be supported for both.
    reasons = [index.review_reason(far, code) for code in ("ADM-1.6", "EXP-7.0")]
    assert REVIEW_REASON in reasons


def test_agreement_is_the_neighbour_label_fraction():
    index = build_index(k=6)
    verdict = index.evaluate(np.array([1.0, 0.0, 0.0]), "ADM-1.6")
    assert verdict.agreement == pytest.approx(0.5)
    assert verdict.nearest_label == "ADM-1.6"


def test_roundtrip_preserves_decisions(tmp_path):
    index = build_index()
    index.save(tmp_path)
    reloaded = FamiliarityIndex.load(tmp_path)
    assert reloaded is not None
    assert reloaded.k == index.k
    assert reloaded.min_agreement == pytest.approx(index.min_agreement)
    probe = np.array([1.0, 0.05, 0.0])
    assert reloaded.review_reason(probe, "EXP-7.0") == index.review_reason(probe, "EXP-7.0")


def test_missing_index_is_absent_not_an_error(tmp_path):
    assert FamiliarityIndex.load(tmp_path) is None
