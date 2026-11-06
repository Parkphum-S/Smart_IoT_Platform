"""Tests for the asynchronous migration engine lifecycle."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.infrastructure.database import migration_runner


class FakeConnection:
    def __init__(self, events, migration_error=None):
        self.events = events
        self.migration_error = migration_error

    async def exec_driver_sql(self, statement):
        self.events.append(("execute", statement))

    async def commit(self):
        self.events.append(("commit",))

    async def run_sync(self, callback):
        self.events.append(("run_sync", callback))

        if self.migration_error is not None:
            raise self.migration_error


class FakeConnectionContext:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        self.connection.events.append(("connect",))
        return self.connection

    async def __aexit__(self, exc_type, exc, tb):
        self.connection.events.append(("connection_exit",))
        return False


class FakeEngine:
    def __init__(self, connection, events):
        self.connection = connection
        self.events = events
        self.dispose = AsyncMock(
            side_effect=lambda: events.append(("dispose",))
        )

    def connect(self):
        return FakeConnectionContext(self.connection)


@pytest.mark.asyncio
async def test_migration_runtime_executes_in_correct_order(monkeypatch):
    events = []
    connection = FakeConnection(events)
    engine = FakeEngine(connection, events)

    factory_calls = []

    def fake_engine_factory(configuration, prefix, poolclass):
        factory_calls.append((configuration, prefix, poolclass))
        return engine

    monkeypatch.setattr(
        migration_runner,
        "async_engine_from_config",
        fake_engine_factory,
    )

    callback = lambda connection: None

    await migration_runner.run_migrations_with_engine(
        configuration={"sqlalchemy.echo": False},
        database_url="postgresql+asyncpg://test:test@localhost/test",
        database_role="smart_iot_test_owner",
        migration_callback=callback,
    )

    assert events == [
        ("connect",),
        ("execute", "SET ROLE smart_iot_test_owner"),
        ("commit",),
        ("run_sync", callback),
        ("connection_exit",),
        ("dispose",),
    ]

    assert len(factory_calls) == 1
    configuration, prefix, poolclass = factory_calls[0]

    assert configuration["sqlalchemy.url"].startswith(
        "postgresql+asyncpg://"
    )
    assert prefix == "sqlalchemy."
    assert poolclass is migration_runner.pool.NullPool

    engine.dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_migration_runtime_disposes_engine_when_migration_fails(
    monkeypatch,
):
    events = []
    migration_error = RuntimeError("migration failed")

    connection = FakeConnection(
        events,
        migration_error=migration_error,
    )
    engine = FakeEngine(connection, events)

    monkeypatch.setattr(
        migration_runner,
        "async_engine_from_config",
        lambda *args, **kwargs: engine,
    )

    with pytest.raises(RuntimeError, match="migration failed"):
        await migration_runner.run_migrations_with_engine(
            configuration={},
            database_url="postgresql+asyncpg://test:test@localhost/test",
            database_role="smart_iot_test_owner",
            migration_callback=lambda connection: None,
        )

    assert events[-2:] == [
        ("connection_exit",),
        ("dispose",),
    ]

    engine.dispose.assert_awaited_once()
