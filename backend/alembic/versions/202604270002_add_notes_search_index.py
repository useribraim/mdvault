"""add notes search index

Revision ID: 202604270002
Revises: 202604270001
Create Date: 2026-04-27 00:00:00.000000
"""
from collections.abc import Sequence

from alembic import op


revision: str = "202604270002"
down_revision: str | None = "202604270001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX ix_notes_search_vector
        ON notes
        USING GIN (
            (
                setweight(to_tsvector('simple', coalesce(title, '')), 'A') ||
                setweight(to_tsvector('simple', coalesce(body_markdown, '')), 'B')
            )
        )
        WHERE deleted_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_notes_search_vector")
