import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.main import app
from app.models.user import User


@pytest.fixture(autouse=True)
def clean_users() -> None:
    with SessionLocal.begin() as db:
        db.execute(delete(User))

    yield

    with SessionLocal.begin() as db:
        db.execute(delete(User))


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_register_creates_user(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={"email": "USER@example.com", "password": "strong-password"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "user@example.com"
    assert body["is_active"] is True
    assert "password_hash" not in body


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    payload = {"email": "user@example.com", "password": "strong-password"}

    first_response = client.post("/auth/register", json=payload)
    second_response = client.post("/auth/register", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"]["code"] == "email_already_registered"


def test_login_returns_access_token(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "strong-password"},
    )

    response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "strong-password"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert body["access_token"]


def test_login_rejects_invalid_password(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "strong-password"},
    )

    response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_credentials"


def test_me_returns_current_user(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "strong-password"},
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "strong-password"},
    )
    token = login_response.json()["access_token"]

    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"


def test_me_requires_authentication(client: TestClient) -> None:
    response = client.get("/me")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "not_authenticated"
