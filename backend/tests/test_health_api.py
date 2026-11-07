"""Tests for application health check endpoints."""

import pytest
from fastapi.testclient import TestClient


class FakeEngine:
    """Database engine substitute that never opens a real connection."""

    def __init__(self, state):
        self.state = state

    async def dispose(self):
        self.state["dispose_calls"] += 1


class FakeSession:
    """Async session substitute for readiness checks."""

    def __init__(self, state):
        self.state = state

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def execute(self, statement):
        self.state["execute_calls"] += 1

        if self.state["error"] is not None:
            raise self.state["error"]

        return None


@pytest.fixture
def test_app(monkeypatch):
    """Create an application with isolated database dependencies."""
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://test_user:test_password@127.0.0.1:5432/test_db",
    )

    from app.core.config import get_settings
    get_settings.cache_clear()

    state = {
        "execute_calls": 0,
        "dispose_calls": 0,
        "error": None,
    }

    import app.main as main_module

    def fake_create_database_engine(*args, **kwargs):
        return FakeEngine(state)

    def fake_create_session_factory(engine):
        def session_factory():
            return FakeSession(state)

        return session_factory

    monkeypatch.setattr(
        main_module,
        "create_database_engine",
        fake_create_database_engine,
    )
    monkeypatch.setattr(
        main_module,
        "create_session_factory",
        fake_create_session_factory,
    )

    try:
        yield main_module.create_app(), state
    finally:
        get_settings.cache_clear()


def test_health_endpoint_returns_healthy(test_app):
    """The liveness endpoint should not require a database query."""
    app, state = test_app

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    assert state["execute_calls"] == 0
    assert state["dispose_calls"] == 1


def test_readiness_endpoint_returns_ready_when_database_is_available(test_app):
    """The readiness endpoint should return ready when SELECT 1 succeeds."""
    app, state = test_app

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "connected",
    }
    assert state["execute_calls"] == 1
    assert state["dispose_calls"] == 1


def test_readiness_endpoint_returns_503_when_database_is_unavailable(test_app):
    """The readiness endpoint should return 503 when the query fails."""
    app, state = test_app
    state["error"] = RuntimeError("Database unavailable")

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "database": "unavailable",
    }
    assert state["execute_calls"] == 1
    assert state["dispose_calls"] == 1


def test_health_endpoints_are_registered_in_openapi(test_app):
    """Both health endpoints should be documented in OpenAPI."""
    app, _ = test_app
    paths = app.openapi()["paths"]

    assert "/health" in paths
    assert "/health/ready" in paths
    assert "get" in paths["/health"]
    assert "get" in paths["/health/ready"]
