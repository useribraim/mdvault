from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NoteVersionRead(BaseModel):
    id: UUID
    note_id: UUID
    title: str
    body_markdown: str
    version_number: int
    reason: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
