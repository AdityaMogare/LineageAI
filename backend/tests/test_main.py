from fastapi.testclient import TestClient
from lineageai.main import app


def test_health() -> None:
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}


def test_public_config_does_not_expose_secrets() -> None:
    payload = TestClient(app).get("/api/config").json()

    assert payload["model"] == "kimi-k3"
    assert "api_key" not in payload
    assert "token" not in payload
