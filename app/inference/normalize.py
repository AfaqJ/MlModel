from __future__ import annotations

import re
import unicodedata


PUNCT_RE = re.compile(r"[^A-Z0-9\- ]+")
SPACE_RE = re.compile(r"\s+")
UNIT_REPLACEMENTS = (
    (re.compile(r"\b(LTS?|LITROS?)\b"), "L"),
    (re.compile(r"\b(KGS?|KILOS?)\b"), "KG"),
    (re.compile(r"\b(CC)\b"), "ML"),
)


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def normalize_text(value: str) -> str:
    text = strip_accents(value or "").upper()
    for pattern, replacement in UNIT_REPLACEMENTS:
        text = pattern.sub(replacement, text)
    text = PUNCT_RE.sub(" ", text)
    return SPACE_RE.sub(" ", text).strip()
