"""Business logic for workspace creation and management."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User, Workspace, WorkspaceMember
from app.modules.users.services.membership.repository import MembershipRepository
from app.modules.users.services.authorization.authorization_service import (
    AuthorizationService,
    PermissionDenied,
    WorkspaceMembershipNotFound,
)
from app.modules.users.services.authorization.permissions import Permission


class WorkspaceCreatorNotActive(Exception):
    """Raised when the requested workspace creator is not an active user."""


class WorkspaceNotFound(Exception):
    """Raised when the requested workspace does not exist."""


class WorkspacePermissionDenied(Exception):
    """Raised when the actor lacks workspace permission."""


class WorkspaceService:
    """Create a workspace and its initial owner in the caller's transaction."""

    def __init__(self) -> None:
        self.repository = MembershipRepository()
        self.authorization = AuthorizationService()

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

    async def _authorize(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        permission: Permission,
    ):
        try:
            return await self.authorization.authorize(
                session,
                user_id=actor_id,
                workspace_id=workspace_id,
                permission=permission,
            )
        except (WorkspaceMembershipNotFound, PermissionDenied) as exc:
            raise WorkspacePermissionDenied from exc

    async def get_workspace(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
    ) -> Workspace:
        """Read workspace details after checking workspace.read."""
        workspace = await self.repository.get_workspace(
            session,
            workspace_id=workspace_id,
        )
        if workspace is None:
            raise WorkspaceNotFound

        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.WORKSPACE_READ,
        )
        return workspace

    async def update_workspace(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        changes: dict[str, str | None],
    ) -> Workspace:
        """Update supplied fields and append an audit record."""
        # Check permission before acquiring the workspace lock.
        workspace = await self.repository.get_workspace(
            session,
            workspace_id=workspace_id,
        )
        if workspace is None:
            raise WorkspaceNotFound

        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.WORKSPACE_UPDATE,
        )

        # Serialize workspace changes with membership mutations.
        workspace = await self.repository.get_workspace_for_update(
            session,
            workspace_id=workspace_id,
        )
        if workspace is None:
            raise WorkspaceNotFound

        # Re-check permission after acquiring the lock. Membership
        # changes using the same lock can no longer race with this update.
        await self._authorize(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.WORKSPACE_UPDATE,
        )

        allowed_fields = {"name", "description", "timezone"}
        if not changes or not set(changes).issubset(allowed_fields):
            raise ValueError("Invalid workspace update fields.")

        changed_fields: dict[str, dict[str, str | None]] = {}
        for field, new_value in changes.items():
            old_value = getattr(workspace, field)
            if old_value != new_value:
                setattr(workspace, field, new_value)
                changed_fields[field] = {
                    "old": old_value,
                    "new": new_value,
                }

        if changed_fields:
            await self.repository.add_audit_log(
                session,
                workspace_id=workspace.id,
                actor_id=actor_id,
                action="workspace.updated",
                resource_type="workspace",
                resource_id=workspace.id,
                details={"changed_fields": changed_fields},
            )
            await session.flush()

        return workspace
