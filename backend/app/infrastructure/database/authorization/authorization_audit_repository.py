"""Append-only audit persistence for migration authorization lifecycle."""

from typing import Any
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.monitoring.models import AuditLog

from .authorization_errors import AuthorizationPersistenceError


AUTHORIZATION_RESOURCE_TYPE = "migration_authorization"

AUTHORIZATION_AUDIT_ACTIONS = frozenset({
    "authorization.issued",
    "authorization.claimed",
    "authorization.execution_started",
    "authorization.succeeded",
    "authorization.failed",
    "authorization.unknown",
    "authorization.recovery_unresolved",
    "authorization.expired",
})


class AuthorizationAuditRepository:
    """Persist authorization audit events in the caller's transaction."""

    async def record(
        self,
        session: AsyncSession,
        *,
        authorization_id: UUID,
        action: str,
        details: dict[str, Any] | None = None,
        workspace_id: UUID | None = None,
        actor_id: UUID | None = None,
    ) -> AuditLog:
        """Append one authorization lifecycle event."""

        if action not in AUTHORIZATION_AUDIT_ACTIONS:
            raise ValueError("Unsupported authorization audit action.")

        if not isinstance(authorization_id, UUID):
            raise ValueError("Authorization ID must be a UUID.")

        entry = AuditLog(
            workspace_id=workspace_id,
            actor_type="system",
            actor_id=actor_id,
            action=action,
            resource_type=AUTHORIZATION_RESOURCE_TYPE,
            resource_id=authorization_id,
            details=dict(details) if details is not None else {},
        )

        try:
            session.add(entry)
            await session.flush()
            return entry
        except SQLAlchemyError as exc:
            raise AuthorizationPersistenceError(
                "Could not persist authorization audit event."
            ) from exc
