"""Append-only audit logging for device-domain operations."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.monitoring.models import AuditLog


class DeviceAuditRepository:
    """Write audit events without committing the request transaction."""

    async def record(
        self,
        session: AsyncSession,
        *,
        workspace_id: UUID,
        actor_id: UUID,
        action: str,
        resource_type: str,
        resource_id: UUID,
        details: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            workspace_id=workspace_id,
            actor_type="user",
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
        )
        session.add(entry)
        await session.flush()
        return entry
