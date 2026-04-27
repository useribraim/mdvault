from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.note import NoteCreate, NoteRead, NoteUpdate
from app.schemas.note_link import BacklinkRead, NoteLinkRead
from app.schemas.note_version import NoteVersionRead
from app.services.note_link_service import list_backlinks, list_outgoing_links
from app.services.note_service import (
    create_note,
    list_notes,
    require_note,
    soft_delete_note,
    update_note,
)
from app.services.note_version_service import list_note_versions, restore_note_version

router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
def create_note_endpoint(
    payload: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NoteRead:
    return create_note(db, current_user, payload)


@router.get("", response_model=list[NoteRead])
def list_notes_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NoteRead]:
    return list_notes(db, current_user)


@router.get("/{note_id}", response_model=NoteRead)
def read_note_endpoint(
    note_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NoteRead:
    return require_note(db, current_user, note_id)


@router.get("/{note_id}/outgoing-links", response_model=list[NoteLinkRead])
def list_outgoing_links_endpoint(
    note_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NoteLinkRead]:
    require_note(db, current_user, note_id)
    return list_outgoing_links(db, current_user, note_id)


@router.get("/{note_id}/backlinks", response_model=list[BacklinkRead])
def list_backlinks_endpoint(
    note_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    require_note(db, current_user, note_id)
    return [
        {
            "id": link.id,
            "source_note_id": source_note.id,
            "source_note_title": source_note.title,
            "raw_title": link.raw_title,
            "status": link.status,
            "created_at": link.created_at,
        }
        for link, source_note in list_backlinks(db, current_user, note_id)
    ]


@router.get("/{note_id}/versions", response_model=list[NoteVersionRead])
def list_note_versions_endpoint(
    note_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NoteVersionRead]:
    return list_note_versions(db, current_user, note_id)


@router.post("/{note_id}/versions/{version_id}/restore", response_model=NoteRead)
def restore_note_version_endpoint(
    note_id: UUID,
    version_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NoteRead:
    return restore_note_version(db, current_user, note_id, version_id)


@router.patch("/{note_id}", response_model=NoteRead)
def update_note_endpoint(
    note_id: UUID,
    payload: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NoteRead:
    return update_note(db, current_user, note_id, payload)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note_endpoint(
    note_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    soft_delete_note(db, current_user, note_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
