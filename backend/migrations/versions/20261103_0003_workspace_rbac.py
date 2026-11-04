"""Add fixed workspace RBAC roles.

Revision ID: 20261103_0003
Revises: 20261103_0002
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20261103_0003"
down_revision: Union[str, None] = "20261103_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_workspace_members_role",
        "workspace_members",
        type_="check",
    )

    op.execute(
        "UPDATE workspace_members SET role = 'viewer' WHERE role = 'member'"
    )

    op.create_check_constraint(
        "ck_workspace_members_role",
        "workspace_members",
        "role IN ('owner', 'admin', 'operator', 'viewer')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_workspace_members_role",
        "workspace_members",
        type_="check",
    )

    op.execute(
        "UPDATE workspace_members "
        "SET role = 'member' "
        "WHERE role IN ('operator', 'viewer')"
    )

    op.create_check_constraint(
        "ck_workspace_members_role",
        "workspace_members",
        "role IN ('owner', 'admin', 'member')",
    )
