"""PostgreSQL integration tests for atomic device enrollment."""

import pytest
from sqlalchemy import select

from app.modules.devices.models import (
    Device,
    DeviceBootstrapToken,
    DeviceCredential,
)
from app.modules.devices.services.device_enrollment_service import (
    DeviceEnrollmentService,
)
from app.modules.devices.services.exceptions import DeviceEnrollmentFailed
from app.modules.monitoring.models import AuditLog


async def verify_pending_state(context):
    """Verify enrollment records using a fresh database session."""
    factory = context["session_factory"]

    async with factory() as session:
        token = await session.scalar(
            select(DeviceBootstrapToken).where(
                DeviceBootstrapToken.id == context["token_id"]
            )
        )
        credential = await session.scalar(
            select(DeviceCredential).where(
                DeviceCredential.id == context["credential_id"]
            )
        )
        device = await session.scalar(
            select(Device).where(
                Device.id == context["device_id"]
            )
        )

        assert token is not None
        assert token.consumed_at is None
        assert token.revoked_at is None

        assert credential is not None
        assert credential.credential_status == "pending"

        assert device is not None
        assert device.lifecycle_status == "pending_provisioning"
        assert device.is_enabled is True


@pytest.mark.asyncio
async def test_enrollment_persists_all_state_changes_and_audit(
    bootstrap_token_concurrency_context,
):
    context = bootstrap_token_concurrency_context
    factory = context["session_factory"]
    service = DeviceEnrollmentService()

    async with factory() as session:
        async with session.begin():
            result = await service.enroll_device(
                session,
                bootstrap_token=context["bootstrap_token"],
                broker_key=context["broker_key"],
                credential_identifier=context["credential_identifier"],
                password=context["credential_password"],
            )

            assert result.device_id == context["device_id"]
            assert result.credential_id == context["credential_id"]
            assert result.lifecycle_status == "active"
            assert result.credential_status == "active"

    # Verify committed state in a separate session.
    async with factory() as session:
        token = await session.scalar(
            select(DeviceBootstrapToken).where(
                DeviceBootstrapToken.id == context["token_id"]
            )
        )
        credential = await session.scalar(
            select(DeviceCredential).where(
                DeviceCredential.id == context["credential_id"]
            )
        )
        device = await session.scalar(
            select(Device).where(
                Device.id == context["device_id"]
            )
        )
        audit = await session.scalar(
            select(AuditLog).where(
                AuditLog.action == "device.enrolled",
                AuditLog.resource_id == context["device_id"],
            )
        )

        assert token is not None
        assert token.consumed_at is not None

        assert credential is not None
        assert credential.credential_status == "active"

        assert device is not None
        assert device.lifecycle_status == "active"
        assert device.is_enabled is True

        assert audit is not None
        assert audit.actor_type == "device"
        assert audit.actor_id == context["device_id"]
        assert audit.resource_type == "device"
        assert audit.details == {
            "credential_id": str(context["credential_id"]),
            "broker_key": context["broker_key"],
        }

        audit_text = str(audit.details)
        assert context["bootstrap_token"] not in audit_text
        assert context["credential_password"] not in audit_text
        assert context["token_hash"] not in audit_text
        assert context["credential_identifier"] not in audit_text


@pytest.mark.asyncio
async def test_enrollment_audit_failure_rolls_back_all_mutations(
    bootstrap_token_concurrency_context,
):
    context = bootstrap_token_concurrency_context
    factory = context["session_factory"]
    service = DeviceEnrollmentService()

    async def fail_audit(*args, **kwargs):
        raise RuntimeError("Synthetic audit failure")

    service.audit.record = fail_audit

    with pytest.raises(RuntimeError, match="Synthetic audit failure"):
        async with factory() as session:
            async with session.begin():
                await service.enroll_device(
                    session,
                    bootstrap_token=context["bootstrap_token"],
                    broker_key=context["broker_key"],
                    credential_identifier=context["credential_identifier"],
                    password=context["credential_password"],
                )

    # All changes must have rolled back.
    await verify_pending_state(context)

    async with factory() as session:
        audit = await session.scalar(
            select(AuditLog).where(
                AuditLog.action == "device.enrolled",
                AuditLog.resource_id == context["device_id"],
            )
        )
        assert audit is None


@pytest.mark.asyncio
async def test_enrollment_invalid_password_does_not_mutate_records(
    bootstrap_token_concurrency_context,
):
    context = bootstrap_token_concurrency_context
    factory = context["session_factory"]
    service = DeviceEnrollmentService()

    with pytest.raises(DeviceEnrollmentFailed):
        async with factory() as session:
            async with session.begin():
                await service.enroll_device(
                    session,
                    bootstrap_token=context["bootstrap_token"],
                    broker_key=context["broker_key"],
                    credential_identifier=context["credential_identifier"],
                    password="Definitely-Wrong-Password",
                )

    await verify_pending_state(context)

    async with factory() as session:
        audit = await session.scalar(
            select(AuditLog).where(
                AuditLog.action == "device.enrolled",
                AuditLog.resource_id == context["device_id"],
            )
        )
        assert audit is None
