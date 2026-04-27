from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.main import app
from app.models.user import User


@pytest.fixture(autouse=True)
def clean_database() -> None:
    with SessionLocal.begin() as db:
        db.execute(delete(User))

    yield

    with SessionLocal.begin() as db:
        db.execute(delete(User))


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_headers(client: TestClient) -> Callable[[str], dict[str, str]]:
    def build_headers(
        email: str = "user@example.com",
        password: str = "strong-password",
    ) -> dict[str, str]:
        client.post("/auth/register", json={"email": email, "password": password})
        login_response = client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return build_headers
