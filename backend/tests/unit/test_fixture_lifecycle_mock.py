"""Isolated lifecycle tests for integration fixtures.

All database engines, sessions, transactions and seed factories are mocked.
No PostgreSQL connection or application service is used.
"""

import asyncio
import importlib.util
import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest
import sqlalchemy.ext.asyncio as sqlalchemy_async


CONFTEST_PATH = (
    Path(__file__).resolve().parents[1]
    / "integration"
    / "conftest.py"
)

spec = importlib.util.spec_from_file_location(
    "bg13c_mock_conftest",
    CONFTEST_PATH,
)
conftest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(conftest)

FIXTURES = (
    "gateway_secret_concurrency_context",
    "bootstrap_token_concurrency_context",
)


class FakeEngine:
    def __init__(self, name, state, dispose_error=None):
        self.name = name
        self.state = state
        self.dispose_error = dispose_error

    async def dispose(self):
        self.state["dispose"].append(self.name)
        if self.dispose_error:
            raise self.dispose_error


class FakeTransaction:
    def __init__(self, state, role, number, error=None):
        self.state = state
        self.role = role
        self.number = number
        self.error = error

    async def __aenter__(self):
        self.state["transaction_enter"].append(
            (self.role, self.number)
        )
        if self.error:
            raise self.error
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.state["transaction_exit"].append(
            (self.role, self.number, exc_type is None)
        )
        return False


class FakeSession:
    def __init__(self, state, role):
        self.state = state
        self.role = role

    def begin(self):
        counts = self.state["begin_counts"]
        counts[self.role] += 1
        number = counts[self.role]

        error = None
        scenario = self.state["scenario"]

        if (
            scenario == "RT-05"
            and self.role == "fixture"
            and number == 1
        ):
            error = RuntimeError("injected seed transaction failure")

        if (
            scenario == "RT-07"
            and self.role == "fixture"
            and number == 2
        ):
            error = RuntimeError("injected cleanup transaction failure")

        self.state["begin_calls"].append((self.role, number))

        return FakeTransaction(
            self.state,
            self.role,
            number,
            error,
        )

    def add(self, obj):
        self.state["add"].append(
            (self.role, type(obj).__name__)
        )

    def add_all(self, objects):
        self.state["add_all"].append(
            (self.role, len(objects))
        )

    async def flush(self):
        self.state["flush"].append(self.role)

    async def execute(self, statement):
        self.state["execute"].append(self.role)


class FakeSessionContext:
    def __init__(self, state, role):
        self.state = state
        self.role = role

    async def __aenter__(self):
        self.state["session_enter"].append(self.role)
        return FakeSession(self.state, self.role)

    async def __aexit__(self, exc_type, exc, tb):
        self.state["session_exit"].append(
            (self.role, exc_type is None)
        )
        return False


class FakeSessionFactory:
    def __init__(self, state, role):
        self.state = state
        self.role = role

    def __call__(self):
        self.state["factory_calls"][self.role] += 1
        return FakeSessionContext(self.state, self.role)


