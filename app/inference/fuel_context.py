"""Deterministic petrol classification from the DTE transport field."""
from __future__ import annotations

from dataclasses import dataclass

from app.inference.normalize import normalize_text


# Values retained as settled after the 2026-08-17 client review. A value that
# merely resembles a plate is not enough: D-033 leaves unknown values in review.
KNOWN_VEHICLE_PLATES = {
    "DJXC64", "DY0000", "EA123", "JSFK23", "JTXC63", "KK3471", "NNNN00", "PBZL91",
    "PKSR82", "PKSR92", "RDYC23", "SPPU51", "SPPU52", "SPPU53", "SPPU54",
    "PSSS88", "SHZW36", "SWPT40", "TBFK28", "TBZK91", "TBZL91", "TJKC63",
    "TJXC63", "TJXC64", "TJXE63", "TJXE64", "TYLD93", "TYSZ10",
}

KNOWN_BIDON_VALUES = {
    "BIDON", "BID000", "BIDI25", "BIDO2", "BIDO11", "BIDO15", "BIDO16",
    "BIDO01", "BIDO28", "BIDO32", "BIDO45", "BIDO54", "BIDO63", "BIDO65", "BIDO85",
    "BIDO91", "BIDO93", "BIOD45", "IBDO96", "VIDO93",
}

PETROL_NAMES = {
    "GASOLINA 93",
    "G93",
    "93 S P",
    "GASOLINA 93 OCTANOS SIN PLOMO",
    "GASOLINA 95",
    "GASOLINA 95 OCTANOS",
    "V-POWER 97",
    "ARAMCO GASOLINA 93",
}


@dataclass(frozen=True)
class FuelContext:
    category_code: str | None
    reason: str
    signal: str


def _field(value: str | None) -> str:
    return "".join(character for character in normalize_text(value or "") if character.isalnum())


def petrol_context(
    item_text: str,
    description: str,
    transport_plate: str | None,
    transaction_type: str | None,
) -> FuelContext | None:
    """Return the client's petrol rule, or None when this is not petrol."""
    if (transaction_type or "").upper() != "COMPRAS":
        return None

    item = normalize_text(item_text)
    petrol = item in PETROL_NAMES or (
        item == "DETALLE" and "GASOLINA" in normalize_text(description)
    )
    if not petrol:
        return None

    plate = _field(transport_plate)
    if plate in KNOWN_BIDON_VALUES:
        return FuelContext("EXP-11.4", "petrol_known_bidon", "bidon")
    if plate in KNOWN_VEHICLE_PLATES:
        return FuelContext("ADM-1.4", "petrol_known_vehicle_plate", "vehicle_plate")
    return FuelContext(None, "petrol_transport_signal_requires_review", "unresolved")
