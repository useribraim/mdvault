from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.folder import FolderCreate, FolderRead, FolderUpdate
from app.services.folder_service import (
    create_folder,
    delete_folder,
    list_folders,
    require_folder,
    update_folder,
)

router = APIRouter(prefix="/folders", tags=["folders"])


@router.post("", response_model=FolderRead, status_code=status.HTTP_201_CREATED)
def create_folder_endpoint(
    payload: FolderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FolderRead:
    return create_folder(db, current_user, payload)


@router.get("", response_model=list[FolderRead])
def list_folders_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FolderRead]:
    return list_folders(db, current_user)


@router.get("/{folder_id}", response_model=FolderRead)
def read_folder_endpoint(
    folder_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FolderRead:
    return require_folder(db, current_user, folder_id)


@router.patch("/{folder_id}", response_model=FolderRead)
def update_folder_endpoint(
    folder_id: UUID,
    payload: FolderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FolderRead:
    return update_folder(db, current_user, folder_id, payload)


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder_endpoint(
    folder_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    delete_folder(db, current_user, folder_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
