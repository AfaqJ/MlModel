import json

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


client = TestClient(app)
settings = get_settings()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["model_loaded"] is False


def test_model_info():
    response = client.get("/model-info")
    assert response.status_code == 200
    body = response.json()
    model_card = json.loads((settings.model_dir / "model_card.json").read_text())
    assert body["model_version"] == model_card["model_version"]
    assert body["num_trained_classes"] == 67


def test_predict_known_vaccine():
    response = client.post(
        "/predict",
        json={"item_text": "VACUNA CLOSTRIBAC 8 GOLD X 50 DOS.", "provider": "COOPRINSEM", "transaction_type": "COMPRAS"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["predictions"][0]["code"] == "EXP-2.3"
    assert body["decision"] in {"auto_accept", "review_required"}


def test_predict_meter_lookup_deterministic():
    # A known electricity meter (CdgIntRecep, dotted form) resolves via the meter
    # map without the ML model. 6365.02 -> irrigation meter -> EXP-9.1.
    response = client.post(
        "/predict",
        json={"item_text": "Administracion del servicio", "provider": "COOP PAILLACO", "meter_code": "6365.02", "transaction_type": "COMPRAS"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "meter_lookup"
    assert body["predictions"][0]["code"] == "EXP-9.1"
    assert body["decision"] == "auto_accept"


def test_predict_unknown_meter_falls_through_to_model():
    # An unknown meter must not short-circuit; it goes to the ML model as usual.
    response = client.post(
        "/predict",
        json={"item_text": "VACUNA CLOSTRIBAC 8 GOLD X 50 DOS.", "provider": "COOPRINSEM", "meter_code": "00000", "transaction_type": "COMPRAS"},
    )
    assert response.status_code == 200
    assert response.json()["source"] in {"model", "product_lookup"}


def test_predict_verified_milk_sale_uses_exact_transaction_lookup():
    response = client.post(
        "/predict",
        json={"item_text": "VENTA DE LECHE", "transaction_type": "VENTAS"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "business_rule"
    assert body["predictions"] == [
        {"code": "ING-0.1", "name": "VENTA DE LECHE", "score": 1.0}
    ]
    assert body["decision"] == "auto_accept"


def test_same_text_is_not_a_sale_without_ventas_direction():
    response = client.post(
        "/predict",
        json={"item_text": "VENTA DE LECHE", "transaction_type": "COMPRAS"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] != "business_rule"
    assert all(not prediction["code"].startswith("ING-") for prediction in body["predictions"])


def test_unknown_sale_can_never_auto_accept():
    response = client.post(
        "/predict",
        json={"item_text": "VENTA CAMIONETA", "transaction_type": "VENTAS"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "model"
    assert body["decision"] == "review_required"
    assert body["reason"] == "unknown_sales_item"


def test_row_level_product_family_resolution_beats_folder_placement_and_model():
    response = client.post(
        "/predict",
        json={
            "item_text": "GUANTE LARGO NITRILO XL SHOOF 204630",
            "description": "GUANTE LARGO NITRILO XL MARCA SHOOF",
            "provider": "COOPERATIVA AGRICOLA Y LECHERA DE LA UNION LTDA.",
            "transaction_type": "COMPRAS",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "product_lookup"
    assert body["predictions"][0]["code"] == "EXP-16.1"
    assert body["decision"] == "auto_accept"


def test_transaction_type_is_validated():
    response = client.post(
        "/predict",
        json={"item_text": "VENTA DE LECHE", "transaction_type": "sale"},
    )
    assert response.status_code == 422


def test_transaction_type_is_required():
    response = client.post("/predict", json={"item_text": "VENTA DE LECHE"})
    assert response.status_code == 422


def test_batch_limit():
    items = [{"item_text": "X", "transaction_type": "COMPRAS"} for _ in range(501)]
    response = client.post("/predict-batch", json={"items": items})
    assert response.status_code == 413
