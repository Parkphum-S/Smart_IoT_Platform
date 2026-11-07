"""Tests for application health check endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_app(monkeypatch):
    """Create an application with an isolated test database URL."""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://test_user:test_password@127.0.0.1:5432/test_db",
    )

    from app.core.config import get_settings
    get_settings.cache_clear()

    from app.main import create_app
    return create_app()


def test_health_endpoint_returns_healthy(test_app):
    """The liveness endpoint should return HTTP 200."""
    with TestClient(test_app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_health_endpoints_are_registered_in_openapi(test_app):
    """Both health endpoints should be documented in OpenAPI."""
    paths = test_app.openapi()["paths"]

    assert "/health" in paths
    assert "/health/ready" in paths
    assert "get" in paths["/health"]
    assert "get" in paths["/health/ready"]
