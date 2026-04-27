from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NoteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body_markdown: str = ""
    folder_id: UUID | None = None


class NoteUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    body_markdown: str | None = None
    folder_id: UUID | None = None


class NoteRead(BaseModel):
    id: UUID
    folder_id: UUID | None
    title: str
    body_markdown: str
    version_number: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
