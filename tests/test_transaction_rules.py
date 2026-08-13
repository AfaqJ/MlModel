from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from app.api.schemas import PredictRequest
from app.inference.business_rules import BusinessRules
from app.inference.confidence import decide
from app.inference.predictor import Predictor
from app.inference.ambiguity_guard import model_review_guard_reason


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


class AmbiguousHead:
    classes_ = np.asarray(["EXP-1.1", "EXP-2.1"])

    def predict_proba(self, embeddings):
        return np.asarray([[0.8, 0.2] for _ in embeddings])


class BoundaryHead:
    classes_ = np.asarray(["EXP-1.1", "EXP-2.1"])

    def predict_proba(self, embeddings):
        return np.asarray([[0.74996, 0.25004] for _ in embeddings])


class Bundle:
    def __init__(self, encoder, head=None):
        self.business_rules = BusinessRules(RULES)
        self.meter_lookup = NoMatch()
        self.lookup = NoMatch()
        self.encoder = encoder
        self.head = head or FixedHead()
        self.names = {
            "EXP-1.1": "Otros Gastos RRHH",
            "ING-0.1": "VENTA DE LECHE",
            "ING-0.4": "VENTA TERNEROS",
            "ING-0.6": "VENTA LEÑA",
        }
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


def test_dte43_liquidacion_is_never_auto_accepted_without_client_category():
    result = Predictor(Bundle(FixedEncoder())).predict(
        item_text="VACA ENGORDA",
        transaction_type="COMPRAS",
        invoice_metadata={"document_type": "043", "xml_document_kind": "Liquidacion"},
    )
    assert result["decision"] == "review_required"
    assert result["reason"] == "liquidacion_dte43_requires_client_category"


def test_every_sales_taxonomy_name_is_a_rule():
    """All six income leaves resolve exactly; the expense side deliberately does not.

    On sales the client writes the invoice, so an item naming a category IS the
    client naming their own category. On purchases the supplier writes it, and a
    match is a coincidence in someone else's document.
    """
    rules = BusinessRules(RULES)
    taxonomy_path = RULES.parents[2] / "Data/current_context_2026_06_30/taxonomy_from_plan.csv"
    import csv

    with taxonomy_path.open(encoding="utf-8-sig", newline="") as handle:
        taxonomy = list(csv.DictReader(handle))
    assert len(taxonomy) == 71
    sales = [row for row in taxonomy if row["new_code"].startswith("ING-")]
    assert len(sales) == 6
    for row in sales:
        hit = rules.match(row["leaf"], "VENTAS")
        assert hit is not None
        assert hit.category_code == row["new_code"]
    for row in taxonomy:
        if row["new_code"].startswith("ING-"):
            continue
        assert rules.match(row["leaf"], "COMPRAS") is None


def test_no_expense_rule_can_exist():
    """The whole table is sales-only, so no expense word can ever short-circuit."""
    rules = BusinessRules(RULES)
    assert rules.entries
    assert {direction for direction, _ in rules.entries} == {"VENTAS"}
    for _, text in rules.entries:
        assert text.startswith("VENTA"), f"non-sales key leaked into the table: {text!r}"


@pytest.mark.parametrize("bare", ["vaca", "VACA", "vacas", "VACAS", "cow", "leche",
                                  "LECHE", "terneros", "vaquillas", "leña"])
@pytest.mark.parametrize("direction", ["COMPRAS", "VENTAS"])
def test_a_bare_product_word_never_resolves(bare, direction):
    """`cow` must never mean "Cow Sales" — it could just as easily be a purchase."""
    assert BusinessRules(RULES).match(bare, direction) is None


@pytest.mark.parametrize("item_text", ["VENTA DE VACAS", "VENTA DE LECHE", "VENTAS TERNEROS"])
def test_the_same_words_never_resolve_under_the_wrong_direction(item_text):
    """An auction settlement filed under COMPRAS keeps the seller's wording."""
    rules = BusinessRules(RULES)
    assert rules.match(item_text, "VENTAS") is not None
    assert rules.match(item_text, "COMPRAS") is None


@pytest.mark.parametrize("item_text", ["VENTA DE LECHE FRESCA", "LECHE", "DE VACAS",
                                       "FACTURA VENTA DE LECHE", "VENTA"])
def test_matching_is_exact_and_never_partial(item_text):
    """Neither a superstring nor a substring of a rule key may match it."""
    assert BusinessRules(RULES).match(item_text, "VENTAS") is None


