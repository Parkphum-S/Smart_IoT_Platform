"""PostgreSQL HTTP integration tests for device enrollment."""

from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.api.device_enrollment import router as enrollment_router
from app.core.config import Settings, get_settings
from app.modules.devices.models import (
    Device,
    DeviceBootstrapToken,
    DeviceCredential,
)
from app.modules.monitoring.models import AuditLog


API_PREFIX = "/api/v1"
ENROLLMENT_PATH = f"{API_PREFIX}/device-enrollment/enroll"


def create_enrollment_app(context):
    """Create an HTTP app backed by the real integration database."""
    current_settings = get_settings()
    settings = Settings(
        _env_file=None,
        database_url=str(current_settings.database_url),
        device_enrollment_broker_key=context["broker_key"],
    )

    app = FastAPI()
    app.state.db_session_factory = context["session_factory"]
    app.include_router(enrollment_router, prefix=API_PREFIX)
    app.dependency_overrides[get_settings] = lambda: settings

    return app


def enrollment_payload(context, *, password=None):
    return {
        "bootstrap_token": context["bootstrap_token"],
        "credential_identifier": context["credential_identifier"],
        "password": password or context["credential_password"],
    }


@pytest.mark.asyncio
async def test_http_enrollment_commits_database_state_and_audit(
    bootstrap_token_concurrency_context,
):
    context = bootstrap_token_concurrency_context
    app = create_enrollment_app(context)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            ENROLLMENT_PATH,
            json=enrollment_payload(context),
        )

    assert response.status_code == 200
    body = response.json()

    assert body == {
        "device_id": str(context["device_id"]),
        "credential_id": str(context["credential_id"]),
        "lifecycle_status": "active",
        "credential_status": "active",
    }

    response_text = response.text
    assert context["bootstrap_token"] not in response_text
    assert context["credential_password"] not in response_text
    assert context["broker_key"] not in response_text
    assert context["token_hash"] not in response_text

    factory = context["session_factory"]
    async with factory() as session:
        token = await session.get(
            DeviceBootstrapToken,
            context["token_id"],
        )
        credential = await session.get(
            DeviceCredential,
            context["credential_id"],
        )
        device = await session.get(
            Device,
            context["device_id"],
        )
        audit = await session.scalar(
            select(AuditLog).where(
                AuditLog.workspace_id == context["workspace_id"],
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

        assert audit is not None
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
async def test_http_enrollment_rejects_reused_bootstrap_token(
    bootstrap_token_concurrency_context,
):
    context = bootstrap_token_concurrency_context
    app = create_enrollment_app(context)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        first = await client.post(
            ENROLLMENT_PATH,
            json=enrollment_payload(context),
        )
        second = await client.post(
            ENROLLMENT_PATH,
            json=enrollment_payload(context),
        )

    assert first.status_code == 200
    assert second.status_code == 401
    assert second.json()["detail"] == "Device enrollment failed."

    factory = context["session_factory"]
    async with factory() as session:
        token = await session.get(
            DeviceBootstrapToken,
            context["token_id"],
        )
        credential = await session.get(
            DeviceCredential,
            context["credential_id"],
        )
        device = await session.get(
            Device,
            context["device_id"],
        )
        audits = (
            await session.scalars(
                select(AuditLog).where(
                    AuditLog.workspace_id == context["workspace_id"],
                    AuditLog.action == "device.enrolled",
                    AuditLog.resource_id == context["device_id"],
                )
            )
        ).all()

        assert token is not None
        assert token.consumed_at is not None
        assert credential.credential_status == "active"
        assert device.lifecycle_status == "active"
        assert len(audits) == 1


@pytest.mark.asyncio
async def test_http_enrollment_invalid_password_preserves_pending_state(
    bootstrap_token_concurrency_context,
):
    context = bootstrap_token_concurrency_context
    app = create_enrollment_app(context)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            ENROLLMENT_PATH,
            json=enrollment_payload(
                context,
                password="Definitely-Wrong-Password",
            ),
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Device enrollment failed."
    assert context["bootstrap_token"] not in response.text
    assert "Definitely-Wrong-Password" not in response.text

    factory = context["session_factory"]
    async with factory() as session:
        token = await session.get(
            DeviceBootstrapToken,
            context["token_id"],
        )
        credential = await session.get(
            DeviceCredential,
            context["credential_id"],
        )
        device = await session.get(
            Device,
            context["device_id"],
        )
        audit = await session.scalar(
            select(AuditLog).where(
                AuditLog.workspace_id == context["workspace_id"],
                AuditLog.action == "device.enrolled",
                AuditLog.resource_id == context["device_id"],
            )
        )

        assert token is not None
        assert token.consumed_at is None
        assert credential.credential_status == "pending"
        assert device.lifecycle_status == "pending_provisioning"
        assert audit is None
