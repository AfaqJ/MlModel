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


def test_batch_limit():
    items = [{"item_text": "X"} for _ in range(501)]
    response = client.post("/predict-batch", json={"items": items})
    assert response.status_code == 413
