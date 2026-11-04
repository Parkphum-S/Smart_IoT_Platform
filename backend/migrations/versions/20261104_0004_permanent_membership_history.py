"""Add permanent membership history and protect audit records.

Revision ID: 20261104_0004
Revises: 20261103_0003
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20261104_0004"
down_revision: Union[str, None] = "20261103_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Preserve audit records independently of workspace lifecycle.
    op.drop_constraint(
        "audit_logs_workspace_id_fkey",
        "audit_logs",
        type_="foreignkey",
    )

    op.create_table(
        "membership_history",
        sa.Column(
            "event_sequence",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("membership_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subject_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("previous_role", sa.String(length=20), nullable=True),
        sa.Column("new_role", sa.String(length=20), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('created', 'role_changed', 'deactivated', "
            "'reactivated', 'ownership_transferred')",
            name="ck_membership_history_event_type",
        ),
        sa.CheckConstraint(
            "previous_role IS NULL OR previous_role IN "
            "('owner', 'admin', 'operator', 'viewer')",
            name="ck_membership_history_previous_role",
        ),
        sa.CheckConstraint(
            "new_role IS NULL OR new_role IN "
            "('owner', 'admin', 'operator', 'viewer')",
            name="ck_membership_history_new_role",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_membership_history_workspace_created",
        "membership_history",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_membership_history_membership_created",
        "membership_history",
        ["membership_id", "created_at"],
    )
    op.create_index(
        "ix_membership_history_membership_sequence",
        "membership_history",
        ["membership_id", "event_sequence"],
    )
    op.create_index(
        "ix_membership_history_actor_created",
        "membership_history",
        ["actor_id", "created_at"],
    )
    op.create_index(
        "ix_membership_history_subject_created",
        "membership_history",
        ["subject_user_id", "created_at"],
    )

    # Reject row-level mutation and table truncation for permanent records.
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_permanent_audit_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $body$
        BEGIN
            RAISE EXCEPTION
                'Permanent audit records cannot be updated, deleted, or truncated'
                USING ERRCODE = '55000';
        END;
        $body$;
    """)

    for table_name in ("membership_history", "audit_logs"):
        op.execute(f"""
            CREATE TRIGGER trg_{table_name}_prevent_mutation
            BEFORE UPDATE OR DELETE ON {table_name}
            FOR EACH ROW
            EXECUTE FUNCTION prevent_permanent_audit_mutation();
        """)
        op.execute(f"""
            CREATE TRIGGER trg_{table_name}_prevent_truncate
            BEFORE TRUNCATE ON {table_name}
            FOR EACH STATEMENT
            EXECUTE FUNCTION prevent_permanent_audit_mutation();
        """)



def downgrade() -> None:
    raise RuntimeError(
        "Migration 20261104_0004 is irreversible: "
        "Membership History and AuditLog are permanent records. "
        "Downgrade would violate the permanent-retention policy."
    )
