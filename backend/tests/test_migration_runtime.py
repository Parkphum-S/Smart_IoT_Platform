"""Tests for the asynchronous migration engine lifecycle."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.infrastructure.database import migration_runner


class FakeConnection:
    def __init__(
        self,
        events,
        migration_error=None,
        execute_error=None,
        commit_error=None,
    ):
        self.events = events
        self.migration_error = migration_error
        self.execute_error = execute_error
        self.commit_error = commit_error

    async def exec_driver_sql(self, statement):
        self.events.append(("execute", statement))
        if self.execute_error is not None:
            raise self.execute_error

    async def commit(self):
        self.events.append(("commit",))
        if self.commit_error is not None:
            raise self.commit_error

    async def run_sync(self, callback):
        self.events.append(("run_sync", callback))

        if self.migration_error is not None:
            raise self.migration_error


class FakeConnectionContext:
    def __init__(self, connection, connect_error=None):
        self.connection = connection
        self.connect_error = connect_error

    async def __aenter__(self):
        self.connection.events.append(("connect",))
        if self.connect_error is not None:
            raise self.connect_error
        return self.connection

    async def __aexit__(self, exc_type, exc, tb):
        self.connection.events.append(("connection_exit",))
        return False


class FakeEngine:
    def __init__(self, connection, events, connect_error=None):
        self.connection = connection
        self.events = events
        self.connect_error = connect_error
        self.dispose = AsyncMock(
            side_effect=lambda: events.append(("dispose",))
        )

    def connect(self):
        return FakeConnectionContext(
            self.connection,
            connect_error=self.connect_error,
        )


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

    original_configuration = {"sqlalchemy.echo": False}
    expected_url = "postgresql+asyncpg://test:test@localhost/test"

    await migration_runner.run_migrations_with_engine(
        configuration=original_configuration,
        database_url=expected_url,
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

    assert configuration["sqlalchemy.url"] == expected_url
    assert original_configuration == {"sqlalchemy.echo": False}
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


@pytest.mark.asyncio
async def test_migration_runtime_disposes_engine_when_set_role_fails(
    monkeypatch,
):
    events = []
    error = RuntimeError("set role failed")
    connection = FakeConnection(events, execute_error=error)
    engine = FakeEngine(connection, events)

    monkeypatch.setattr(
        migration_runner,
        "async_engine_from_config",
        lambda *args, **kwargs: engine,
    )

    with pytest.raises(RuntimeError, match="set role failed"):
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


@pytest.mark.asyncio
async def test_migration_runtime_disposes_engine_when_commit_fails(
    monkeypatch,
):
    events = []
    error = RuntimeError("commit failed")
    connection = FakeConnection(events, commit_error=error)
    engine = FakeEngine(connection, events)

    monkeypatch.setattr(
        migration_runner,
        "async_engine_from_config",
        lambda *args, **kwargs: engine,
    )

    with pytest.raises(RuntimeError, match="commit failed"):
        await migration_runner.run_migrations_with_engine(
            configuration={},
            database_url="postgresql+asyncpg://test:test@localhost/test",
            database_role="smart_iot_test_owner",
            migration_callback=lambda connection: None,
        )

    assert ("run_sync",) not in events
    assert events[-2:] == [
        ("connection_exit",),
        ("dispose",),
    ]
    engine.dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_migration_runtime_disposes_engine_when_connect_fails(
    monkeypatch,
):
    events = []
    error = RuntimeError("connect failed")
    connection = FakeConnection(events)
    engine = FakeEngine(connection, events, connect_error=error)

    monkeypatch.setattr(
        migration_runner,
        "async_engine_from_config",
        lambda *args, **kwargs: engine,
    )

    with pytest.raises(RuntimeError, match="connect failed"):
        await migration_runner.run_migrations_with_engine(
            configuration={},
            database_url="postgresql+asyncpg://test:test@localhost/test",
            database_role="smart_iot_test_owner",
            migration_callback=lambda connection: None,
        )

    assert events == [("connect",), ("dispose",)]
    engine.dispose.assert_awaited_once()
