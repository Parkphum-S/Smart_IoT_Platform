"""PostgreSQL integration tests for device credential and MQTT route constraints."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.devices.models import DeviceCredential
from app.integrations.mqtt.models import MQTTTopicRoute
from factories import (
    create_device,
    create_device_type,
    create_workspace,
    create_workspace_with_owner,
)


async def create_device_context(session):
    workspace, _, _ = await create_workspace_with_owner(session)
    device_type = await create_device_type(session)
    device = await create_device(
        session,
        workspace=workspace,
        device_type=device_type,
    )
    return workspace, device


def credential_values(workspace_id, device_id, **overrides):
    values = {
        "workspace_id": workspace_id,
        "device_id": device_id,
        "broker_key": "integration-broker",
        "credential_identifier": "integration-credential",
        "credential_type": "password",
        "secret_hash": "integration-secret-hash",
        "secret_reference": None,
        "credential_status": "pending",
    }
    values.update(overrides)
    return values


def route_values(workspace_id, device_id, **overrides):
    values = {
        "workspace_id": workspace_id,
        "device_id": device_id,
        "broker_key": "integration-broker",
        "topic": "integration/device/telemetry",
        "direction": "subscribe",
        "qos": 0,
        "is_enabled": True,
    }
    values.update(overrides)
    return values


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"broker_key": " "}, id="empty-broker-key"),
        pytest.param(
            {"credential_identifier": " "},
            id="empty-credential-identifier",
        ),
        pytest.param({"credential_type": " "}, id="empty-credential-type"),
        pytest.param(
            {"secret_hash": None, "secret_reference": None},
            id="missing-both-secrets",
        ),
        pytest.param(
            {"secret_reference": "vault://integration/secret"},
            id="both-secret-fields-present",
        ),
        pytest.param({"credential_status": "invalid"}, id="invalid-status"),
        pytest.param(
            {
                "created_at": datetime.now(timezone.utc),
                "expires_at": datetime.now(timezone.utc) - timedelta(days=1),
            },
            id="expiry-before-creation",
        ),
        pytest.param(
            {"credential_status": "revoked"},
            id="revoked-without-revocation-timestamp",
        ),
        pytest.param(
            {
                "credential_status": "active",
                "revoked_at": datetime.now(timezone.utc),
            },
            id="active-with-revocation-timestamp",
        ),
    ],
)
async def test_device_credential_check_constraints(
    db_session,
    overrides,
):
    workspace, device = await create_device_context(db_session)

    credential = DeviceCredential(
        **credential_values(workspace.id, device.id, **overrides)
    )

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(credential)
            await db_session.flush()


async def test_device_credential_composite_workspace_fk(db_session):
    workspace, device = await create_device_context(db_session)
    other_workspace = await create_workspace(db_session)

    credential = DeviceCredential(
        **credential_values(
            other_workspace.id,
            device.id,
        )
    )

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(credential)
            await db_session.flush()


async def test_device_credential_broker_identifier_unique(db_session):
    workspace, device = await create_device_context(db_session)

    first = DeviceCredential(
        **credential_values(workspace.id, device.id)
    )
    db_session.add(first)
    await db_session.flush()

    duplicate = DeviceCredential(
        **credential_values(workspace.id, device.id)
    )

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(duplicate)
            await db_session.flush()


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"broker_key": " "}, id="empty-broker-key"),
        pytest.param({"direction": "invalid"}, id="invalid-direction"),
        pytest.param({"qos": -1}, id="qos-below-range"),
        pytest.param({"qos": 3}, id="qos-above-range"),
        pytest.param({"topic": " "}, id="empty-topic"),
        pytest.param({"topic": "devices/+/telemetry"}, id="topic-plus-wildcard"),
        pytest.param({"topic": "devices/#"}, id="topic-hash-wildcard"),
    ],
)
async def test_mqtt_topic_route_check_constraints(db_session, overrides):
    workspace, device = await create_device_context(db_session)

    route = MQTTTopicRoute(
        **route_values(workspace.id, device.id, **overrides)
    )

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(route)
            await db_session.flush()


async def test_mqtt_topic_route_composite_workspace_fk(db_session):
    workspace, device = await create_device_context(db_session)
    other_workspace = await create_workspace(db_session)

    route = MQTTTopicRoute(
        **route_values(other_workspace.id, device.id)
    )

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(route)
            await db_session.flush()


async def test_mqtt_topic_route_broker_topic_direction_unique(db_session):
    workspace, device = await create_device_context(db_session)

    first = MQTTTopicRoute(
        **route_values(workspace.id, device.id)
    )
    db_session.add(first)
    await db_session.flush()

    duplicate = MQTTTopicRoute(
        **route_values(workspace.id, device.id)
    )

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(duplicate)
            await db_session.flush()


async def test_valid_device_credential_and_mqtt_route(db_session):
    workspace, device = await create_device_context(db_session)

    credential = DeviceCredential(
        **credential_values(workspace.id, device.id)
    )
    route = MQTTTopicRoute(
        **route_values(workspace.id, device.id)
    )

    db_session.add_all([credential, route])
    await db_session.flush()

    assert credential.id is not None
    assert route.id is not None
