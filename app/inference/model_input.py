from __future__ import annotations

import re


NUMERIC_RE = re.compile(r"[\d\s.,\-/]+$")
VALID_TRANSACTION_TYPES = {"COMPRAS", "VENTAS"}


def clean_description(value: str | None) -> str:
    """Drop numeric-only product codes, which carry no language semantics."""
    value = (value or "").strip()
    return "" if not value or NUMERIC_RE.fullmatch(value) else value


def normalize_transaction_type(value: str | None) -> str:
    direction = (value or "").strip().upper()
    if direction not in VALID_TRANSACTION_TYPES:
        raise ValueError("transaction_type must be COMPRAS or VENTAS")
    return direction


def build_model_text(
    item_text: str,
    description: str = "",
    provider: str = "",
    transaction_type: str | None = None,
) -> str:
    """Build the one canonical string shared by training and inference.

    The DTE source direction is deliberately the first token. It lets the
    encoder learn that identical words can mean different things on incoming
    purchases and outgoing sales, while deterministic direction masks remain
    the final fail-safe.
    """
    direction = normalize_transaction_type(transaction_type)
    parts = [
        f"[{direction}]",
        (item_text or "").strip(),
        clean_description(description),
        (provider or "").strip(),
    ]
    return " | ".join(part for part in parts if part)
