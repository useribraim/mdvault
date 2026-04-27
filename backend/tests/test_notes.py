from collections.abc import Callable

from fastapi.testclient import TestClient


def test_create_note_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/notes",
        json={"title": "Private note", "body_markdown": "# Hello"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "not_authenticated"


def test_create_note(client: TestClient, auth_headers: Callable[[str], dict[str, str]]) -> None:
    response = client.post(
        "/notes",
        headers=auth_headers(),
        json={"title": "PostgreSQL notes", "body_markdown": "# Indexing\nUse GIN."},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "PostgreSQL notes"
    assert body["body_markdown"] == "# Indexing\nUse GIN."
    assert body["version_number"] == 1
    assert body["folder_id"] is None


def test_list_notes_returns_only_current_user_notes(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    first_user_headers = auth_headers("first@example.com")
    second_user_headers = auth_headers("second@example.com")

    first_response = client.post(
        "/notes",
        headers=first_user_headers,
        json={"title": "First user's note", "body_markdown": "Private"},
    )
    client.post(
        "/notes",
        headers=second_user_headers,
        json={"title": "Second user's note", "body_markdown": "Also private"},
    )

    response = client.get("/notes", headers=first_user_headers)

    assert response.status_code == 200
    assert response.json() == [first_response.json()]


def test_read_note(client: TestClient, auth_headers: Callable[[str], dict[str, str]]) -> None:
    headers = auth_headers()
    create_response = client.post(
        "/notes",
        headers=headers,
        json={"title": "Daily note", "body_markdown": "Today I learned."},
    )
    note_id = create_response.json()["id"]

    response = client.get(f"/notes/{note_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["title"] == "Daily note"


def test_update_note_increments_version(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers()
    create_response = client.post(
        "/notes",
        headers=headers,
        json={"title": "Draft", "body_markdown": "Old body"},
    )
    note_id = create_response.json()["id"]

    response = client.patch(
        f"/notes/{note_id}",
        headers=headers,
        json={"title": "Updated draft", "body_markdown": "New body"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Updated draft"
    assert body["body_markdown"] == "New body"
    assert body["version_number"] == 2


def test_delete_note_soft_deletes_it(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers()
    create_response = client.post(
        "/notes",
        headers=headers,
        json={"title": "Delete me", "body_markdown": "Temporary"},
    )
    note_id = create_response.json()["id"]

    delete_response = client.delete(f"/notes/{note_id}", headers=headers)
    read_response = client.get(f"/notes/{note_id}", headers=headers)
    list_response = client.get("/notes", headers=headers)

    assert delete_response.status_code == 204
    assert read_response.status_code == 404
    assert list_response.json() == []


def test_user_cannot_access_another_users_note(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    owner_headers = auth_headers("owner@example.com")
    other_headers = auth_headers("other@example.com")
    create_response = client.post(
        "/notes",
        headers=owner_headers,
        json={"title": "Owned note", "body_markdown": "Secret"},
    )
    note_id = create_response.json()["id"]

    read_response = client.get(f"/notes/{note_id}", headers=other_headers)
    update_response = client.patch(
        f"/notes/{note_id}",
        headers=other_headers,
        json={"title": "Stolen"},
    )
    delete_response = client.delete(f"/notes/{note_id}", headers=other_headers)

    assert read_response.status_code == 404
    assert update_response.status_code == 404
    assert delete_response.status_code == 404
