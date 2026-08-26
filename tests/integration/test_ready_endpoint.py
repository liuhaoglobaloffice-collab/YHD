from fastapi.testclient import TestClient

from src.api.app import create_app


def test_ready_endpoint():
    app = create_app()
    client = TestClient(app)

    resp = client.get("/api/v1/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["status"] in ("ready", "not_ready")
