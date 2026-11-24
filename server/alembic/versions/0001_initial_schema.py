"""Initial Postgres schema for users, photos, and diary_entries.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-23 18:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create users, photos, and diary_entries tables with FKs and indexes."""
    op.create_table(
        "users",
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=True),
        sa.Column("role", sa.String(length=20), server_default="user", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "photos",
        sa.Column("photo_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("photo_id"),
    )
    op.create_index(op.f("ix_photos_user_id"), "photos", ["user_id"], unique=False)

    op.create_table(
        "diary_entries",
        sa.Column("entry_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("location", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("weather", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("mode", sa.String(length=20), server_default="auto", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("entry_id"),
    )
    op.create_index(op.f("ix_diary_entries_user_id"), "diary_entries", ["user_id"], unique=False)


def downgrade() -> None:
    """Drop diary_entries, photos, and users tables in reverse dependency order."""
    op.drop_index(op.f("ix_diary_entries_user_id"), table_name="diary_entries")
    op.drop_table("diary_entries")
    op.drop_index(op.f("ix_photos_user_id"), table_name="photos")
    op.drop_table("photos")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
