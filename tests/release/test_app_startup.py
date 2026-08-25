import os

os.environ.setdefault("SECRET_KEY", "1234567890abcdef1234567890abcdef")
os.environ.setdefault("JWT_SECRET_KEY", "1234567890abcdef1234567890abcdef")

from fastapi.testclient import TestClient

from src.api.app import create_app


def test_app_startup_and_healthcheck():
    app = create_app()
    client = TestClient(app)

    root = client.get("/")
    assert root.status_code == 200, root.text
    assert root.json()["status"] == "running"

    health = client.get("/api/v1/health")
    assert health.status_code == 200, health.text
    assert "status" in health.json()
