from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import asc, select
from sqlalchemy.orm import Session

from app.models.note import Note
from app.models.note_version import NoteVersion
from app.models.user import User
from app.services.note_link_service import refresh_links_for_title, sync_note_links

CREATED = "created"
UPDATED = "updated"
RESTORED = "restored"


def get_active_note(db: Session, user: User, note_id: UUID) -> Note | None:
    statement = select(Note).where(
        Note.id == note_id,
        Note.user_id == user.id,
        Note.deleted_at.is_(None),
    )
    return db.scalars(statement).first()


def require_active_note(db: Session, user: User, note_id: UUID) -> Note:
    note = get_active_note(db, user, note_id)
    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "note_not_found", "message": "Note not found"},
        )
    return note


def create_note_version(db: Session, user: User, note: Note, reason: str) -> NoteVersion:
    version = NoteVersion(
        user_id=user.id,
        note_id=note.id,
        title=note.title,
        body_markdown=note.body_markdown,
        version_number=note.version_number,
        reason=reason,
    )
    db.add(version)
    return version


def list_note_versions(db: Session, user: User, note_id: UUID) -> list[NoteVersion]:
    require_active_note(db, user, note_id)
    statement = (
        select(NoteVersion)
        .where(NoteVersion.user_id == user.id, NoteVersion.note_id == note_id)
        .order_by(asc(NoteVersion.version_number))
    )
    return list(db.scalars(statement).all())


def require_note_version(
    db: Session,
    user: User,
    note_id: UUID,
    version_id: UUID,
) -> NoteVersion:
    statement = select(NoteVersion).where(
        NoteVersion.id == version_id,
        NoteVersion.user_id == user.id,
        NoteVersion.note_id == note_id,
    )
    version = db.scalars(statement).first()
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "note_version_not_found", "message": "Note version not found"},
        )
    return version


def restore_note_version(
    db: Session,
    user: User,
    note_id: UUID,
    version_id: UUID,
) -> Note:
    note = require_active_note(db, user, note_id)
    version = require_note_version(db, user, note_id, version_id)
    old_title = note.title

    note.title = version.title
    note.body_markdown = version.body_markdown
    note.version_number += 1

    sync_note_links(db, user, note)
    refresh_links_for_title(db, user, old_title)
    refresh_links_for_title(db, user, note.title)
    create_note_version(db, user, note, RESTORED)

    db.commit()
    db.refresh(note)
    return note
