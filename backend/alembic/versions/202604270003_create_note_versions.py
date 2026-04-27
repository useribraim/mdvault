"""create note versions

Revision ID: 202604270003
Revises: 202604270002
Create Date: 2026-04-27 00:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "202604270003"
down_revision: str | None = "202604270002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "note_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body_markdown", sa.Text(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "reason IN ('created', 'updated', 'restored')",
            name=op.f("ck_note_versions_note_version_reason"),
        ),
        sa.ForeignKeyConstraint(
            ["note_id"],
            ["notes.id"],
            name=op.f("fk_note_versions_note_id_notes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_note_versions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_note_versions")),
    )
    op.create_index(op.f("ix_note_versions_note_id"), "note_versions", ["note_id"])
    op.create_index(
        "ix_note_versions_note_version",
        "note_versions",
        ["note_id", "version_number"],
        unique=True,
    )
    op.create_index(op.f("ix_note_versions_user_id"), "note_versions", ["user_id"])
    op.create_index("ix_note_versions_user_note", "note_versions", ["user_id", "note_id"])


def downgrade() -> None:
    op.drop_index("ix_note_versions_user_note", table_name="note_versions")
    op.drop_index(op.f("ix_note_versions_user_id"), table_name="note_versions")
    op.drop_index("ix_note_versions_note_version", table_name="note_versions")
    op.drop_index(op.f("ix_note_versions_note_id"), table_name="note_versions")
    op.drop_table("note_versions")
