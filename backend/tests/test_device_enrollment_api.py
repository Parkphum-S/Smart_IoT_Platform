"""HTTP tests for the public device enrollment endpoint."""

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_db_session
from app.api.device_enrollment import router as enrollment_router
from app.core.config import Settings, get_settings
from app.modules.devices.services.exceptions import DeviceEnrollmentFailed
from app.modules.devices.services.device_enrollment_service import (
    DeviceEnrollmentResult,
)


TEST_DATABASE_URL = (
    "postgresql+asyncpg://test_user:test_password@127.0.0.1:5432/test_db"
)
TEST_BROKER_KEY = "test-broker"
API_PREFIX = "/api/v1"
ENROLLMENT_PATH = f"{API_PREFIX}/device-enrollment/enroll"


@contextmanager
def client_context(*, broker_key=TEST_BROKER_KEY):
    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        device_enrollment_broker_key=broker_key,
    )

    db_session = AsyncMock()
    app = FastAPI()
    app.include_router(enrollment_router, prefix=API_PREFIX)

    async def override_db_session():
        yield db_session

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db_session] = override_db_session

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def enrollment_payload(**overrides):
    payload = {
        "bootstrap_token": "bootstrap-test-token",
        "credential_identifier": "sensor-test-001",
        "password": "test-device-password",
    }
    payload.update(overrides)
    return payload


def test_enrollment_success_returns_safe_metadata(monkeypatch):
    from app.api import device_enrollment as enrollment_module

    result = DeviceEnrollmentResult(
        device_id=uuid4(),
        credential_id=uuid4(),
        lifecycle_status="active",
        credential_status="active",
    )
    service = SimpleNamespace(
        enroll_device=AsyncMock(return_value=result)
    )
    monkeypatch.setattr(
        enrollment_module,
        "DeviceEnrollmentService",
        lambda: service,
    )

    with client_context() as client:
        response = client.post(
            ENROLLMENT_PATH,
            json=enrollment_payload(),
        )

    assert response.status_code == 200
    assert response.json() == {
        "device_id": str(result.device_id),
        "credential_id": str(result.credential_id),
        "lifecycle_status": "active",
        "credential_status": "active",
    }

    kwargs = service.enroll_device.await_args.kwargs
    assert kwargs["bootstrap_token"] == "bootstrap-test-token"
    assert kwargs["broker_key"] == TEST_BROKER_KEY
    assert kwargs["credential_identifier"] == "sensor-test-001"
    assert kwargs["password"] == "test-device-password"


def test_enrollment_without_broker_key_returns_503(monkeypatch):
    from app.api import device_enrollment as enrollment_module

    service = SimpleNamespace(enroll_device=AsyncMock())
    monkeypatch.setattr(
        enrollment_module,
        "DeviceEnrollmentService",
        lambda: service,
    )

    with client_context(broker_key=None) as client:
        response = client.post(
            ENROLLMENT_PATH,
            json=enrollment_payload(),
        )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Device enrollment is unavailable."
    )
    service.enroll_device.assert_not_awaited()


def test_enrollment_failure_returns_generic_401(monkeypatch):
    from app.api import device_enrollment as enrollment_module

    service = SimpleNamespace(
        enroll_device=AsyncMock(
            side_effect=DeviceEnrollmentFailed(
                "Internal failure detail."
            )
        )
    )
    monkeypatch.setattr(
        enrollment_module,
        "DeviceEnrollmentService",
        lambda: service,
    )

    with client_context() as client:
        response = client.post(
            ENROLLMENT_PATH,
            json=enrollment_payload(),
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Device enrollment failed."
    assert "Internal failure detail." not in response.text
    service.enroll_device.assert_awaited_once()


def test_enrollment_rejects_client_controlled_broker_key(monkeypatch):
    from app.api import device_enrollment as enrollment_module

    service = SimpleNamespace(enroll_device=AsyncMock())
    monkeypatch.setattr(
        enrollment_module,
        "DeviceEnrollmentService",
        lambda: service,
    )

    with client_context() as client:
        response = client.post(
            ENROLLMENT_PATH,
            json=enrollment_payload(broker_key="attacker-controlled"),
        )

    assert response.status_code == 422
    service.enroll_device.assert_not_awaited()


def test_enrollment_rejects_missing_required_field(monkeypatch):
    from app.api import device_enrollment as enrollment_module

    service = SimpleNamespace(enroll_device=AsyncMock())
    monkeypatch.setattr(
        enrollment_module,
        "DeviceEnrollmentService",
        lambda: service,
    )

    payload = enrollment_payload()
    payload.pop("password")

    with client_context() as client:
        response = client.post(ENROLLMENT_PATH, json=payload)

    assert response.status_code == 422
    service.enroll_device.assert_not_awaited()


def test_enrollment_does_not_echo_secrets(monkeypatch):
    from app.api import device_enrollment as enrollment_module

    result = DeviceEnrollmentResult(
        device_id=uuid4(),
        credential_id=uuid4(),
        lifecycle_status="active",
        credential_status="active",
    )
    service = SimpleNamespace(
        enroll_device=AsyncMock(return_value=result)
    )
    monkeypatch.setattr(
        enrollment_module,
        "DeviceEnrollmentService",
        lambda: service,
    )

    payload = enrollment_payload()

    with client_context() as client:
        response = client.post(ENROLLMENT_PATH, json=payload)

    assert response.status_code == 200
    assert payload["bootstrap_token"] not in response.text
    assert payload["password"] not in response.text
    assert TEST_BROKER_KEY not in response.text
