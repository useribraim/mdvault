from collections.abc import Callable

from fastapi.testclient import TestClient


def create_note(
    client: TestClient,
    headers: dict[str, str],
    title: str,
    body_markdown: str = "",
    folder_id: str | None = None,
) -> dict[str, object]:
    response = client.post(
        "/notes",
        headers=headers,
        json={
            "title": title,
            "body_markdown": body_markdown,
            "folder_id": folder_id,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_note_stores_initial_version(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers()
    note = create_note(client, headers, "Initial", "First body")

    response = client.get(f"/notes/{note['id']}/versions", headers=headers)

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": response.json()[0]["id"],
            "note_id": note["id"],
            "title": "Initial",
            "body_markdown": "First body",
            "version_number": 1,
            "reason": "created",
            "created_at": response.json()[0]["created_at"],
        }
    ]


def test_update_note_stores_updated_version(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers()
    note = create_note(client, headers, "Draft", "Old body")

    update_response = client.patch(
        f"/notes/{note['id']}",
        headers=headers,
        json={"title": "Published", "body_markdown": "New body"},
    )
    versions_response = client.get(f"/notes/{note['id']}/versions", headers=headers)

    assert update_response.status_code == 200
    assert update_response.json()["version_number"] == 2
    versions = versions_response.json()
    assert [version["version_number"] for version in versions] == [1, 2]
    assert [version["reason"] for version in versions] == ["created", "updated"]
    assert versions[1]["title"] == "Published"
    assert versions[1]["body_markdown"] == "New body"


def test_folder_only_update_does_not_create_content_version(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers()
    folder_response = client.post("/folders", headers=headers, json={"name": "Projects"})
    note = create_note(client, headers, "Foldered", "Same body")

    update_response = client.patch(
        f"/notes/{note['id']}",
        headers=headers,
        json={"folder_id": folder_response.json()["id"]},
    )
    versions_response = client.get(f"/notes/{note['id']}/versions", headers=headers)

    assert update_response.status_code == 200
    assert update_response.json()["version_number"] == 1
    assert len(versions_response.json()) == 1


def test_restore_version_updates_note_and_creates_restored_snapshot(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers()
    note = create_note(client, headers, "Draft", "Old body")
    client.patch(
        f"/notes/{note['id']}",
        headers=headers,
        json={"title": "Published", "body_markdown": "New body"},
    )
    versions = client.get(f"/notes/{note['id']}/versions", headers=headers).json()
    first_version_id = versions[0]["id"]

    restore_response = client.post(
        f"/notes/{note['id']}/versions/{first_version_id}/restore",
        headers=headers,
    )
    versions_after_restore = client.get(f"/notes/{note['id']}/versions", headers=headers)

    assert restore_response.status_code == 200
    restored_note = restore_response.json()
    assert restored_note["title"] == "Draft"
    assert restored_note["body_markdown"] == "Old body"
    assert restored_note["version_number"] == 3
    versions_after = versions_after_restore.json()
    assert [version["version_number"] for version in versions_after] == [1, 2, 3]
    assert versions_after[2]["reason"] == "restored"
    assert versions_after[2]["title"] == "Draft"


def test_restore_version_refreshes_outgoing_links(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers()
    first_target = create_note(client, headers, "First")
    second_target = create_note(client, headers, "Second")
    source = create_note(client, headers, "Index", "Open [[First]].")
    client.patch(
        f"/notes/{source['id']}",
        headers=headers,
        json={"body_markdown": "Open [[Second]]."},
    )
    first_version = client.get(f"/notes/{source['id']}/versions", headers=headers).json()[0]

    restore_response = client.post(
        f"/notes/{source['id']}/versions/{first_version['id']}/restore",
        headers=headers,
    )
    outgoing_response = client.get(f"/notes/{source['id']}/outgoing-links", headers=headers)

    assert restore_response.status_code == 200
    links = outgoing_response.json()
    assert len(links) == 1
    assert links[0]["raw_title"] == "First"
    assert links[0]["target_note_id"] == first_target["id"]
    assert links[0]["target_note_id"] != second_target["id"]


def test_user_cannot_access_or_restore_another_users_versions(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    owner_headers = auth_headers("owner@example.com")
    other_headers = auth_headers("other@example.com")
    note = create_note(client, owner_headers, "Private", "Secret")
    version = client.get(f"/notes/{note['id']}/versions", headers=owner_headers).json()[0]

    list_response = client.get(f"/notes/{note['id']}/versions", headers=other_headers)
    restore_response = client.post(
        f"/notes/{note['id']}/versions/{version['id']}/restore",
        headers=other_headers,
    )

    assert list_response.status_code == 404
    assert restore_response.status_code == 404


def test_deleted_note_versions_are_not_accessible(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers()
    note = create_note(client, headers, "Temporary", "Body")
    delete_response = client.delete(f"/notes/{note['id']}", headers=headers)

    response = client.get(f"/notes/{note['id']}/versions", headers=headers)

    assert delete_response.status_code == 204
    assert response.status_code == 404
