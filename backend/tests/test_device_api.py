"""HTTP-level integration tests for workspace-scoped device CRUD endpoints."""

from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_db_session
from app.api.devices import router as devices_router
from app.api.security import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    SESSION_COOKIE_NAME,
)
from app.core.config import Settings, get_settings
from app.core.csrf import generate_csrf_token
from app.modules.devices.services.exceptions import (
    DeviceInvalidInput,
    DeviceNotFound,
    DevicePermissionDenied,
    DeviceTypeNotFound,
)


TEST_DATABASE_URL = (
    "postgresql+asyncpg://test_user:test_password@127.0.0.1:5432/test_db"
)
TEST_SECRET = "test-secret-key-that-is-at-least-32-characters"
TEST_ORIGIN = "https://example.com"
TEST_SESSION = "device-api-test-session"
API_PREFIX = "/api/v1"
_UNSET = object()


def make_device(**overrides):
    """Build a response-compatible device object."""
    now = datetime.now(timezone.utc)
    values = {
        "id": uuid4(),
        "workspace_id": uuid4(),
        "device_type_id": uuid4(),
        "device_uid": "sensor-001",
        "name": "Temperature Sensor",
        "manufacturer": "Example",
        "model": "T-100",
        "protocol": "mqtt",
        "is_enabled": True,
        "lifecycle_status": "pending_provisioning",
        "created_at": now,
        "updated_at": now,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@contextmanager
def client_context(current_user=_UNSET):
    """Create an isolated API app with mocked database dependencies."""
    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        secret_key=TEST_SECRET,
        trusted_origins=[TEST_ORIGIN],
    )
    db_session = AsyncMock()
    app = FastAPI()
    app.include_router(devices_router, prefix=API_PREFIX)

    async def override_db_session():
        yield db_session

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db_session] = override_db_session

    if current_user is not _UNSET:
        async def override_current_user():
            return current_user

        app.dependency_overrides[get_current_user] = override_current_user

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def set_session_csrf(client):
    token = generate_csrf_token(
        TEST_SECRET,
        session_binding=TEST_SESSION,
    )
    client.cookies.set(SESSION_COOKIE_NAME, TEST_SESSION)
    client.cookies.set(CSRF_COOKIE_NAME, token)
    return token


def trusted_headers(token):
    return {
        "Origin": TEST_ORIGIN,
        CSRF_HEADER_NAME: token,
    }


def create_payload(**overrides):
    values = {
        "device_type_id": str(uuid4()),
        "device_uid": "sensor-001",
        "name": "Temperature Sensor",
        "manufacturer": "Example",
        "model": "T-100",
        "protocol": "mqtt",
    }
    values.update(overrides)
    return values


