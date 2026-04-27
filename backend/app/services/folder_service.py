from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import asc, select, update
from sqlalchemy.orm import Session

from app.models.folder import Folder
from app.models.note import Note
from app.models.user import User
from app.schemas.folder import FolderCreate, FolderUpdate


def list_folders(db: Session, user: User) -> list[Folder]:
    statement = (
        select(Folder)
        .where(Folder.user_id == user.id)
        .order_by(asc(Folder.name), asc(Folder.created_at))
    )
    return list(db.scalars(statement).all())


def get_folder(db: Session, user: User, folder_id: UUID) -> Folder | None:
    statement = select(Folder).where(
        Folder.id == folder_id,
        Folder.user_id == user.id,
    )
    return db.scalars(statement).first()


def require_folder(db: Session, user: User, folder_id: UUID) -> Folder:
    folder = get_folder(db, user, folder_id)
    if folder is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "folder_not_found", "message": "Folder not found"},
        )
    return folder


def validate_parent_folder(
    db: Session,
    user: User,
    parent_id: UUID | None,
    folder_id: UUID | None = None,
) -> None:
    if parent_id is None:
        return

    parent = require_folder(db, user, parent_id)
    if folder_id is None:
        return

    seen_folder_ids: set[UUID] = set()
    current: Folder | None = parent
    while current is not None:
        if current.id == folder_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "folder_cycle",
                    "message": "A folder cannot be moved inside itself or its descendants",
                },
            )

        if current.id in seen_folder_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "folder_cycle", "message": "Folder hierarchy contains a cycle"},
            )

        seen_folder_ids.add(current.id)
        current = get_folder(db, user, current.parent_id) if current.parent_id else None


def create_folder(db: Session, user: User, payload: FolderCreate) -> Folder:
    validate_parent_folder(db, user, payload.parent_id)

    folder = Folder(
        user_id=user.id,
        parent_id=payload.parent_id,
        name=payload.name,
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return folder


def update_folder(db: Session, user: User, folder_id: UUID, payload: FolderUpdate) -> Folder:
    folder = require_folder(db, user, folder_id)
    update_data = payload.model_dump(exclude_unset=True)

    if "parent_id" in update_data:
        validate_parent_folder(db, user, payload.parent_id, folder.id)
        folder.parent_id = payload.parent_id

    if "name" in update_data and payload.name is not None:
        folder.name = payload.name

    db.commit()
    db.refresh(folder)
    return folder


def delete_folder(db: Session, user: User, folder_id: UUID) -> None:
    folder = require_folder(db, user, folder_id)

    db.execute(
        update(Note)
        .where(Note.user_id == user.id, Note.folder_id == folder.id)
        .values(folder_id=None)
    )
    db.execute(
        update(Folder)
        .where(Folder.user_id == user.id, Folder.parent_id == folder.id)
        .values(parent_id=None)
    )
    db.delete(folder)
    db.commit()
