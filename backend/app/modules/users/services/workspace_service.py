"""Business logic for creating workspaces."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User, Workspace, WorkspaceMember
from app.modules.users.services.membership.repository import MembershipRepository


class WorkspaceCreatorNotActive(Exception):
    """Raised when the requested workspace creator is not an active user."""


class WorkspaceService:
    """Create a workspace and its initial owner in the caller's transaction."""

    def __init__(self) -> None:
        self.repository = MembershipRepository()

    async def create_workspace(
        self,
        session: AsyncSession,
        *,
        creator_id: UUID,
        name: str,
        description: str | None,
        timezone: str,
    ) -> tuple[Workspace, WorkspaceMember]:
        """Create workspace, owner membership, history, and audit record.

        The request-level transaction owns commit/rollback.
        This method only flushes pending records and never commits.
        """
        creator: User | None = await self.repository.get_active_user(
            session,
            user_id=creator_id,
        )
        if creator is None:
            raise WorkspaceCreatorNotActive

        workspace = Workspace(
            name=name,
            description=description,
            timezone=timezone,
        )
        session.add(workspace)
        await session.flush()

        membership = await self.repository.create_membership(
            session,
            workspace_id=workspace.id,
            user_id=creator.id,
            role="owner",
        )

        await self.repository.add_membership_history(
            session,
            workspace_id=workspace.id,
            membership_id=membership.id,
            actor_id=creator.id,
            subject_user_id=creator.id,
            event_type="created",
            new_role="owner",
            details={"source": "workspace_creation"},
        )

        await self.repository.add_audit_log(
            session,
            workspace_id=workspace.id,
            actor_id=creator.id,
            action="workspace.created",
            resource_type="workspace",
            resource_id=workspace.id,
            details={
                "owner_user_id": str(creator.id),
                "workspace_name": workspace.name,
            },
        )

        return workspace, membership
