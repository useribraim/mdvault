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


def test_note_outgoing_links_include_resolved_and_unresolved_links(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers()
    target = create_note(client, headers, "Search Design")
    source = create_note(
        client,
        headers,
        "Backend notes",
        "Read [[Search Design]] and [[Missing Note]].",
    )

    response = client.get(f"/notes/{source['id']}/outgoing-links", headers=headers)

    assert response.status_code == 200
    links = sorted(response.json(), key=lambda link: link["raw_title"])
    assert links[0]["raw_title"] == "Missing Note"
    assert links[0]["status"] == "unresolved"
    assert links[0]["target_note_id"] is None
    assert links[1]["raw_title"] == "Search Design"
    assert links[1]["status"] == "resolved"
    assert links[1]["target_note_id"] == target["id"]


def test_backlinks_return_source_notes_for_resolved_links(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers()
    target = create_note(client, headers, "PostgreSQL")
    source = create_note(client, headers, "Search", "Use [[PostgreSQL]] full-text search.")

    response = client.get(f"/notes/{target['id']}/backlinks", headers=headers)

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": response.json()[0]["id"],
            "source_note_id": source["id"],
            "source_note_title": "Search",
            "raw_title": "PostgreSQL",
            "status": "resolved",
            "created_at": response.json()[0]["created_at"],
        }
    ]


def test_duplicate_titles_make_links_ambiguous(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers()
    first_target = create_note(client, headers, "Daily")
    second_target = create_note(client, headers, "Daily")
    source = create_note(client, headers, "Index", "Open [[Daily]].")

    outgoing_response = client.get(f"/notes/{source['id']}/outgoing-links", headers=headers)
    first_backlinks_response = client.get(f"/notes/{first_target['id']}/backlinks", headers=headers)
    second_backlinks_response = client.get(
        f"/notes/{second_target['id']}/backlinks",
        headers=headers,
    )

    assert outgoing_response.status_code == 200
    assert outgoing_response.json()[0]["status"] == "ambiguous"
    assert outgoing_response.json()[0]["target_note_id"] is None
    assert first_backlinks_response.json() == []
    assert second_backlinks_response.json() == []


def test_updating_note_body_replaces_outgoing_links(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers()
    first_target = create_note(client, headers, "First")
    second_target = create_note(client, headers, "Second")
    source = create_note(client, headers, "Index", "Open [[First]].")

    response = client.patch(
        f"/notes/{source['id']}",
        headers=headers,
        json={"body_markdown": "Open [[Second]]."},
    )
    outgoing_response = client.get(f"/notes/{source['id']}/outgoing-links", headers=headers)

    assert response.status_code == 200
    assert outgoing_response.status_code == 200
    links = outgoing_response.json()
    assert len(links) == 1
    assert links[0]["raw_title"] == "Second"
    assert links[0]["target_note_id"] == second_target["id"]
    assert links[0]["target_note_id"] != first_target["id"]


def test_creating_target_resolves_existing_unresolved_links(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers()
    source = create_note(client, headers, "Index", "Open [[Later]].")

    before_response = client.get(f"/notes/{source['id']}/outgoing-links", headers=headers)
    target = create_note(client, headers, "Later")
    after_response = client.get(f"/notes/{source['id']}/outgoing-links", headers=headers)

    assert before_response.json()[0]["status"] == "unresolved"
    assert after_response.json()[0]["status"] == "resolved"
    assert after_response.json()[0]["target_note_id"] == target["id"]


def test_renaming_target_resolves_existing_unresolved_links(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers()
    source = create_note(client, headers, "Index", "Open [[Later]].")
    target = create_note(client, headers, "Untitled")

    response = client.patch(
        f"/notes/{target['id']}",
        headers=headers,
        json={"title": "Later"},
    )
    outgoing_response = client.get(f"/notes/{source['id']}/outgoing-links", headers=headers)

    assert response.status_code == 200
    assert outgoing_response.status_code == 200
    assert outgoing_response.json()[0]["status"] == "resolved"
    assert outgoing_response.json()[0]["target_note_id"] == target["id"]


def test_deleting_target_marks_existing_links_unresolved(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers()
    target = create_note(client, headers, "Temporary")
    source = create_note(client, headers, "Index", "Open [[Temporary]].")

    delete_response = client.delete(f"/notes/{target['id']}", headers=headers)
    outgoing_response = client.get(f"/notes/{source['id']}/outgoing-links", headers=headers)

    assert delete_response.status_code == 204
    assert outgoing_response.json()[0]["status"] == "unresolved"
    assert outgoing_response.json()[0]["target_note_id"] is None


def test_user_cannot_read_another_users_note_links(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    owner_headers = auth_headers("owner@example.com")
    other_headers = auth_headers("other@example.com")
    note = create_note(client, owner_headers, "Private", "[[Secret]]")

    outgoing_response = client.get(f"/notes/{note['id']}/outgoing-links", headers=other_headers)
    backlinks_response = client.get(f"/notes/{note['id']}/backlinks", headers=other_headers)

    assert outgoing_response.status_code == 404
    assert backlinks_response.status_code == 404
