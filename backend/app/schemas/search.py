from pydantic import BaseModel

from app.schemas.note import NoteRead


class SearchResult(BaseModel):
    note: NoteRead
    rank: float
