from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["model_loaded"] is False


def test_model_info():
    response = client.get("/model-info")
    assert response.status_code == 200
    body = response.json()
    assert body["model_version"] == "v1.0.0"
    assert body["num_trained_classes"] == 66


def test_predict_known_vaccine():
    response = client.post(
        "/predict",
        json={"item_text": "VACUNA CLOSTRIBAC 8 GOLD X 50 DOS.", "provider": "COOPRINSEM"},
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
        json={"item_text": "Administracion del servicio", "provider": "COOP PAILLACO", "meter_code": "6365.02"},
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
        json={"item_text": "VACUNA CLOSTRIBAC 8 GOLD X 50 DOS.", "provider": "COOPRINSEM", "meter_code": "00000"},
    )
    assert response.status_code == 200
    assert response.json()["source"] in {"model", "product_lookup"}


def test_batch_limit():
    items = [{"item_text": "X"} for _ in range(501)]
    response = client.post("/predict-batch", json={"items": items})
    assert response.status_code == 413