class Harness:
    def __init__(self, monkeypatch, scenario):
        self.scenario = scenario

        self.state = {
            "scenario": scenario,
            "engine_attempts": [],
            "engines_created": [],
            "factory_attempts": [],
            "factory_calls": {
                "fixture": 0,
                "app": 0,
            },
            "session_enter": [],
            "session_exit": [],
            "begin_counts": {
                "fixture": 0,
                "app": 0,
            },
            "begin_calls": [],
            "transaction_enter": [],
            "transaction_exit": [],
            "execute": [],
            "flush": [],
            "add": [],
            "add_all": [],
            "dispose": [],
            "seed_helpers": [],
        }

        self.fixture_factory = FakeSessionFactory(
            self.state, "fixture"
        )
        self.app_factory = FakeSessionFactory(
            self.state, "app"
        )

        settings = SimpleNamespace(
            fixture_database_url="mock://fixture",
            database_url="mock://application",
        )

        monkeypatch.setattr(
            conftest,
            "get_settings",
            lambda: settings,
        )

        def create_engine(url, **kwargs):
            index = len(self.state["engine_attempts"]) + 1
            self.state["engine_attempts"].append(url)

            if scenario == "RT-01" and index == 1:
                raise RuntimeError(
                    "injected fixture engine creation failure"
                )

            if scenario == "RT-02" and index == 2:
                raise RuntimeError(
                    "injected app engine creation failure"
                )

            name = "fixture" if index == 1 else "app"

            dispose_error = None
            if scenario == "RT-08" and name == "fixture":
                dispose_error = RuntimeError(
                    "injected fixture dispose failure"
                )
            elif scenario == "RT-09" and name == "app":
                dispose_error = RuntimeError(
                    "injected app dispose failure"
                )

            engine = FakeEngine(
                name,
                self.state,
                dispose_error,
            )
            self.state["engines_created"].append(name)
            return engine

        monkeypatch.setattr(
            conftest,
            "create_database_engine",
            create_engine,
        )

        def create_factory(**kwargs):
            index = len(self.state["factory_attempts"]) + 1
            self.state["factory_attempts"].append(index)

            if scenario == "RT-03" and index == 1:
                raise RuntimeError(
                    "injected fixture factory creation failure"
                )

            if scenario == "RT-04" and index == 2:
                raise RuntimeError(
                    "injected app factory creation failure"
                )

            return (
                self.fixture_factory
                if index == 1
                else self.app_factory
            )

        # The fixture functions import this symbol locally.
        monkeypatch.setattr(
            sqlalchemy_async,
            "async_sessionmaker",
            create_factory,
        )

        # Load the integration factory module explicitly.
        import importlib.util
        import sys

        factory_path = (
            Path(__file__).resolve().parents[1]
            / "integration"
            / "factories.py"
        )

        factory_spec = importlib.util.spec_from_file_location(
            "factories",
            factory_path,
        )

        if factory_spec is None or factory_spec.loader is None:
            raise RuntimeError(
                f"Cannot load factory module: {factory_path}"
            )

        factories = importlib.util.module_from_spec(factory_spec)
        monkeypatch.setitem(sys.modules, "factories", factories)
        factory_spec.loader.exec_module(factories)

        async def create_workspace_with_owner(session):
            self.state["seed_helpers"].append(
                "create_workspace_with_owner"
            )
            return (
                SimpleNamespace(id=101),
                SimpleNamespace(id=201),
                None,
            )

        async def create_device_type(session):
            self.state["seed_helpers"].append(
                "create_device_type"
            )
            return SimpleNamespace(id=301)

        device_counter = {"value": 0}

        async def create_device(session, **kwargs):
            device_counter["value"] += 1
            self.state["seed_helpers"].append(
                "create_device"
            )
            return SimpleNamespace(
                id=400 + device_counter["value"]
            )

        monkeypatch.setattr(
            factories,
            "create_workspace_with_owner",
            create_workspace_with_owner,
        )
        monkeypatch.setattr(
            factories,
            "create_device_type",
            create_device_type,
        )
        monkeypatch.setattr(
            factories,
            "create_device",
            create_device,
        )

        # Prevent real password hashing in bootstrap fixture.
        import app.core.security as security

        monkeypatch.setattr(
            security,
            "hash_password",
            lambda value: "mock-hash",
        )


async def drive_fixture(fixture_name, harness, scenario):
    fixture = getattr(conftest, fixture_name)
    assert inspect.isasyncgenfunction(fixture.__wrapped__)

    generator = fixture.__wrapped__()

    if scenario in ("RT-06", "RT-07", "RT-08", "RT-09"):
        context = await anext(generator)

        assert context["session_factory"] is harness.app_factory

        injected = RuntimeError("injected runtime failure")

        try:
            await generator.athrow(injected)
        except RuntimeError as exc:
            return context, exc

        raise AssertionError(
            "Expected RuntimeError from async generator"
        )

    if scenario == "RT-10":
        context = await anext(generator)

        assert context["session_factory"] is harness.app_factory

        await generator.aclose()
        return context, None

    try:
        await anext(generator)
    except RuntimeError as exc:
        return None, exc

    raise AssertionError(
        f"{scenario}: expected setup failure"
    )