def test_a_cattle_purchase_can_never_be_labelled_as_a_sale():
    """End to end: the 103 DTE-43 auction lines must stay out of income."""
    result = Predictor(Bundle(FixedEncoder())).predict(
        item_text="VACA ENGORDA",
        description="vacas preñadas",
        transaction_type="COMPRAS",
    )
    assert result["source"] != "business_rule"
    assert all(not prediction["code"].startswith("ING-") for prediction in result["predictions"])


@pytest.mark.parametrize(
    "item_text",
    ["VENTA TERNEROS", "VENTAS TERNEROS", "VENTA DE TERNERAS", "VENTAS DE TERNERAS"],
)
def test_male_and_female_calf_aliases_share_one_category(item_text):
    hit = BusinessRules(RULES).match(item_text, "VENTAS")
    assert hit is not None
    assert hit.category_code == "ING-0.4"


def test_untrained_firewood_class_is_still_resolved_by_exact_taxonomy_rule():
    result = Predictor(Bundle(FailIfCalledEncoder())).predict(
        item_text="VENTA LEÑA",
        transaction_type="VENTAS",
    )
    assert result["source"] == "business_rule"
    assert result["predictions"][0]["code"] == "ING-0.6"


def test_transaction_type_is_first_model_token():
    predictor = Predictor(Bundle(FixedEncoder()))
    assert predictor.build_text("leña", provider="Proveedor", transaction_type="COMPRAS").startswith(
        "[COMPRAS] | leña"
    )


def test_transaction_type_rejects_unknown_values():
    with pytest.raises(ValidationError):
        PredictRequest(item_text="VENTA DE LECHE", transaction_type="sale")


def test_confidence_cannot_override_missing_semantic_context():
    assert model_review_guard_reason("- Revision Tecnica Maquinaria automotriz VPSJ99")
    assert model_review_guard_reason("Interés por mora Energía")
    assert model_review_guard_reason("GASOLINA 93") is None
    assert model_review_guard_reason("Item", "FILTRO DE COMBUSTIBLE") == "generic_item_name_requires_review"
    assert model_review_guard_reason("GUANTE LARGO NITRILO") == "client_examples_conflict_with_glove_taxonomy"
    assert model_review_guard_reason("MENGUANTE") is None
    assert (
        model_review_guard_reason("R.N.PIBOTE RIEGO R 24", predicted_code="EXP-13.2")
        == "irrigation_context_conflicts_with_prediction"
    )
    assert model_review_guard_reason("R.N.PIBOTE RIEGO R 24", predicted_code="EXP-9.2") is None


def test_model_decision_does_not_depend_on_requested_top_k():
    bundle = Bundle(FixedEncoder(), AmbiguousHead())
    bundle.thresholds = {"accept_top1": 0.75, "accept_margin": 0.70, "model_auto_accept": True}
    one = Predictor(bundle).predict(item_text="ambiguous", transaction_type="COMPRAS", top_k=1)
    two = Predictor(bundle).predict(item_text="ambiguous", transaction_type="COMPRAS", top_k=2)
    assert one["decision"] == two["decision"] == "review_required"
    assert one["reason"] == two["reason"] == "small_margin"
    assert one["confidence"]["margin"] == two["confidence"]["margin"] == 0.6


def test_threshold_uses_unrounded_probability():
    bundle = Bundle(FixedEncoder(), BoundaryHead())
    bundle.thresholds = {"accept_top1": 0.75, "accept_margin": 0.40, "model_auto_accept": True}
    result = Predictor(bundle).predict(item_text="boundary", transaction_type="COMPRAS")
    assert result["predictions"][0]["score"] == 0.75
    assert result["decision"] == "review_required"
    assert result["reason"] == "low_confidence"


def test_shadow_mode_applies_to_every_authoritative_path():
    result = Predictor(Bundle(FailIfCalledEncoder()), shadow_mode=True).predict(
        item_text="VENTA DE LECHE", transaction_type="VENTAS"
    )
    assert result["decision"] == "review_required"
    assert result["reason"] == "shadow_mode"


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


def test_staged_release_auto_accepts_high_confidence_model_input():
    decision = decide(
        source="model",
        code1="EXP-11.4",
        top1=0.99,
        margin=0.98,
        weak_classes=set(),
        thresholds={
            "accept_top1": 0.75,
            "accept_margin": 0.50,
            "model_auto_accept": True,
        },
    )
    assert decision.decision == "auto_accept"
    assert decision.reason is None


def test_weak_class_still_requires_review_at_high_confidence():
    decision = decide(
        source="model",
        code1="EXP-11.2",
        top1=0.99,
        margin=0.98,
        weak_classes={"EXP-11.2"},
        thresholds={"accept_top1": 0.75, "accept_margin": 0.50, "model_auto_accept": True},
    )
    assert decision.decision == "review_required"
    assert decision.reason == "weak_class"
