import app.models  # noqa: F401
from app.db.base import Base


def test_initial_model_metadata_contains_expected_tables() -> None:
    assert sorted(Base.metadata.tables.keys()) == [
        "folders",
        "note_links",
        "notes",
        "users",
    ]
