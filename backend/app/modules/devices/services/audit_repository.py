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
        actor_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: UUID,
        details: dict | None = None,
        actor_type: str = "user",
    ) -> AuditLog:
        if actor_type not in {"user", "device", "system"}:
            raise ValueError("Unsupported audit actor type.")

        if actor_type == "user" and actor_id is None:
            raise ValueError("User audit events require an actor ID.")

        entry = AuditLog(
            workspace_id=workspace_id,
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
        )
        session.add(entry)
        await session.flush()
        return entry
