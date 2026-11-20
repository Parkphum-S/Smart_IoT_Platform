"""Unit tests for telemetry persistence operations."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.modules.telemetry.models import TelemetryReading
from app.modules.telemetry.repository import TelemetryRepository


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    return session


def compile_statement(session):
    statement = session.execute.await_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    return str(compiled).lower(), compiled.params


@pytest.mark.asyncio
async def test_get_metric_scopes_device_type_and_metric_key(mock_session):
    device_type_id = uuid4()
    expected = MagicMock()

    result = MagicMock()
    result.scalar_one_or_none.return_value = expected
    mock_session.execute.return_value = result

    metric = await TelemetryRepository.get_metric(
        mock_session,
        device_type_id=device_type_id,
        metric_key="temperature",
    )

    sql, params = compile_statement(mock_session)

    assert metric is expected
    assert "from telemetry_metrics" in sql
    assert "telemetry_metrics.device_type_id =" in sql
    assert "telemetry_metrics.metric_key =" in sql
    assert device_type_id in params.values()
    assert "temperature" in params.values()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_list_metrics_is_device_type_scoped_and_deterministic(
    mock_session,
):
    device_type_id = uuid4()
    expected = [MagicMock(), MagicMock()]

    result = MagicMock()
    result.scalars.return_value.all.return_value = expected
    mock_session.execute.return_value = result

    metrics = await TelemetryRepository.list_metrics(
        mock_session,
        device_type_id=device_type_id,
    )

    sql, params = compile_statement(mock_session)

    assert metrics == expected
    assert "from telemetry_metrics" in sql
    assert "telemetry_metrics.device_type_id =" in sql
    assert "order by telemetry_metrics.metric_key" in sql
    assert device_type_id in params.values()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_add_reading_flushes_without_commit(mock_session):
    workspace_id = uuid4()
    device_id = uuid4()
    device_type_id = uuid4()
    metric_id = uuid4()
    timestamp = datetime.now(timezone.utc)

    reading = await TelemetryRepository.add_reading(
        mock_session,
        workspace_id=workspace_id,
        device_id=device_id,
        device_type_id=device_type_id,
        metric_id=metric_id,
        recorded_at=timestamp,
        received_at=timestamp,
        value_numeric=Decimal("28.500000"),
    )

    assert isinstance(reading, TelemetryReading)
    assert reading.workspace_id == workspace_id
    assert reading.device_id == device_id
    assert reading.device_type_id == device_type_id
    assert reading.metric_id == metric_id
    assert reading.recorded_at == timestamp
    assert reading.received_at == timestamp
    assert reading.value_numeric == Decimal("28.500000")

    mock_session.add.assert_called_once_with(reading)
    mock_session.flush.assert_awaited_once()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_add_readings_flushes_batch_without_commit(mock_session):
    timestamp = datetime.now(timezone.utc)
    workspace_id = uuid4()
    device_id = uuid4()
    device_type_id = uuid4()

    common = {
        "workspace_id": workspace_id,
        "device_id": device_id,
        "device_type_id": device_type_id,
        "recorded_at": timestamp,
        "received_at": timestamp,
    }

    readings = await TelemetryRepository.add_readings(
        mock_session,
        readings=[
            {
                **common,
                "metric_id": uuid4(),
                "value_numeric": Decimal("28.5"),
            },
            {
                **common,
                "metric_id": uuid4(),
                "value_numeric": Decimal("65.2"),
            },
        ],
    )

    assert len(readings) == 2
    assert all(isinstance(item, TelemetryReading) for item in readings)
    mock_session.add_all.assert_called_once_with(readings)
    mock_session.flush.assert_awaited_once()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_add_readings_empty_batch_does_not_write(mock_session):
    readings = await TelemetryRepository.add_readings(
        mock_session,
        readings=[],
    )

    assert readings == []
    mock_session.add_all.assert_not_called()
    mock_session.flush.assert_not_awaited()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_add_readings_propagates_flush_failure(mock_session):
    mock_session.flush.side_effect = RuntimeError("flush failed")

    with pytest.raises(RuntimeError, match="flush failed"):
        await TelemetryRepository.add_readings(
            mock_session,
            readings=[
                {
                    "workspace_id": uuid4(),
                    "device_id": uuid4(),
                    "device_type_id": uuid4(),
                    "metric_id": uuid4(),
                    "recorded_at": datetime.now(timezone.utc),
                    "received_at": datetime.now(timezone.utc),
                    "value_numeric": Decimal("28.5"),
                }
            ],
        )

    mock_session.commit.assert_not_called()
