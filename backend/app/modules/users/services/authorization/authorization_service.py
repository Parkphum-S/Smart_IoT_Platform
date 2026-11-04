"""Business logic for workspace authorization."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import WorkspaceMember
from app.modules.users.services.authorization.policy import has_permission
from app.modules.users.services.authorization.repository import (
    AuthorizationRepository,
)


class WorkspaceMembershipNotFound(Exception):
    """Raised when the user has no active membership in the workspace."""


class PermissionDenied(Exception):
    """Raised when the active member lacks the required permission."""


class AuthorizationService:
    """Authorize users within the scope of a specific workspace."""

    def __init__(self) -> None:
        self.repository = AuthorizationRepository()

    async def authorize(
        self,
        session: AsyncSession,
        *,
        user_id: UUID,
        workspace_id: UUID,
        permission: str,
    ) -> WorkspaceMember:
        """Return active membership when the requested permission is granted.

        Membership and user activity are checked before evaluating the role.
        Unknown roles and permissions are denied by the centralized policy.
        """
        membership = await self.repository.get_active_membership(
            session,
            user_id=user_id,
            workspace_id=workspace_id,
        )

        if membership is None:
            raise WorkspaceMembershipNotFound

        if not has_permission(membership.role, permission):
            raise PermissionDenied

        return membership
