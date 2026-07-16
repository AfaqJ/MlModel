from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path


# Meter codes arrive in slightly different shapes across utilities: the SII DTE
# writes them with a dot (CdgIntRecep "6365.01") while the client sheet lists the
# same meter as "636501". Strip everything that isn't alphanumeric so both forms
# collapse to the same key.
_METER_NORM_RE = re.compile(r"[^0-9A-Za-z]+")


def normalize_meter(value: str) -> str:
    return _METER_NORM_RE.sub("", value or "").upper()


@dataclass(frozen=True)
class MeterHit:
    category_code: str
    meter_code: str
    provider: str
    farm: str


class MeterLookup:
    """Deterministic electricity meter -> category lookup.

    Built from the client's `Servicios Electricos` sheet. Electricity invoices
    carry the meter in the DTE `<CdgIntRecep>` field; that value alone fixes the
    category (dairy shed / houses / irrigation), so no ML inference is needed.
    """

    def __init__(self, path: Path):
        self.path = path
        self.entries: dict[str, MeterHit] = {}
        if path.exists():
            self._load(path)

    @property
    def enabled(self) -> bool:
        return bool(self.entries)

    def _load(self, path: Path) -> None:
        with open(path, newline="") as handle:
            for row in csv.DictReader(handle):
                key = normalize_meter(row.get("service_number", ""))
                code = (row.get("category_code") or "").strip()
                if key and code:
                    self.entries[key] = MeterHit(
                        category_code=code,
                        meter_code=(row.get("service_number") or "").strip(),
                        provider=(row.get("provider") or "").strip(),
                        farm=(row.get("farm") or "").strip(),
                    )

    def match(self, meter_code: str) -> MeterHit | None:
        return self.entries.get(normalize_meter(meter_code))

    def info(self) -> dict:
        return {
            "enabled": self.enabled,
            "path": str(self.path),
            "entries": len(self.entries),
        }