EXPECTED = {
    "RT-01": (
        "injected fixture engine creation failure",
        [],
        1,
        0,
        0,
    ),
    "RT-02": (
        "injected app engine creation failure",
        ["fixture"],
        2,
        1,
        0,
    ),
    "RT-03": (
        "injected fixture factory creation failure",
        ["fixture"],
        1,
        1,
        0,
    ),
    "RT-04": (
        "injected app factory creation failure",
        ["fixture", "app"],
        2,
        2,
        0,
    ),
    "RT-05": (
        "injected seed transaction failure",
        ["fixture", "app"],
        2,
        2,
        1,
    ),
    "RT-06": (
        "injected runtime failure",
        ["fixture", "app"],
        2,
        2,
        2,
    ),
    "RT-07": (
        "injected cleanup transaction failure",
        ["fixture", "app"],
        2,
        2,
        2,
    ),
    "RT-08": (
        "injected fixture dispose failure",
        ["fixture", "app"],
        2,
        2,
        2,
    ),
    "RT-09": (
        "injected app dispose failure",
        ["fixture", "app"],
        2,
        2,
        2,
    ),
    "RT-10": (
        None,
        ["fixture", "app"],
        2,
        2,
        2,
    ),
}


@pytest.mark.parametrize("fixture_name", FIXTURES)
@pytest.mark.parametrize(
    "scenario",
    [f"RT-{number:02d}" for number in range(1, 11)],
)
def test_fixture_lifecycle_mock(monkeypatch, fixture_name, scenario):
    harness = Harness(monkeypatch, scenario)

    (
        expected_error,
        expected_disposals,
        expected_engine_attempts,
        expected_factory_attempts,
        expected_fixture_sessions,
    ) = EXPECTED[scenario]

    context, error = asyncio.run(
        drive_fixture(fixture_name, harness, scenario)
    )

    # Exact exception behavior, including nested-finally propagation.
    if expected_error is None:
        assert error is None
    else:
        assert isinstance(error, RuntimeError)
        assert str(error) == expected_error

    state = harness.state

    # Engine and factory construction attempts.
    assert len(state["engine_attempts"]) == expected_engine_attempts
    assert len(state["factory_attempts"]) == expected_factory_attempts

    # No real engine is ever returned by the patched constructor.
    assert state["engines_created"] == (
        ["fixture", "app"][:len(state["engines_created"])]
    )

    # Every successfully created engine must be disposed exactly once.
    assert state["dispose"] == expected_disposals

    # App factory is assigned to Runtime Context but never invoked.
    assert state["factory_calls"]["app"] == 0

    if context is not None:
        assert context["session_factory"] is harness.app_factory

    # Seed and cleanup both use the Fixture factory.
    assert state["factory_calls"]["fixture"] == expected_fixture_sessions

    if scenario in ("RT-06", "RT-07", "RT-08", "RT-09", "RT-10"):
        assert context is not None
        assert len(state["seed_helpers"]) > 0
        assert len(state["session_enter"]) == 2
        assert len(state["session_exit"]) == 2
        assert state["begin_counts"]["fixture"] == 2
        assert len(state["execute"]) == (
            0 if scenario == "RT-07"
            else 7
        )

    if scenario == "RT-05":
        assert context is None
        assert state["begin_counts"]["fixture"] == 1
        assert state["factory_calls"]["fixture"] == 1
        assert state["execute"] == []

    if scenario in ("RT-06", "RT-08", "RT-09", "RT-10"):
        assert len(state["transaction_exit"]) == 2
        assert all(
            success
            for _, _, success in state["transaction_exit"]
        )

    if scenario == "RT-07":
        assert state["begin_counts"]["fixture"] == 2
        assert state["execute"] == []
        assert state["transaction_exit"] == [
            ("fixture", 1, True)
        ]

    # No application session may be opened by fixture setup/cleanup.
    assert state["factory_calls"]["app"] == 0
