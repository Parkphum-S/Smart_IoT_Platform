"""Integration test fixtures and fail-closed database safety guard."""

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.database_guard import validate_test_database_settings
from app.infrastructure.database.session import create_database_engine


EXPECTED_DATABASE = "smart_iot_integration_test"
EXPECTED_APP_ROLE = "smart_iot_test_app"
EXPECTED_MIGRATOR_ROLE = "smart_iot_test_migrator"
EXPECTED_FIXTURE_ROLE = "smart_iot_test_fixture"
EXPECTED_OWNER_ROLE = "smart_iot_test_owner"


@pytest.fixture(scope='session', autouse=True)
def integration_database_guard():
    """Validate integration database isolation."""
    settings = get_settings()
    try:
        validate_test_database_settings(settings)
    except RuntimeError as exc:
        raise pytest.UsageError(str(exc)) from exc


@pytest.fixture
async def db_engine():
    """Create an engine for the approved integration database."""
    settings = get_settings()
    engine = create_database_engine(
        str(settings.database_url),
        pool_pre_ping=True,
    )

    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Provide a session isolated by an outer rollback-only transaction."""
    async with db_engine.connect() as connection:
        outer_transaction = await connection.begin()

        try:
            session_factory = async_sessionmaker(
                bind=connection,
                class_=AsyncSession,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            )

            async with session_factory() as session:
                yield session
        finally:
            if outer_transaction.is_active:
                await outer_transaction.rollback()


@pytest.fixture
async def gateway_secret_concurrency_context():
    """Committed test records and independent sessions for PostgreSQL locking tests."""
    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.modules.devices.models import (
        Device,
        DeviceGateway,
        DeviceGatewayMember,
    )
    from app.modules.users.models import User, Workspace, WorkspaceMember
    from factories import (
        create_device,
        create_device_type,
        create_workspace_with_owner,
    )

    fixture_engine = None
    fixture_factory = None
    app_engine = None
    app_factory = None
    context = {}

    try:
        settings = get_settings()
        fixture_engine = create_database_engine(
            str(settings.fixture_database_url),
            pool_pre_ping=True,
        )
        fixture_factory = async_sessionmaker(
            bind=fixture_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        app_engine = create_database_engine(
            str(settings.database_url),
            pool_pre_ping=True,
        )
        app_factory = async_sessionmaker(
            bind=app_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with fixture_factory() as session:
            async with session.begin():
                workspace, owner, _ = await create_workspace_with_owner(session)
                device_type = await create_device_type(session)
                device = await create_device(
                    session,
                    workspace=workspace,
                    device_type=device_type,
                )
                second_gateway_device = await create_device(
                    session,
                    workspace=workspace,
                    device_type=device_type,
                )
                child_device = await create_device(
                    session,
                    workspace=workspace,
                    device_type=device_type,
                )

                gateway = DeviceGateway(
                    device_id=device.id,
                    workspace_id=workspace.id,
                    gateway_type="generic",
                    adapter_key="integration",
                    configuration={},
                )
                second_gateway = DeviceGateway(
                    device_id=second_gateway_device.id,
                    workspace_id=workspace.id,
                    gateway_type="generic",
                    adapter_key="integration",
                    configuration={},
                )
                session.add_all([gateway, second_gateway])
                await session.flush()

                context.update(
                    workspace_id=workspace.id,
                    owner_id=owner.id,
                    gateway_device_id=device.id,
                    second_gateway_device_id=second_gateway_device.id,
                    child_device_id=child_device.id,
                    device_type_id=device_type.id,
                )

        context["session_factory"] = app_factory
        yield context

    finally:
        try:
            if context and fixture_factory is not None:
                async with fixture_factory() as session:
                    async with session.begin():
                        await session.execute(
                            delete(DeviceGatewayMember).where(
                                DeviceGatewayMember.workspace_id
                                == context["workspace_id"]
                            )
                        )
                        await session.execute(
                            delete(DeviceGateway).where(
                                DeviceGateway.workspace_id == context["workspace_id"]
                            )
                        )
                        await session.execute(
                            delete(Device).where(
                                Device.workspace_id == context["workspace_id"]
                            )
                        )
                        await session.execute(
                            delete(WorkspaceMember).where(
                                WorkspaceMember.workspace_id == context["workspace_id"]
                            )
                        )
                        await session.execute(
                            delete(Workspace).where(
                                Workspace.id == context["workspace_id"]
                            )
                        )
                        await session.execute(
                            delete(User).where(
                                User.id == context["owner_id"]
                            )
                        )
                        from app.modules.devices.models import DeviceType

                        await session.execute(
                            delete(DeviceType).where(
                                DeviceType.id == context["device_type_id"]
                            )
                        )

        finally:
            try:
                if fixture_engine is not None:
                    await fixture_engine.dispose()
            finally:
                if app_engine is not None:
                    await app_engine.dispose()


@pytest.fixture
async def bootstrap_token_concurrency_context():
    """Committed bootstrap-token records and independent PostgreSQL sessions."""
    import hashlib
    import secrets
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.core.security import hash_password
    from app.modules.devices.models import (
        Device,
        DeviceBootstrapToken,
        DeviceCredential,
        DeviceType,
    )
    from app.modules.users.models import User, Workspace, WorkspaceMember
    from factories import (
        create_device,
        create_device_type,
        create_workspace_with_owner,
    )

    fixture_engine = None
    fixture_factory = None
    app_engine = None
    app_factory = None
    context = {}

    try:
        settings = get_settings()
        fixture_engine = create_database_engine(
            str(settings.fixture_database_url),
            pool_pre_ping=True,
        )
        fixture_factory = async_sessionmaker(
            bind=fixture_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        app_engine = create_database_engine(
            str(settings.database_url),
            pool_pre_ping=True,
        )
        app_factory = async_sessionmaker(
            bind=app_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with fixture_factory() as session:
            async with session.begin():
                workspace, owner, _ = await create_workspace_with_owner(session)
                device_type = await create_device_type(session)
                device = await create_device(
                    session,
                    workspace=workspace,
                    device_type=device_type,
                    lifecycle_status="pending_provisioning",
                    is_enabled=True,
                )

                bootstrap_token = secrets.token_urlsafe(32)
                token_hash = hashlib.sha256(
                    bootstrap_token.encode("utf-8")
                ).hexdigest()
                token = DeviceBootstrapToken(
                    workspace_id=workspace.id,
                    device_id=device.id,
                    token_hash=token_hash,
                    expires_at=datetime.now(timezone.utc)
                    + timedelta(minutes=15),
                )
                session.add(token)

                credential_password = "Enrollment-Test-Password"
                credential = DeviceCredential(
                    workspace_id=workspace.id,
                    device_id=device.id,
                    broker_key="integration-broker",
                    credential_identifier=f"dc_integration_{secrets.token_hex(8)}",
                    credential_type="mqtt_password",
                    secret_hash=hash_password(credential_password),
                    expires_at=datetime.now(timezone.utc)
                    + timedelta(minutes=15),
                    credential_status="pending",
                )
                session.add(credential)
                await session.flush()

                context.update(
                    workspace_id=workspace.id,
                    owner_id=owner.id,
                    device_type_id=device_type.id,
                    device_id=device.id,
                    token_id=token.id,
                    token_hash=token_hash,
                    bootstrap_token=bootstrap_token,
                    credential_id=credential.id,
                    broker_key=credential.broker_key,
                    credential_identifier=credential.credential_identifier,
                    credential_password=credential_password,
                )

        context["session_factory"] = app_factory
        yield context

    finally:
        try:
            if context and fixture_factory is not None:
                async with fixture_factory() as session:
                    async with session.begin():
                        await session.execute(
                            delete(DeviceCredential).where(
                                DeviceCredential.workspace_id
                                == context["workspace_id"]
                            )
                        )
                        await session.execute(
                            delete(DeviceBootstrapToken).where(
                                DeviceBootstrapToken.workspace_id
                                == context["workspace_id"]
                            )
                        )
                        await session.execute(
                            delete(Device).where(
                                Device.workspace_id == context["workspace_id"]
                            )
                        )
                        await session.execute(
                            delete(WorkspaceMember).where(
                                WorkspaceMember.workspace_id
                                == context["workspace_id"]
                            )
                        )
                        await session.execute(
                            delete(Workspace).where(
                                Workspace.id == context["workspace_id"]
                            )
                        )
                        await session.execute(
                            delete(User).where(
                                User.id == context["owner_id"]
                            )
                        )
                        await session.execute(
                            delete(DeviceType).where(
                                DeviceType.id == context["device_type_id"]
                            )
                        )

        finally:
            try:
                if fixture_engine is not None:
                    await fixture_engine.dispose()
            finally:
                if app_engine is not None:
                    await app_engine.dispose()
