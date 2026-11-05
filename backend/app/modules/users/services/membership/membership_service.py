"""Business logic for workspace membership lifecycle management."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.services.authorization.authorization_service import (
    AuthorizationService,
    PermissionDenied,
    WorkspaceMembershipNotFound,
)
from app.modules.users.services.authorization.permissions import (
    Permission,
    WorkspaceRole,
)
from app.modules.users.services.membership.exceptions import (
    DeactivationHistoryNotFound,
    InvalidRoleAssignment,
    MembershipAlreadyActive,
    MembershipAlreadyExists,
    MembershipInactive,
    MembershipNotFound,
    MembershipPermissionDenied,
    InvalidOwnershipTransferTarget,
    OwnerDeactivationProhibited,
    SelfManagementProhibited,
    UserNotFoundOrInactive,
    WorkspaceNotFound,
)
from app.modules.users.services.membership.repository import (
    MembershipRepository,
)


class MembershipService:
    """Manage workspace membership within the caller's transaction."""

    def __init__(self) -> None:
        self.repository = MembershipRepository()
        self.authorization = AuthorizationService()

    async def _authorize_actor(
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
            raise MembershipPermissionDenied from exc

    @staticmethod
    def _validate_role_assignment(
        *,
        actor_role: str,
        target_role: str,
    ) -> str:
        """Validate assignable roles independently of broad permissions."""
        try:
            actor = WorkspaceRole(actor_role)
            target = WorkspaceRole(target_role)
        except (TypeError, ValueError) as exc:
            raise InvalidRoleAssignment from exc

        if actor == WorkspaceRole.OWNER:
            allowed_targets = {
                WorkspaceRole.ADMIN,
                WorkspaceRole.OPERATOR,
                WorkspaceRole.VIEWER,
            }
        elif actor == WorkspaceRole.ADMIN:
            allowed_targets = {
                WorkspaceRole.OPERATOR,
                WorkspaceRole.VIEWER,
            }
        else:
            allowed_targets = set()

        if target not in allowed_targets:
            raise InvalidRoleAssignment

        return target.value

    @staticmethod
    def _validate_managed_target_role(*, actor_role: str, target_role: str) -> str:
        """Ensure the actor may manage the target's current or restored role."""
        try:
            actor = WorkspaceRole(actor_role)
            target = WorkspaceRole(target_role)
        except (TypeError, ValueError) as exc:
            raise InvalidRoleAssignment from exc

        if actor == WorkspaceRole.OWNER:
            allowed = {
                WorkspaceRole.ADMIN,
                WorkspaceRole.OPERATOR,
                WorkspaceRole.VIEWER,
            }
        elif actor == WorkspaceRole.ADMIN:
            allowed = {WorkspaceRole.OPERATOR, WorkspaceRole.VIEWER}
        else:
            allowed = set()

        if target not in allowed:
            raise InvalidRoleAssignment
        return target.value

    async def list_members(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        include_inactive: bool = False,
    ):
        """List workspace memberships after checking read permission."""
        await self._authorize_actor(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.MEMBERS_READ,
        )
        return await self.repository.list_memberships(
            session,
            workspace_id=workspace_id,
            include_inactive=include_inactive,
        )

    async def add_member(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
        role: str,
    ):
        """Add an active registered user to a workspace."""
        workspace = await self.repository.get_workspace_for_update(
            session,
            workspace_id=workspace_id,
        )
        if workspace is None:
            raise WorkspaceNotFound

        actor = await self._authorize_actor(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.MEMBERS_INVITE,
        )
        await self._authorize_actor(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.MEMBERS_ROLE_ASSIGN,
        )

        assigned_role = self._validate_role_assignment(
            actor_role=actor.role,
            target_role=role,
        )

        if actor_id == user_id:
            raise SelfManagementProhibited

        user = await self.repository.get_active_user(
            session,
            user_id=user_id,
        )
        if user is None:
            raise UserNotFoundOrInactive

        existing = await self.repository.get_membership_by_user(
            session,
            workspace_id=workspace_id,
            user_id=user_id,
            for_update=True,
        )
        if existing is not None:
            raise MembershipAlreadyExists

        membership = await self.repository.create_membership(
            session,
            workspace_id=workspace_id,
            user_id=user_id,
            role=assigned_role,
        )

        await self.repository.add_membership_history(
            session,
            workspace_id=workspace_id,
            membership_id=membership.id,
            actor_id=actor_id,
            subject_user_id=user_id,
            event_type="created",
            new_role=assigned_role,
        )
        await self.repository.add_audit_log(
            session,
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="membership.created",
            resource_type="workspace_member",
            resource_id=membership.id,
            details={
                "subject_user_id": str(user_id),
                "new_role": assigned_role,
            },
        )
        return membership

    async def change_role(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        membership_id: UUID,
        new_role: str,
    ):
        """Change a member's role subject to Owner/Admin management rules."""
        workspace = await self.repository.get_workspace_for_update(
            session,
            workspace_id=workspace_id,
        )
        if workspace is None:
            raise WorkspaceNotFound

        actor = await self._authorize_actor(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.MEMBERS_UPDATE,
        )
        await self._authorize_actor(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.MEMBERS_ROLE_ASSIGN,
        )

        membership = await self.repository.get_membership_for_update(
            session,
            workspace_id=workspace_id,
            membership_id=membership_id,
        )
        if membership is None:
            raise MembershipNotFound
        if not membership.is_active:
            raise MembershipInactive
        if membership.user_id == actor_id:
            raise SelfManagementProhibited

        self._validate_managed_target_role(
            actor_role=actor.role,
            target_role=membership.role,
        )

        previous_role = membership.role
        assigned_role = self._validate_role_assignment(
            actor_role=actor.role,
            target_role=new_role,
        )

        if previous_role == assigned_role:
            raise InvalidRoleAssignment

        membership.role = assigned_role
        await session.flush()

        await self.repository.add_membership_history(
            session,
            workspace_id=workspace_id,
            membership_id=membership.id,
            actor_id=actor_id,
            subject_user_id=membership.user_id,
            event_type="role_changed",
            previous_role=previous_role,
            new_role=assigned_role,
        )
        await self.repository.add_audit_log(
            session,
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="membership.role_changed",
            resource_type="workspace_member",
            resource_id=membership.id,
            details={
                "subject_user_id": str(membership.user_id),
                "previous_role": previous_role,
                "new_role": assigned_role,
            },
        )
        return membership

    async def deactivate_member(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        membership_id: UUID,
    ):
        """Deactivate one workspace membership without affecting the user account."""
        workspace = await self.repository.get_workspace_for_update(
            session, workspace_id=workspace_id
        )
        if workspace is None:
            raise WorkspaceNotFound

        actor = await self._authorize_actor(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.MEMBERS_DEACTIVATE,
        )

        membership = await self.repository.get_membership_for_update(
            session,
            workspace_id=workspace_id,
            membership_id=membership_id,
        )
        if membership is None:
            raise MembershipNotFound
        if not membership.is_active:
            raise MembershipInactive
        if membership.user_id == actor_id:
            raise SelfManagementProhibited
        if membership.role == WorkspaceRole.OWNER.value:
            raise OwnerDeactivationProhibited

        self._validate_managed_target_role(
            actor_role=actor.role,
            target_role=membership.role,
        )

        previous_role = membership.role
        membership.is_active = False
        await session.flush()

        await self.repository.add_membership_history(
            session,
            workspace_id=workspace_id,
            membership_id=membership.id,
            actor_id=actor_id,
            subject_user_id=membership.user_id,
            event_type="deactivated",
            previous_role=previous_role,
        )
        await self.repository.add_audit_log(
            session,
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="membership.deactivated",
            resource_type="workspace_member",
            resource_id=membership.id,
            details={
                "subject_user_id": str(membership.user_id),
                "previous_role": previous_role,
            },
        )
        return membership

    async def reactivate_member(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        membership_id: UUID,
    ):
        """Reactivate a membership using its latest deactivation role history."""
        workspace = await self.repository.get_workspace_for_update(
            session, workspace_id=workspace_id
        )
        if workspace is None:
            raise WorkspaceNotFound

        actor = await self._authorize_actor(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.MEMBERS_UPDATE,
        )

        membership = await self.repository.get_membership_for_update(
            session,
            workspace_id=workspace_id,
            membership_id=membership_id,
        )
        if membership is None:
            raise MembershipNotFound
        if membership.is_active:
            raise MembershipAlreadyActive
        if membership.user_id == actor_id:
            raise SelfManagementProhibited

        active_user = await self.repository.get_active_user(
            session, user_id=membership.user_id
        )
        if active_user is None:
            raise UserNotFoundOrInactive

        deactivation = await self.repository.get_latest_deactivation(
            session,
            membership_id=membership.id,
        )
        if deactivation is None or deactivation.previous_role is None:
            raise DeactivationHistoryNotFound

        restored_role = self._validate_managed_target_role(
            actor_role=actor.role,
            target_role=deactivation.previous_role,
        )

        previous_role = membership.role
        membership.role = restored_role
        membership.is_active = True
        await session.flush()

        await self.repository.add_membership_history(
            session,
            workspace_id=workspace_id,
            membership_id=membership.id,
            actor_id=actor_id,
            subject_user_id=membership.user_id,
            event_type="reactivated",
            previous_role=previous_role,
            new_role=restored_role,
        )
        await self.repository.add_audit_log(
            session,
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="membership.reactivated",
            resource_type="workspace_member",
            resource_id=membership.id,
            details={
                "subject_user_id": str(membership.user_id),
                "previous_role": previous_role,
                "restored_role": restored_role,
            },
        )
        return membership

    async def transfer_ownership(
        self,
        session: AsyncSession,
        *,
        actor_id: UUID,
        workspace_id: UUID,
        target_membership_id: UUID,
    ):
        """Transfer workspace ownership atomically to another active member."""
        workspace = await self.repository.get_workspace_for_update(
            session,
            workspace_id=workspace_id,
        )
        if workspace is None:
            raise WorkspaceNotFound

        actor = await self._authorize_actor(
            session,
            actor_id=actor_id,
            workspace_id=workspace_id,
            permission=Permission.OWNERSHIP_TRANSFER,
        )

        old_owner = await self.repository.get_membership_for_update(
            session,
            workspace_id=workspace_id,
            membership_id=actor.id,
        )
        if (
            old_owner is None
            or not old_owner.is_active
            or old_owner.user_id != actor_id
            or old_owner.role != WorkspaceRole.OWNER.value
        ):
            raise MembershipPermissionDenied

        new_owner = await self.repository.get_membership_for_update(
            session,
            workspace_id=workspace_id,
            membership_id=target_membership_id,
        )
        if (
            new_owner is None
            or not new_owner.is_active
            or new_owner.user_id == actor_id
            or new_owner.role not in {
                WorkspaceRole.ADMIN.value,
                WorkspaceRole.OPERATOR.value,
                WorkspaceRole.VIEWER.value,
            }
        ):
            raise InvalidOwnershipTransferTarget

        target_user = await self.repository.get_active_user(
            session,
            user_id=new_owner.user_id,
        )
        if target_user is None:
            raise InvalidOwnershipTransferTarget

        old_role = old_owner.role
        new_previous_role = new_owner.role

        old_owner.role = WorkspaceRole.ADMIN.value
        await session.flush()

        new_owner.role = WorkspaceRole.OWNER.value
        await session.flush()

        await self.repository.add_membership_history(
            session,
            workspace_id=workspace_id,
            membership_id=old_owner.id,
            actor_id=actor_id,
            subject_user_id=old_owner.user_id,
            event_type="ownership_transferred",
            previous_role=old_role,
            new_role=WorkspaceRole.ADMIN.value,
            details={"transferred_to_user_id": str(new_owner.user_id)},
        )
        await self.repository.add_membership_history(
            session,
            workspace_id=workspace_id,
            membership_id=new_owner.id,
            actor_id=actor_id,
            subject_user_id=new_owner.user_id,
            event_type="ownership_transferred",
            previous_role=new_previous_role,
            new_role=WorkspaceRole.OWNER.value,
            details={"transferred_from_user_id": str(old_owner.user_id)},
        )
        await self.repository.add_audit_log(
            session,
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="ownership.transferred",
            resource_type="workspace",
            resource_id=workspace_id,
            details={
                "previous_owner_user_id": str(old_owner.user_id),
                "new_owner_user_id": str(new_owner.user_id),
                "previous_owner_new_role": WorkspaceRole.ADMIN.value,
                "new_owner_previous_role": new_previous_role,
            },
        )

        return old_owner, new_owner
