from __future__ import annotations

import json
from pathlib import Path
from app.inference.classifier import LogisticHead
from app.inference.onnx_encoder import OnnxEncoder
from app.inference.product_lookup import ProductLookup
from app.inference.meter_lookup import MeterLookup
from app.inference.business_rules import BusinessRules


class ModelBundle:
    def __init__(self, artifact_dir: Path, product_lookup_path: Path, meter_lookup_path: Path | None = None,
                 business_rules_path: Path | None = None):
        self.artifact_dir = artifact_dir
        self.model_card = json.loads((artifact_dir / "model_card.json").read_text())
        self.labels = json.loads((artifact_dir / "labels.json").read_text())
        self.encoder = OnnxEncoder(artifact_dir)
        self.head = LogisticHead(artifact_dir)
        self.lookup = ProductLookup(product_lookup_path)
        self.meter_lookup = MeterLookup(meter_lookup_path) if meter_lookup_path else MeterLookup(Path("__none__"))
        default_rules = product_lookup_path.parent / "business_rules.csv"
        self.business_rules = BusinessRules(business_rules_path or default_rules)
        required_lookups = {
            "product_lookup": self.lookup.enabled,
            "meter_lookup": self.meter_lookup.enabled,
            "business_rules": self.business_rules.enabled,
        }
        missing = [name for name, enabled in required_lookups.items() if not enabled]
        if missing:
            raise RuntimeError(f"required deterministic lookup missing or empty: {', '.join(missing)}")
        self.names = {row["code"]: row["name"] for row in self.labels["labels"]}
        self.weak_classes = {row["code"] for row in self.labels["labels"] if row["weak"]}

    @property
    def model_version(self) -> str:
        return self.model_card["model_version"]

    @property
    def thresholds(self) -> dict:
        return self.model_card["thresholds"]

    def info(self) -> dict:
        return {
            "model_version": self.model_version,
            "base_model": self.model_card["base_model"],
            "artifact_format": self.model_card["artifact_format"],
            "trained_date": self.model_card["trained_date"],
            "num_trained_classes": self.model_card["trained_classes"],
            "thresholds": self.thresholds,
            "product_lookup": self.lookup.info(),
            "meter_lookup": self.meter_lookup.info(),
            "business_rules": self.business_rules.info(),
            "artifacts_sha256": self.model_card.get("artifacts_sha256", {}),
        }
