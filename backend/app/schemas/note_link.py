from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NoteLinkRead(BaseModel):
    id: UUID
    source_note_id: UUID
    target_note_id: UUID | None
    raw_title: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BacklinkRead(BaseModel):
    id: UUID
    source_note_id: UUID
    source_note_title: str
    raw_title: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
