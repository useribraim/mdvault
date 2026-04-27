from collections.abc import Callable

from fastapi.testclient import TestClient


def create_note(
    client: TestClient,
    headers: dict[str, str],
    title: str,
    body_markdown: str = "",
) -> dict[str, object]:
    response = client.post(
        "/notes",
        headers=headers,
        json={"title": title, "body_markdown": body_markdown},
    )
    assert response.status_code == 201
    return response.json()


def test_search_requires_authentication(client: TestClient) -> None:
    response = client.get("/search?q=postgresql")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "not_authenticated"


def test_search_returns_matching_notes(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers()
    match = create_note(client, headers, "PostgreSQL Guide", "Indexes and ranking")
    create_note(client, headers, "Cooking", "Pasta notes")

    response = client.get("/search?q=postgresql", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["note"]["id"] == match["id"]
    assert response.json()[0]["rank"] > 0


def test_search_ranks_title_matches_before_body_matches(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers()
    title_match = create_note(client, headers, "PostgreSQL Guide", "Database notes")
    body_match = create_note(client, headers, "Database Guide", "PostgreSQL notes")

    response = client.get("/search?q=postgresql", headers=headers)

    assert response.status_code == 200
    results = response.json()
    assert [result["note"]["id"] for result in results] == [
        title_match["id"],
        body_match["id"],
    ]
    assert results[0]["rank"] > results[1]["rank"]


def test_search_is_scoped_to_current_user(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    first_user_headers = auth_headers("first@example.com")
    second_user_headers = auth_headers("second@example.com")
    first_user_note = create_note(
        client,
        first_user_headers,
        "PostgreSQL private note",
        "Search text",
    )
    create_note(
        client,
        second_user_headers,
        "PostgreSQL other note",
        "Search text",
    )

    response = client.get("/search?q=postgresql", headers=first_user_headers)

    assert response.status_code == 200
    assert [result["note"]["id"] for result in response.json()] == [first_user_note["id"]]


def test_search_excludes_soft_deleted_notes(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers()
    note = create_note(client, headers, "Temporary PostgreSQL note")
    delete_response = client.delete(f"/notes/{note['id']}", headers=headers)

    response = client.get("/search?q=postgresql", headers=headers)

    assert delete_response.status_code == 204
    assert response.status_code == 200
    assert response.json() == []


def test_search_limit_caps_results(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers()
    create_note(client, headers, "PostgreSQL one")
    create_note(client, headers, "PostgreSQL two")

    response = client.get("/search?q=postgresql&limit=1", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 1
