from io import BytesIO
from re import sub
from uuid import UUID
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import asc, select
from sqlalchemy.orm import Session

from app.models.folder import Folder
from app.models.note import Note
from app.models.user import User


def sanitize_path_component(value: str, fallback: str) -> str:
    sanitized = sub(r"[\\/\x00-\x1f\x7f]+", "-", value).strip()
    sanitized = sub(r"\s+", " ", sanitized)
    sanitized = sanitized.strip("-. ")
    if not sanitized or sanitized in {".", ".."}:
        return fallback
    return sanitized[:120]


def folder_path(folder: Folder, folders_by_id: dict[UUID, Folder]) -> list[str]:
    components: list[str] = []
    seen_folder_ids: set[UUID] = set()
    current: Folder | None = folder

    while current is not None and current.id not in seen_folder_ids:
        seen_folder_ids.add(current.id)
        components.append(sanitize_path_component(current.name, "folder"))
        current = folders_by_id.get(current.parent_id) if current.parent_id else None

    return list(reversed(components))


def unique_zip_path(base_path: str, used_paths: set[str]) -> str:
    if base_path not in used_paths:
        used_paths.add(base_path)
        return base_path

    stem, suffix = base_path.rsplit(".", maxsplit=1)
    counter = 2
    while True:
        candidate = f"{stem} ({counter}).{suffix}"
        if candidate not in used_paths:
            used_paths.add(candidate)
            return candidate
        counter += 1


def build_notes_export_zip(db: Session, user: User) -> bytes:
    folders = list(
        db.scalars(
            select(Folder)
            .where(Folder.user_id == user.id)
            .order_by(asc(Folder.name), asc(Folder.created_at)),
        ).all()
    )
    folders_by_id = {folder.id: folder for folder in folders}

    notes = list(
        db.scalars(
            select(Note)
            .where(Note.user_id == user.id, Note.deleted_at.is_(None))
            .order_by(asc(Note.title), asc(Note.created_at)),
        ).all()
    )

    output = BytesIO()
    used_paths: set[str] = set()

    with ZipFile(output, mode="w", compression=ZIP_DEFLATED) as zip_file:
        for note in notes:
            note_filename = f"{sanitize_path_component(note.title, 'untitled')}.md"
            path_components: list[str] = []
            if note.folder_id and note.folder_id in folders_by_id:
                path_components = folder_path(folders_by_id[note.folder_id], folders_by_id)

            zip_path = unique_zip_path("/".join([*path_components, note_filename]), used_paths)
            zip_file.writestr(zip_path, note.body_markdown)

    return output.getvalue()
