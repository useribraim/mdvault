from collections.abc import Callable
from io import BytesIO
from zipfile import ZipFile

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
        json={"title": title, "body_markdown": body_markdown, "folder_id": folder_id},
    )
    assert response.status_code == 201
    return response.json()


def test_export_requires_authentication(client: TestClient) -> None:
    response = client.get("/export.zip")

    assert response.status_code == 401


def test_export_includes_current_users_active_notes(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers()
    other_headers = auth_headers("other@example.com")
    create_note(client, headers, "PostgreSQL Guide", "# PostgreSQL\nUse GIN.")
    deleted_note = create_note(client, headers, "Deleted", "Do not export")
    create_note(client, other_headers, "Other User", "Do not export")
    client.delete(f"/notes/{deleted_note['id']}", headers=headers)

    response = client.get("/export.zip", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["content-disposition"] == 'attachment; filename="mdvault-notes.zip"'

    with ZipFile(BytesIO(response.content)) as zip_file:
        assert zip_file.namelist() == ["PostgreSQL Guide.md"]
        assert zip_file.read("PostgreSQL Guide.md").decode() == "# PostgreSQL\nUse GIN."


def test_export_preserves_folder_paths_and_disambiguates_duplicate_names(
    client: TestClient,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    headers = auth_headers()
    root_response = client.post("/folders", headers=headers, json={"name": "Projects"})
    child_response = client.post(
        "/folders",
        headers=headers,
        json={"name": "Backend/API", "parent_id": root_response.json()["id"]},
    )
    create_note(client, headers, "Daily", "Root daily")
    create_note(client, headers, "Daily", "Folder daily", child_response.json()["id"])
    create_note(client, headers, "../Unsafe/Name", "Safe filename")

    response = client.get("/export.zip", headers=headers)

    assert response.status_code == 200
    with ZipFile(BytesIO(response.content)) as zip_file:
        assert zip_file.namelist() == [
            "Unsafe-Name.md",
            "Daily.md",
            "Projects/Backend-API/Daily.md",
        ]
        assert zip_file.read("Projects/Backend-API/Daily.md").decode() == "Folder daily"
