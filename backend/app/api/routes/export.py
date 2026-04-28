from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.export_service import build_notes_export_zip

router = APIRouter(tags=["export"])


@router.get("/export.zip")
def export_notes_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    zip_bytes = build_notes_export_zip(db, current_user)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="mdvault-notes.zip"'},
    )
