"""Add server-side user sessions.

Revision ID: 20261103_0002
Revises: 20261103_0001
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20261103_0002"
down_revision: Union[str, None] = "20261103_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_sessions",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "expires_at > created_at",
            name="ck_user_sessions_expiry_after_creation",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "token_hash",
            name="uq_user_sessions_token_hash",
        ),
    )

    op.create_index(
        "ix_user_sessions_user_expires",
        "user_sessions",
        ["user_id", "expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_sessions_user_expires",
        table_name="user_sessions",
    )
    op.drop_table("user_sessions")
