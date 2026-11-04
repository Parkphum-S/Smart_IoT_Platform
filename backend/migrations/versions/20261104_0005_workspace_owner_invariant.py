"""Enforce exactly one active owner per workspace.

Revision ID: 20261104_0005
Revises: 20261104_0004
"""

from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261104_0005"
down_revision: Union[str, None] = "20261104_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # At most one active Owner per Workspace.
    op.create_index(
        "uq_workspace_members_active_owner",
        "workspace_members",
        ["workspace_id"],
        unique=True,
        postgresql_where=sa.text(
            "role = 'owner' AND is_active IS TRUE"
        ),
    )

    # Verify the final transaction state. Locking the Workspace row
    # serializes concurrent membership changes for the same Workspace.
    op.execute("""
        CREATE OR REPLACE FUNCTION enforce_workspace_active_owner()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $body$
        DECLARE
            target_workspace_id uuid;
        BEGIN
            IF TG_OP = 'UPDATE'
               AND OLD.workspace_id IS DISTINCT FROM NEW.workspace_id
            THEN
                RAISE EXCEPTION
                    'A workspace membership cannot be moved to another workspace'
                    USING
                        ERRCODE = '23514',
                        CONSTRAINT = 'ck_workspace_members_immutable_workspace';
            END IF;

            IF TG_OP = 'DELETE' THEN
                target_workspace_id := OLD.workspace_id;
            ELSE
                target_workspace_id := NEW.workspace_id;
            END IF;

            -- Acquire the same transaction-scoped lock used by MembershipRepository.
            PERFORM pg_advisory_xact_lock(
                hashtextextended(target_workspace_id::text, 0)
            );

            -- A Workspace may no longer exist if a future deletion workflow
            -- removes its dependent memberships in the same transaction.
            PERFORM id
            FROM workspaces
            WHERE id = target_workspace_id;

            IF NOT FOUND THEN
                RETURN NULL;
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM workspace_members
                WHERE workspace_id = target_workspace_id
                  AND role = 'owner'
                  AND is_active IS TRUE
            ) THEN
                RAISE EXCEPTION
                    'Workspace % must have at least one active owner',
                    target_workspace_id
                    USING
                        ERRCODE = '23514',
                        CONSTRAINT = 'ck_workspace_members_active_owner';
            END IF;

            RETURN NULL;
        END;
        $body$;
    """)

    # Deferred until transaction end so Workspace creation and Ownership
    # Transfer can perform multiple membership changes atomically.
    op.execute("""
        CREATE CONSTRAINT TRIGGER trg_workspace_members_active_owner
        AFTER INSERT OR UPDATE OR DELETE
        ON workspace_members
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE FUNCTION enforce_workspace_active_owner();
    """)


def downgrade() -> None:
    op.execute("""
        DROP TRIGGER IF EXISTS trg_workspace_members_active_owner
        ON workspace_members;
    """)

    op.execute("""
        DROP FUNCTION IF EXISTS enforce_workspace_active_owner();
    """)

    op.drop_index(
        "uq_workspace_members_active_owner",
        table_name="workspace_members",
    )
