from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.note import Note
from app.models.note_link import NoteLink
from app.models.user import User
from app.services.markdown_link_parser import parse_wiki_links

RESOLVED = "resolved"
UNRESOLVED = "unresolved"
AMBIGUOUS = "ambiguous"


def resolve_link_target(db: Session, user: User, raw_title: str) -> tuple[str, UUID | None]:
    statement = select(Note.id).where(
        Note.user_id == user.id,
        Note.deleted_at.is_(None),
        func.lower(Note.title) == raw_title.lower(),
    )
    matches = list(db.scalars(statement).all())

    if len(matches) == 1:
        return RESOLVED, matches[0]
    if len(matches) > 1:
        return AMBIGUOUS, None
    return UNRESOLVED, None


def sync_note_links(db: Session, user: User, note: Note) -> None:
    db.execute(
        delete(NoteLink).where(
            NoteLink.user_id == user.id,
            NoteLink.source_note_id == note.id,
        )
    )

    for raw_title in parse_wiki_links(note.body_markdown):
        status, target_note_id = resolve_link_target(db, user, raw_title)
        db.add(
            NoteLink(
                user_id=user.id,
                source_note_id=note.id,
                target_note_id=target_note_id,
                raw_title=raw_title,
                status=status,
            )
        )


def refresh_links_for_title(db: Session, user: User, title: str) -> None:
    statement = (
        select(Note)
        .join(NoteLink, NoteLink.source_note_id == Note.id)
        .where(
            Note.user_id == user.id,
            Note.deleted_at.is_(None),
            NoteLink.user_id == user.id,
            func.lower(NoteLink.raw_title) == title.lower(),
        )
        .distinct()
    )

    for source_note in db.scalars(statement).all():
        sync_note_links(db, user, source_note)


def list_outgoing_links(db: Session, user: User, source_note_id: UUID) -> list[NoteLink]:
    statement = (
        select(NoteLink)
        .where(NoteLink.user_id == user.id, NoteLink.source_note_id == source_note_id)
        .order_by(NoteLink.created_at.asc(), NoteLink.raw_title.asc())
    )
    return list(db.scalars(statement).all())


def list_backlinks(db: Session, user: User, target_note_id: UUID) -> list[tuple[NoteLink, Note]]:
    statement = (
        select(NoteLink, Note)
        .join(Note, Note.id == NoteLink.source_note_id)
        .where(
            NoteLink.user_id == user.id,
            NoteLink.target_note_id == target_note_id,
            NoteLink.status == RESOLVED,
            Note.deleted_at.is_(None),
        )
        .order_by(Note.updated_at.desc(), NoteLink.created_at.asc())
    )
    return list(db.execute(statement).all())
