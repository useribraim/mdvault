from sqlalchemy import desc, func, literal_column, select
from sqlalchemy.orm import Session

from app.models.note import Note
from app.models.user import User

SEARCH_CONFIG = literal_column("'simple'")
TITLE_WEIGHT = literal_column("'A'")
BODY_WEIGHT = literal_column("'B'")


def notes_search_vector():
    title_vector = func.setweight(
        func.to_tsvector(SEARCH_CONFIG, func.coalesce(Note.title, "")),
        TITLE_WEIGHT,
    )
    body_vector = func.setweight(
        func.to_tsvector(SEARCH_CONFIG, func.coalesce(Note.body_markdown, "")),
        BODY_WEIGHT,
    )
    return title_vector.op("||")(body_vector)


def search_notes(
    db: Session,
    user: User,
    query_text: str,
    limit: int,
) -> list[dict[str, object]]:
    normalized_query = query_text.strip()
    if not normalized_query:
        return []

    search_query = func.websearch_to_tsquery(SEARCH_CONFIG, normalized_query)
    search_vector = notes_search_vector()
    rank = func.ts_rank_cd(search_vector, search_query).label("rank")

    statement = (
        select(Note, rank)
        .where(
            Note.user_id == user.id,
            Note.deleted_at.is_(None),
            search_vector.op("@@")(search_query),
        )
        .order_by(desc(rank), desc(Note.updated_at))
        .limit(limit)
    )

    return [
        {"note": note, "rank": float(score or 0)}
        for note, score in db.execute(statement).all()
    ]