def test_create_device_returns_created_device(monkeypatch):
    from app.api import devices as devices_module

    user = SimpleNamespace(id=uuid4())
    workspace_id = uuid4()
    device = make_device(workspace_id=workspace_id)
    service = SimpleNamespace(
        create_device=AsyncMock(return_value=device)
    )
    monkeypatch.setattr(
        devices_module,
        "DeviceService",
        lambda: service,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        response = client.post(
            f"{API_PREFIX}/workspaces/{workspace_id}/devices",
            json=create_payload(),
            headers=trusted_headers(token),
        )

    assert response.status_code == 201
    assert response.json()["id"] == str(device.id)
    assert response.json()["workspace_id"] == str(workspace_id)
    assert response.json()["device_uid"] == device.device_uid
    assert response.json()["name"] == device.name

    service.create_device.assert_awaited_once()
    kwargs = service.create_device.await_args.kwargs
    assert kwargs["actor_id"] == user.id
    assert kwargs["workspace_id"] == workspace_id
    assert kwargs["device_uid"] == "sensor-001"


def test_create_device_rejects_missing_csrf(monkeypatch):
    from app.api import devices as devices_module

    service = SimpleNamespace(create_device=AsyncMock())
    monkeypatch.setattr(
        devices_module,
        "DeviceService",
        lambda: service,
    )

    user = SimpleNamespace(id=uuid4())
    workspace_id = uuid4()

    with client_context(user) as client:
        client.cookies.set(SESSION_COOKIE_NAME, TEST_SESSION)
        response = client.post(
            f"{API_PREFIX}/workspaces/{workspace_id}/devices",
            json=create_payload(),
            headers={"Origin": TEST_ORIGIN},
        )

    assert response.status_code == 403
    service.create_device.assert_not_awaited()


def test_create_device_rejects_untrusted_origin(monkeypatch):
    from app.api import devices as devices_module

    service = SimpleNamespace(create_device=AsyncMock())
    monkeypatch.setattr(
        devices_module,
        "DeviceService",
        lambda: service,
    )

    user = SimpleNamespace(id=uuid4())
    workspace_id = uuid4()

    with client_context(user) as client:
        token = set_session_csrf(client)
        response = client.post(
            f"{API_PREFIX}/workspaces/{workspace_id}/devices",
            json=create_payload(),
            headers={
                CSRF_HEADER_NAME: token,
                "Origin": "https://untrusted.example",
            },
        )

    assert response.status_code == 403
    service.create_device.assert_not_awaited()


def test_create_device_rejects_invalid_request_body(monkeypatch):
    from app.api import devices as devices_module

    service = SimpleNamespace(create_device=AsyncMock())
    monkeypatch.setattr(
        devices_module,
        "DeviceService",
        lambda: service,
    )

    user = SimpleNamespace(id=uuid4())
    workspace_id = uuid4()

    with client_context(user) as client:
        token = set_session_csrf(client)
        response = client.post(
            f"{API_PREFIX}/workspaces/{workspace_id}/devices",
            json=create_payload(name="", unexpected="field"),
            headers=trusted_headers(token),
        )

    assert response.status_code == 422
    service.create_device.assert_not_awaited()


def test_create_device_maps_missing_device_type_to_404(monkeypatch):
    from app.api import devices as devices_module

    service = SimpleNamespace(
        create_device=AsyncMock(side_effect=DeviceTypeNotFound())
    )
    monkeypatch.setattr(
        devices_module,
        "DeviceService",
        lambda: service,
    )

    user = SimpleNamespace(id=uuid4())
    workspace_id = uuid4()

    with client_context(user) as client:
        token = set_session_csrf(client)
        response = client.post(
            f"{API_PREFIX}/workspaces/{workspace_id}/devices",
            json=create_payload(),
            headers=trusted_headers(token),
        )

    assert response.status_code == 404


def test_list_devices_returns_workspace_devices(monkeypatch):
    from app.api import devices as devices_module

    user = SimpleNamespace(id=uuid4())
    workspace_id = uuid4()
    devices = [
        make_device(workspace_id=workspace_id),
        make_device(workspace_id=workspace_id),
    ]
    service = SimpleNamespace(
        list_devices=AsyncMock(return_value=devices)
    )
    monkeypatch.setattr(
        devices_module,
        "DeviceService",
        lambda: service,
    )

    with client_context(user) as client:
        response = client.get(
            f"{API_PREFIX}/workspaces/{workspace_id}/devices",
            params={"limit": 25, "offset": 10},
        )

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["workspace_id"] == str(workspace_id)

    service.list_devices.assert_awaited_once()
    kwargs = service.list_devices.await_args.kwargs
    assert kwargs["actor_id"] == user.id
    assert kwargs["workspace_id"] == workspace_id
    assert kwargs["limit"] == 25
    assert kwargs["offset"] == 10


def test_list_devices_uses_default_pagination(monkeypatch):
    from app.api import devices as devices_module

    service = SimpleNamespace(
        list_devices=AsyncMock(return_value=[])
    )
    monkeypatch.setattr(
        devices_module,
        "DeviceService",
        lambda: service,
    )

    workspace_id = uuid4()

    with client_context(SimpleNamespace(id=uuid4())) as client:
        response = client.get(
            f"{API_PREFIX}/workspaces/{workspace_id}/devices"
        )

    assert response.status_code == 200
    kwargs = service.list_devices.await_args.kwargs
    assert kwargs["limit"] == 100
    assert kwargs["offset"] == 0


def test_list_devices_rejects_invalid_pagination(monkeypatch):
    from app.api import devices as devices_module

    service = SimpleNamespace(
        list_devices=AsyncMock(return_value=[])
    )
    monkeypatch.setattr(
        devices_module,
        "DeviceService",
        lambda: service,
    )

    workspace_id = uuid4()

    with client_context(SimpleNamespace(id=uuid4())) as client:
        response = client.get(
            f"{API_PREFIX}/workspaces/{workspace_id}/devices",
            params={"limit": 0, "offset": -1},
        )

    assert response.status_code == 422
    service.list_devices.assert_not_awaited()


def test_get_device_returns_device(monkeypatch):
    from app.api import devices as devices_module

    user = SimpleNamespace(id=uuid4())
    workspace_id = uuid4()
    device = make_device(workspace_id=workspace_id)
    service = SimpleNamespace(
        get_device=AsyncMock(return_value=device)
    )
    monkeypatch.setattr(
        devices_module,
        "DeviceService",
        lambda: service,
    )

    with client_context(user) as client:
        response = client.get(
            f"{API_PREFIX}/workspaces/{workspace_id}/devices/{device.id}"
        )

    assert response.status_code == 200
    assert response.json()["id"] == str(device.id)
    assert response.json()["name"] == device.name

    kwargs = service.get_device.await_args.kwargs
    assert kwargs["actor_id"] == user.id
    assert kwargs["workspace_id"] == workspace_id
    assert kwargs["device_id"] == device.id


def test_get_device_maps_not_found_to_404(monkeypatch):
    from app.api import devices as devices_module

    service = SimpleNamespace(
        get_device=AsyncMock(side_effect=DeviceNotFound())
    )
    monkeypatch.setattr(
        devices_module,
        "DeviceService",
        lambda: service,
    )

    workspace_id = uuid4()
    device_id = uuid4()

    with client_context(SimpleNamespace(id=uuid4())) as client:
        response = client.get(
            f"{API_PREFIX}/workspaces/{workspace_id}/devices/{device_id}"
        )

    assert response.status_code == 404


def test_get_device_maps_permission_denied_to_403(monkeypatch):
    from app.api import devices as devices_module

    service = SimpleNamespace(
        get_device=AsyncMock(side_effect=DevicePermissionDenied())
    )
    monkeypatch.setattr(
        devices_module,
        "DeviceService",
        lambda: service,
    )

    workspace_id = uuid4()
    device_id = uuid4()

    with client_context(SimpleNamespace(id=uuid4())) as client:
        response = client.get(
            f"{API_PREFIX}/workspaces/{workspace_id}/devices/{device_id}"
        )

    assert response.status_code == 403


def test_update_device_returns_updated_device(monkeypatch):
    from app.api import devices as devices_module

    user = SimpleNamespace(id=uuid4())
    workspace_id = uuid4()
    device = make_device(
        workspace_id=workspace_id,
        name="Updated Sensor",
    )
    service = SimpleNamespace(
        update_device=AsyncMock(return_value=device)
    )
    monkeypatch.setattr(
        devices_module,
        "DeviceService",
        lambda: service,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        response = client.patch(
            f"{API_PREFIX}/workspaces/{workspace_id}/devices/{device.id}",
            json={"name": "Updated Sensor"},
            headers=trusted_headers(token),
        )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Sensor"

    kwargs = service.update_device.await_args.kwargs
    assert kwargs["actor_id"] == user.id
    assert kwargs["workspace_id"] == workspace_id
    assert kwargs["device_id"] == device.id
    assert kwargs["changes"] == {"name": "Updated Sensor"}


def test_update_device_rejects_missing_csrf(monkeypatch):
    from app.api import devices as devices_module

    service = SimpleNamespace(update_device=AsyncMock())
    monkeypatch.setattr(
        devices_module,
        "DeviceService",
        lambda: service,
    )

    workspace_id = uuid4()
    device_id = uuid4()

    with client_context(SimpleNamespace(id=uuid4())) as client:
        client.cookies.set(SESSION_COOKIE_NAME, TEST_SESSION)
        response = client.patch(
            f"{API_PREFIX}/workspaces/{workspace_id}/devices/{device_id}",
            json={"name": "Changed Name"},
            headers={"Origin": TEST_ORIGIN},
        )

    assert response.status_code == 403
    service.update_device.assert_not_awaited()


def test_update_device_rejects_invalid_request_body(monkeypatch):
    from app.api import devices as devices_module

    service = SimpleNamespace(update_device=AsyncMock())
    monkeypatch.setattr(
        devices_module,
        "DeviceService",
        lambda: service,
    )

    workspace_id = uuid4()
    device_id = uuid4()

    with client_context(SimpleNamespace(id=uuid4())) as client:
        token = set_session_csrf(client)
        response = client.patch(
            f"{API_PREFIX}/workspaces/{workspace_id}/devices/{device_id}",
            json={"name": "", "unsupported": True},
            headers=trusted_headers(token),
        )

    assert response.status_code == 422
    service.update_device.assert_not_awaited()


def test_update_device_maps_invalid_input_to_422(monkeypatch):
    from app.api import devices as devices_module

    service = SimpleNamespace(
        update_device=AsyncMock(
            side_effect=DeviceInvalidInput("Invalid device name.")
        )
    )
    monkeypatch.setattr(
        devices_module,
        "DeviceService",
        lambda: service,
    )

    workspace_id = uuid4()
    device_id = uuid4()

    with client_context(SimpleNamespace(id=uuid4())) as client:
        token = set_session_csrf(client)
        response = client.patch(
            f"{API_PREFIX}/workspaces/{workspace_id}/devices/{device_id}",
            json={"name": "Changed Name"},
            headers=trusted_headers(token),
        )

    assert response.status_code == 422


def test_device_api_rejects_unauthenticated_request():
    workspace_id = uuid4()

    with client_context() as client:
        response = client.get(
            f"{API_PREFIX}/workspaces/{workspace_id}/devices"
        )

    assert response.status_code == 401
