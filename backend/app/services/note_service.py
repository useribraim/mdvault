from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.folder import Folder
from app.models.note import Note
from app.models.user import User
from app.schemas.note import NoteCreate, NoteUpdate


def list_notes(db: Session, user: User) -> list[Note]:
    statement = (
        select(Note)
        .where(Note.user_id == user.id, Note.deleted_at.is_(None))
        .order_by(desc(Note.updated_at))
    )
    return list(db.scalars(statement).all())


def get_note(db: Session, user: User, note_id: UUID) -> Note | None:
    statement = select(Note).where(
        Note.id == note_id,
        Note.user_id == user.id,
        Note.deleted_at.is_(None),
    )
    return db.scalars(statement).first()


def require_note(db: Session, user: User, note_id: UUID) -> Note:
    note = get_note(db, user, note_id)
    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "note_not_found", "message": "Note not found"},
        )
    return note


def validate_folder(db: Session, user: User, folder_id: UUID | None) -> None:
    if folder_id is None:
        return

    folder = db.get(Folder, folder_id)
    if folder is None or folder.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "folder_not_found", "message": "Folder not found"},
        )


def create_note(db: Session, user: User, payload: NoteCreate) -> Note:
    validate_folder(db, user, payload.folder_id)

    note = Note(
        user_id=user.id,
        folder_id=payload.folder_id,
        title=payload.title,
        body_markdown=payload.body_markdown,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def update_note(db: Session, user: User, note_id: UUID, payload: NoteUpdate) -> Note:
    note = require_note(db, user, note_id)
    update_data = payload.model_dump(exclude_unset=True)

    if "folder_id" in update_data:
        validate_folder(db, user, payload.folder_id)
        note.folder_id = payload.folder_id

    if "title" in update_data and payload.title is not None:
        note.title = payload.title

    if "body_markdown" in update_data:
        note.body_markdown = payload.body_markdown if payload.body_markdown is not None else ""

    note.version_number += 1
    db.commit()
    db.refresh(note)
    return note


def soft_delete_note(db: Session, user: User, note_id: UUID) -> None:
    note = require_note(db, user, note_id)
    note.deleted_at = datetime.now(timezone.utc)
    db.commit()
