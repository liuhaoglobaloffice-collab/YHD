import os
from uuid import uuid4

os.environ.setdefault("SECRET_KEY", "1234567890abcdef1234567890abcdef")
os.environ.setdefault("JWT_SECRET_KEY", "1234567890abcdef1234567890abcdef")

from fastapi.testclient import TestClient

from src.api.app import create_app


def test_auth_register_login_and_me():
    app = create_app()
    client = TestClient(app)

    username = f"release_{uuid4().hex[:8]}"
    email = f"{username}@example.com"
    password = "ReleasePass123"

    register = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "full_name": "Release User",
            "password": password,
            "role": "user",
        },
    )
    assert register.status_code == 201, register.text

    login = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    assert token

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200, me.text
    assert me.json()["username"] == username
