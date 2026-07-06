from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from app.inference.normalize import normalize_text


@dataclass(frozen=True)
class LookupHit:
    category_code: str
    rule_source: str
    matched_key: str


class ProductLookup:
    def __init__(self, path: Path):
        self.path = path
        self.entries: dict[tuple[str, str], LookupHit] = {}
        if path.exists():
            self._load(path)

    @property
    def enabled(self) -> bool:
        return bool(self.entries)

    def _load(self, path: Path) -> None:
        with open(path, newline="") as handle:
            for row in csv.DictReader(handle):
                text = normalize_text(row.get("item_text", ""))
                provider = normalize_text(row.get("provider", ""))
                code = row.get("category_code", "").strip()
                if text and code:
                    hit = LookupHit(code, row.get("rule_source", "client_rule"), text)
                    self.entries[(text, provider)] = hit
                    self.entries.setdefault((text, ""), hit)

    def match(self, item_text: str, provider: str = "") -> LookupHit | None:
        text = normalize_text(item_text)
        prov = normalize_text(provider)
        return self.entries.get((text, prov)) or self.entries.get((text, ""))

    def info(self) -> dict:
        unique_keys = {hit.matched_key for hit in self.entries.values()}
        return {
            "enabled": self.enabled,
            "path": str(self.path),
            "entries": len(unique_keys),
        }
