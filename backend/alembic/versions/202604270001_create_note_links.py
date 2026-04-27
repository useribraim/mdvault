"""create note links

Revision ID: 202604270001
Revises: 202604260001
Create Date: 2026-04-27 00:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "202604270001"
down_revision: str | None = "202604260001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "note_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_note_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_note_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("raw_title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('resolved', 'unresolved', 'ambiguous')",
            name=op.f("ck_note_links_note_link_status"),
        ),
        sa.ForeignKeyConstraint(
            ["source_note_id"],
            ["notes.id"],
            name=op.f("fk_note_links_source_note_id_notes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_note_id"],
            ["notes.id"],
            name=op.f("fk_note_links_target_note_id_notes"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_note_links_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_note_links")),
    )
    op.create_index(op.f("ix_note_links_source_note_id"), "note_links", ["source_note_id"])
    op.create_index(op.f("ix_note_links_target_note_id"), "note_links", ["target_note_id"])
    op.create_index(op.f("ix_note_links_user_id"), "note_links", ["user_id"])
    op.create_index("ix_note_links_user_source", "note_links", ["user_id", "source_note_id"])
    op.create_index("ix_note_links_user_target", "note_links", ["user_id", "target_note_id"])


def downgrade() -> None:
    op.drop_index("ix_note_links_user_target", table_name="note_links")
    op.drop_index("ix_note_links_user_source", table_name="note_links")
    op.drop_index(op.f("ix_note_links_user_id"), table_name="note_links")
    op.drop_index(op.f("ix_note_links_target_note_id"), table_name="note_links")
    op.drop_index(op.f("ix_note_links_source_note_id"), table_name="note_links")
    op.drop_table("note_links")
