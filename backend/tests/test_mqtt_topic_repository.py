"""Unit tests for workspace-scoped MQTT topic route queries."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.integrations.mqtt.repository import MQTTTopicRouteRepository


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.execute = AsyncMock()
    return session


def compiled_statement(session):
    statement = session.execute.await_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    return str(compiled).lower(), compiled.params


@pytest.mark.asyncio
async def test_get_ingress_route_requires_active_enabled_device(
    mock_session,
):
    expected = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = expected
    mock_session.execute.return_value = result

    route = await MQTTTopicRouteRepository.get_ingress_route(
        mock_session,
        broker_key="main",
        topic="farm/zoneA/sensors",
    )

    sql, params = compiled_statement(mock_session)

    assert route is expected
    assert "join devices" in sql
    assert "devices.workspace_id = mqtt_topic_routes.workspace_id" in sql
    assert "devices.id = mqtt_topic_routes.device_id" in sql
    assert "mqtt_topic_routes.is_enabled is true" in sql
    assert "devices.is_enabled is true" in sql
    assert "devices.lifecycle_status =" in sql

    assert "main" in params.values()
    assert "farm/zoneA/sensors" in params.values()
    assert "subscribe" in params.values()
    assert "active" in params.values()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_get_egress_route_is_workspace_and_device_scoped(
    mock_session,
):
    workspace_id = uuid4()
    device_id = uuid4()

    expected = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = expected
    mock_session.execute.return_value = result

    route = await MQTTTopicRouteRepository.get_egress_route(
        mock_session,
        workspace_id=workspace_id,
        device_id=device_id,
        broker_key="main",
        topic="farm/zoneA/relay_01/control",
    )

    sql, params = compiled_statement(mock_session)

    assert route is expected
    assert "join devices" in sql
    assert "mqtt_topic_routes.workspace_id =" in sql
    assert "mqtt_topic_routes.device_id =" in sql
    assert "mqtt_topic_routes.direction =" in sql
    assert "devices.lifecycle_status =" in sql

    assert workspace_id in params.values()
    assert device_id in params.values()
    assert "main" in params.values()
    assert "farm/zoneA/relay_01/control" in params.values()
    assert "publish" in params.values()
    assert "active" in params.values()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_list_enabled_routes_returns_deterministic_results(
    mock_session,
):
    expected = [MagicMock(), MagicMock()]

    scalars = MagicMock()
    scalars.all.return_value = expected

    result = MagicMock()
    result.scalars.return_value = scalars
    mock_session.execute.return_value = result

    routes = await MQTTTopicRouteRepository.list_enabled_routes(
        mock_session,
        broker_key="main",
        direction="subscribe",
    )

    sql, params = compiled_statement(mock_session)

    assert routes == expected
    assert "join devices" in sql
    assert "order by mqtt_topic_routes.topic" in sql
    assert "mqtt_topic_routes.is_enabled is true" in sql
    assert "devices.is_enabled is true" in sql
    assert "devices.lifecycle_status =" in sql

    assert "main" in params.values()
    assert "subscribe" in params.values()
    assert "active" in params.values()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_list_enabled_routes_rejects_invalid_direction(
    mock_session,
):
    with pytest.raises(ValueError, match="Invalid MQTT route direction"):
        await MQTTTopicRouteRepository.list_enabled_routes(
            mock_session,
            broker_key="main",
            direction="invalid",
        )

    mock_session.execute.assert_not_awaited()
