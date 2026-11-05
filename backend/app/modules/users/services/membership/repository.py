"""Database repository for workspace membership management."""

from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.monitoring.models import AuditLog
from app.modules.users.models import (
    MembershipHistory,
    User,
    Workspace,
    WorkspaceMember,
)


class MembershipRepository:
    """Perform membership data access within the caller's transaction."""

    @staticmethod
    async def get_workspace(
        session: AsyncSession,
        *,
        workspace_id: UUID,
    ) -> Workspace | None:
        """Return a workspace without acquiring a write lock."""
        statement = select(Workspace).where(Workspace.id == workspace_id)
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_workspace_for_update(
        session: AsyncSession,
        *,
        workspace_id: UUID,
    ) -> Workspace | None:
        """Acquire a transaction-scoped workspace lock, then read the workspace."""
        lock_statement = select(
            func.pg_advisory_xact_lock(
                func.hashtextextended(str(workspace_id), 0)
            )
        )
        await session.execute(lock_statement)

        statement = select(Workspace).where(Workspace.id == workspace_id)
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_active_user(
        session: AsyncSession,
        *,
        user_id: UUID,
    ) -> User | None:
        """Return a registered active platform user."""
        statement = select(User).where(
            User.id == user_id,
            User.is_active.is_(True),
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_membership_by_user(
        session: AsyncSession,
        *,
        workspace_id: UUID,
        user_id: UUID,
        for_update: bool = False,
    ) -> WorkspaceMember | None:
        """Find a membership, including inactive records."""
        statement = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        if for_update:
            statement = statement.with_for_update()

        result = await session.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_membership_for_update(
        session: AsyncSession,
        *,
        workspace_id: UUID,
        membership_id: UUID,
    ) -> WorkspaceMember | None:
        """Find and lock a membership scoped to its workspace."""
        statement = (
            select(WorkspaceMember)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.id == membership_id,
            )
            .with_for_update()
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_memberships(
        session: AsyncSession,
        *,
        workspace_id: UUID,
        include_inactive: bool = False,
    ) -> list[WorkspaceMember]:
        """List workspace memberships, active only by default."""
        statement = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id
        )
        if not include_inactive:
            statement = statement.where(WorkspaceMember.is_active.is_(True))

        statement = statement.order_by(
            WorkspaceMember.joined_at,
            WorkspaceMember.id,
        )
        result = await session.execute(statement)
        return list(result.scalars().all())

    @staticmethod
    async def create_membership(
        session: AsyncSession,
        *,
        workspace_id: UUID,
        user_id: UUID,
        role: str,
    ) -> WorkspaceMember:
        """Add a membership and flush it without committing."""
        membership = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
            is_active=True,
        )
        session.add(membership)
        await session.flush()
        return membership

    @staticmethod
    async def get_latest_deactivation(
        session: AsyncSession,
        *,
        membership_id: UUID,
    ) -> MembershipHistory | None:
        """Return the latest deactivation event for role restoration."""
        statement = (
            select(MembershipHistory)
            .where(
                MembershipHistory.membership_id == membership_id,
                MembershipHistory.event_type == "deactivated",
            )
            .order_by(desc(MembershipHistory.event_sequence))
            .limit(1)
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def add_membership_history(
        session: AsyncSession,
        *,
        workspace_id: UUID,
        membership_id: UUID,
        actor_id: UUID | None,
        subject_user_id: UUID,
        event_type: str,
        previous_role: str | None = None,
        new_role: str | None = None,
        details: dict | None = None,
    ) -> MembershipHistory:
        """Append a permanent membership event without committing."""
        history = MembershipHistory(
            workspace_id=workspace_id,
            membership_id=membership_id,
            actor_id=actor_id,
            subject_user_id=subject_user_id,
            event_type=event_type,
            previous_role=previous_role,
            new_role=new_role,
            details=details or {},
        )
        session.add(history)
        await session.flush()
        return history

    @staticmethod
    async def add_audit_log(
        session: AsyncSession,
        *,
        workspace_id: UUID,
        actor_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: UUID | None,
        details: dict | None = None,
    ) -> AuditLog:
        """Append an audit event without committing."""
        audit_log = AuditLog(
            workspace_id=workspace_id,
            actor_type="user" if actor_id is not None else "system",
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
        )
        session.add(audit_log)
        await session.flush()
        return audit_log
