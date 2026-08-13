"""Known semantic ambiguities that confidence alone cannot resolve.

Deliberately free of product vocabulary. An earlier v1.3.2 build carried ten
Spanish word lists here (food terms, hardware terms, transport verbs, bank fee
phrases) tuned to one batch of invoices. They worked on that batch and would
have rotted on the next: word lists cannot anticipate the vocabulary of data
they have not seen, and the same word means different things in different
contexts. Batch-specific corrections belong in the batch data, not in the
deployed decision path.

What is left is either structural (holds for any language and any vocabulary)
or a v1.3.1 rule about a distinction that genuinely cannot be made from text —
electricity needs the meter, glove taxonomy conflicts with the client examples.
"""
from __future__ import annotations

import re
import unicodedata


def _normalize(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", (value or "").lower())
    value = value.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _has_readable_word(text: str) -> bool:
    """True when some token carries at least three letters.

    Structural, not lexical: an item named `61891841` or `G93` gives a text
    classifier nothing to work with, so whatever it predicts came from the
    provider instead. In the v1.3.2 raw replay those rows were auto-accepted at
    0.75-0.79 — insurer policy numbers became machinery maintenance. The
    description is included because a meaningful description can legitimately
    carry a row whose name is a bare code.

    A row the client has actually labelled is unaffected: batch backfill applies
    client evidence over this gate, because proof outranks a heuristic.
    """
    return any(len(re.sub(r"[^a-z]", "", token)) >= 3 for token in _normalize(text).split())


def model_review_guard_reason(
    item_text: str,
    description: str = "",
    predicted_code: str | None = None,
) -> str | None:
    """Return why a model-only result must be reviewed despite confidence.

    Exact taxonomy, product, and meter lookups are resolved before this guard.
    These cases need information absent from free text, so confidence is not
    evidence that the missing distinction was resolved correctly.
    """
    text = _normalize(f"{item_text} {description}")
    item = _normalize(item_text)
    if not _has_readable_word(f"{item_text} {description}"):
        return "item_name_carries_no_classifiable_text"
    if "revision tecnica" in text:
        return "ambiguous_vehicle_vs_machinery_inspection"
    if item in {"item", "servicio", "mano de obra", "traslado"}:
        return "generic_item_name_requires_review"
    if item.startswith("aplicacion fertilizante"):
        return "fertilizer_type_requires_review"
    if re.search(r"\bguantes?\b", text):
        return "client_examples_conflict_with_glove_taxonomy"
    irrigation_terms = ("riego", "pibote", "pivote", "irripod")
    if (
        predicted_code
        and any(term in text for term in irrigation_terms)
        and predicted_code not in {"EXP-9.1", "EXP-9.2"}
    ):
        return "irrigation_context_conflicts_with_prediction"
    electricity_terms = ("electricidad", "electrica", "electrico", "energia")
    if any(term in text for term in electricity_terms):
        return "electricity_requires_exact_meter_or_lookup"
    return None
