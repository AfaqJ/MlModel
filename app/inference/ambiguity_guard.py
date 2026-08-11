"""Known semantic ambiguities that confidence alone cannot resolve."""
from __future__ import annotations

import re
import unicodedata


def _normalize(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", (value or "").lower())
    value = value.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def model_review_guard_reason(item_text: str, description: str = "") -> str | None:
    """Return why a model-only result must be reviewed despite confidence.

    Exact taxonomy, product, and meter lookups are resolved before this guard.
    These cases need information absent from free text, so confidence is not
    evidence that the missing distinction was resolved correctly.
    """
    text = _normalize(f"{item_text} {description}")
    if "revision tecnica" in text:
        return "ambiguous_vehicle_vs_machinery_inspection"
    if _normalize(item_text) in {"item", "servicio", "mano de obra", "traslado"}:
        return "generic_item_name_requires_review"
    if _normalize(item_text).startswith("aplicacion fertilizante"):
        return "fertilizer_type_requires_review"
    if re.search(r"\bguantes?\b", text):
        return "client_examples_conflict_with_glove_taxonomy"
    electricity_terms = ("electricidad", "electrica", "electrico", "energia")
    if any(term in text for term in electricity_terms):
        return "electricity_requires_exact_meter_or_lookup"
    return None
