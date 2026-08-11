from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from app.api.schemas import PredictRequest
from app.inference.business_rules import BusinessRules
from app.inference.predictor import Predictor


RULES = Path(__file__).resolve().parents[1] / "app/data/business_rules.csv"


class NoMatch:
    def match(self, *args):
        return None


class FailIfCalledEncoder:
    def embed(self, texts):
        raise AssertionError("encoder must not run for an authoritative exact rule")


class FixedEncoder:
    def embed(self, texts):
        return np.zeros((len(texts), 2), dtype=np.float32)


class FixedHead:
    classes_ = np.asarray(["EXP-1.1", "ING-0.1"])

    def predict_proba(self, embeddings):
        return np.asarray([[0.1, 0.9] for _ in embeddings])


class Bundle:
    def __init__(self, encoder):
        self.business_rules = BusinessRules(RULES)
        self.meter_lookup = NoMatch()
        self.lookup = NoMatch()
        self.encoder = encoder
        self.head = FixedHead()
        self.names = {"EXP-1.1": "Otros Gastos RRHH", "ING-0.1": "VENTA DE LECHE"}
        self.weak_classes = set()
        self.thresholds = {"accept_top1": 0.8, "accept_margin": 0.2}
        self.model_version = "test"


def test_verified_sale_short_circuits_encoder():
    result = Predictor(Bundle(FailIfCalledEncoder())).predict(
        item_text="VENTA DE LECHE",
        transaction_type="VENTAS",
    )
    assert result["source"] == "business_rule"
    assert result["predictions"][0]["code"] == "ING-0.1"
    assert result["decision"] == "auto_accept"


def test_purchase_direction_masks_all_income_probabilities():
    result = Predictor(Bundle(FixedEncoder())).predict(
        item_text="unexpected purchase",
        transaction_type="COMPRAS",
    )
    assert result["predictions"][0]["code"] == "EXP-1.1"
    assert all(not prediction["code"].startswith("ING-") for prediction in result["predictions"])


def test_unknown_sale_is_never_auto_accepted():
    result = Predictor(Bundle(FixedEncoder())).predict(
        item_text="VENTA CAMIONETA",
        transaction_type="VENTAS",
    )
    assert result["source"] == "model"
    assert result["decision"] == "review_required"
    assert result["reason"] == "unknown_sales_item"


def test_transaction_type_rejects_unknown_values():
    with pytest.raises(ValidationError):
        PredictRequest(item_text="VENTA DE LECHE", transaction_type="sale")


def test_rules_reject_duplicate_normalized_keys(tmp_path):
    path = tmp_path / "rules.csv"
    path.write_text(
        "rule_version,transaction_type,item_text,category_code,action,note\n"
        "1,VENTAS,VENTA DE LECHE,ING-0.1,assign,a\n"
        "1,VENTAS,venta/de/leche,ING-0.2,assign,b\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate normalized key"):
        BusinessRules(path)
