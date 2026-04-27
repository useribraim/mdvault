from collections.abc import Callable

from fastapi.testclient import TestClient


def test_create_folder_requires_authentication(client: TestClient) -> None:
    response = client.post("/folders", json={"name": "Projects"})

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "not_authenticated"


def test_create_root_folder(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    response = client.post(
        "/folders",
        headers=auth_headers(),
        json={"name": "Projects"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Projects"
    assert body["parent_id"] is None


def test_create_child_folder(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers()
    parent_response = client.post("/folders", headers=headers, json={"name": "Projects"})
    parent_id = parent_response.json()["id"]

    response = client.post(
        "/folders",
        headers=headers,
        json={"name": "Backend", "parent_id": parent_id},
    )

    assert response.status_code == 201
    assert response.json()["parent_id"] == parent_id


def test_list_folders_returns_only_current_user_folders(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    first_user_headers = auth_headers("first@example.com")
    second_user_headers = auth_headers("second@example.com")

    first_response = client.post(
        "/folders",
        headers=first_user_headers,
        json={"name": "First user folder"},
    )
    client.post(
        "/folders",
        headers=second_user_headers,
        json={"name": "Second user folder"},
    )

    response = client.get("/folders", headers=first_user_headers)

    assert response.status_code == 200
    assert response.json() == [first_response.json()]


def test_read_and_update_folder(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers()
    create_response = client.post("/folders", headers=headers, json={"name": "Drafts"})
    folder_id = create_response.json()["id"]

    read_response = client.get(f"/folders/{folder_id}", headers=headers)
    update_response = client.patch(
        f"/folders/{folder_id}",
        headers=headers,
        json={"name": "Archive"},
    )

    assert read_response.status_code == 200
    assert read_response.json()["name"] == "Drafts"
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Archive"


def test_folder_parent_must_belong_to_current_user(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    owner_headers = auth_headers("owner@example.com")
    other_headers = auth_headers("other@example.com")
    owner_folder = client.post(
        "/folders",
        headers=owner_headers,
        json={"name": "Owner folder"},
    )

    response = client.post(
        "/folders",
        headers=other_headers,
        json={"name": "Invalid child", "parent_id": owner_folder.json()["id"]},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "folder_not_found"


def test_update_folder_rejects_cycles(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers()
    root_response = client.post("/folders", headers=headers, json={"name": "Root"})
    child_response = client.post(
        "/folders",
        headers=headers,
        json={"name": "Child", "parent_id": root_response.json()["id"]},
    )

    response = client.patch(
        f"/folders/{root_response.json()['id']}",
        headers=headers,
        json={"parent_id": child_response.json()["id"]},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "folder_cycle"


def test_delete_folder_preserves_notes_and_child_folders(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers()
    parent_response = client.post("/folders", headers=headers, json={"name": "Projects"})
    parent_id = parent_response.json()["id"]
    child_response = client.post(
        "/folders",
        headers=headers,
        json={"name": "Backend", "parent_id": parent_id},
    )
    note_response = client.post(
        "/notes",
        headers=headers,
        json={"title": "Foldered note", "body_markdown": "Content", "folder_id": parent_id},
    )

    delete_response = client.delete(f"/folders/{parent_id}", headers=headers)
    folders_response = client.get("/folders", headers=headers)
    note_read_response = client.get(f"/notes/{note_response.json()['id']}", headers=headers)

    assert delete_response.status_code == 204
    assert len(folders_response.json()) == 1
    remaining_folder = folders_response.json()[0]
    assert remaining_folder["id"] == child_response.json()["id"]
    assert remaining_folder["name"] == "Backend"
    assert remaining_folder["parent_id"] is None
    assert note_read_response.json()["folder_id"] is None
