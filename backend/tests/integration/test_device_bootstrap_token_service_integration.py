"""PostgreSQL integration tests for bootstrap token lifecycle service."""

import pytest
from sqlalchemy import delete, select

from app.modules.devices.models import DeviceBootstrapToken
from app.modules.devices.services.device_bootstrap_token_service import (
    DeviceBootstrapTokenService,
)
from app.modules.monitoring.models import AuditLog


@pytest.mark.asyncio
async def test_create_token_persists_hash_and_audit(
    bootstrap_token_concurrency_context,
):
    context = bootstrap_token_concurrency_context
    factory = context["session_factory"]
    service = DeviceBootstrapTokenService()

    async with factory() as session:
            async with session.begin():
                result = await service.create_token(
                    session,
                    actor_id=context["owner_id"],
                    workspace_id=context["workspace_id"],
                    device_id=context["device_id"],
                )

                assert result.token
                assert result.metadata.id is not None
                assert result.metadata.device_id == context["device_id"]

                stored = await session.scalar(
                    select(DeviceBootstrapToken).where(
                        DeviceBootstrapToken.id == result.metadata.id
                    )
                )

                assert stored is not None
                assert stored.token_hash != result.token
                assert len(stored.token_hash) == 64
                assert stored.expires_at > stored.created_at

                audit = await session.scalar(
                    select(AuditLog).where(
                        AuditLog.action == "device_bootstrap_token.created",
                        AuditLog.resource_id == stored.id,
                    )
                )

                assert audit is not None
                assert audit.actor_id == context["owner_id"]
                assert audit.resource_type == "device_bootstrap_token"
                assert audit.details["device_id"] == str(
                    context["device_id"]
                )
                assert result.token not in str(audit.details)
                assert stored.token_hash not in str(audit.details)


@pytest.mark.asyncio
async def test_revoke_token_persists_state_and_audit(
    bootstrap_token_concurrency_context,
):
    context = bootstrap_token_concurrency_context
    factory = context["session_factory"]
    service = DeviceBootstrapTokenService()

    async with factory() as session:
            async with session.begin():
                result = await service.revoke_token(
                    session,
                    actor_id=context["owner_id"],
                    workspace_id=context["workspace_id"],
                    token_id=context["token_id"],
                )

                assert result.id == context["token_id"]
                assert result.revoked_at is not None
                assert result.consumed_at is None

                stored = await session.scalar(
                    select(DeviceBootstrapToken).where(
                        DeviceBootstrapToken.id == context["token_id"]
                    )
                )

                assert stored is not None
                assert stored.revoked_at is not None
                assert stored.consumed_at is None

                audit = await session.scalar(
                    select(AuditLog).where(
                        AuditLog.action == "device_bootstrap_token.revoked",
                        AuditLog.resource_id == context["token_id"],
                    )
                )

                assert audit is not None
                assert audit.actor_id == context["owner_id"]
                assert audit.details == {
                    "device_id": str(context["device_id"])
                }


@pytest.mark.asyncio
async def test_create_token_rollback_removes_token_and_audit(
    bootstrap_token_concurrency_context,
):
    context = bootstrap_token_concurrency_context
    factory = context["session_factory"]
    service = DeviceBootstrapTokenService()

    async with factory() as session:
        transaction = await session.begin()

        result = await service.create_token(
            session,
            actor_id=context["owner_id"],
            workspace_id=context["workspace_id"],
            device_id=context["device_id"],
        )

        token_id = result.metadata.id
        await transaction.rollback()

    async with factory() as verification_session:
        stored_token = await verification_session.scalar(
            select(DeviceBootstrapToken).where(
                DeviceBootstrapToken.id == token_id
            )
        )

        stored_audit = await verification_session.scalar(
            select(AuditLog).where(
                AuditLog.action == "device_bootstrap_token.created",
                AuditLog.resource_id == token_id,
            )
        )

    assert stored_token is None
    assert stored_audit is None
