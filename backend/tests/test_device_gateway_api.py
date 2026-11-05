from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import devices as devices_module
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
    DeviceStateConflict,
    GatewayAlreadyRegistered,
    GatewayCycleDetected,
    GatewayMembershipConflict,
    GatewayNotFound,
    GatewaySecretAlreadyExists,
    GatewaySecretEncryptionUnavailable,
    GatewaySecretNotFound,
)


TEST_DATABASE_URL = (
    "postgresql+asyncpg://test_user:test_password@127.0.0.1:5432/test_db"
)
TEST_SECRET = "test-secret-key-that-is-at-least-32-characters"
TEST_ORIGIN = "https://example.com"
TEST_SESSION = "device-gateway-api-test-session"
API_PREFIX = "/api/v1"
_UNSET = object()


@contextmanager
def client_context(current_user=_UNSET):
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


def make_device(**overrides):
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


def make_gateway(**overrides):
    now = datetime.now(timezone.utc)
    values = {
        "device_id": uuid4(),
        "workspace_id": uuid4(),
        "gateway_type": "mqtt",
        "adapter_key": "generic-mqtt",
        "configuration": {"host": "broker.example.com"},
        "created_at": now,
        "updated_at": now,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def make_membership(**overrides):
    values = {
        "child_device_id": uuid4(),
        "workspace_id": uuid4(),
        "gateway_device_id": uuid4(),
        "created_at": datetime.now(timezone.utc),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def device_base_path(workspace_id):
    return f"{API_PREFIX}/workspaces/{workspace_id}/devices"


def assert_service_call(service_mock, **expected_kwargs):
    service_mock.assert_awaited_once()
    assert len(service_mock.await_args.args) == 1
    assert service_mock.await_args.kwargs == expected_kwargs


# ---------------------------------------------------------------------------
# Device lifecycle API
# ---------------------------------------------------------------------------


def test_change_lifecycle_success(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    device = make_device(lifecycle_status="active", is_enabled=True)
    service_mock = AsyncMock(return_value=device)
    monkeypatch.setattr(
        devices_module.DeviceService,
        "change_lifecycle",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(device.workspace_id)}/{device.id}/lifecycle"
        )
        response = client.post(
            path,
            json={"status": "active"},
            headers=trusted_headers(token),
        )

    assert response.status_code == 200
    assert response.json()["id"] == str(device.id)
    assert response.json()["lifecycle_status"] == "active"
    assert_service_call(
        service_mock,
        actor_id=user.id,
        workspace_id=device.workspace_id,
        device_id=device.id,
        new_status="active",
    )


def test_change_lifecycle_requires_csrf(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    device = make_device()
    service_mock = AsyncMock(return_value=device)
    monkeypatch.setattr(
        devices_module.DeviceService,
        "change_lifecycle",
        service_mock,
    )

    with client_context(user) as client:
        path = (
            f"{device_base_path(device.workspace_id)}/{device.id}/lifecycle"
        )
        response = client.post(
            path,
            json={"status": "active"},
            headers={"Origin": TEST_ORIGIN},
        )

    assert response.status_code == 403
    service_mock.assert_not_awaited()


def test_change_lifecycle_rejects_invalid_body(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    device = make_device()
    service_mock = AsyncMock(return_value=device)
    monkeypatch.setattr(
        devices_module.DeviceService,
        "change_lifecycle",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(device.workspace_id)}/{device.id}/lifecycle"
        )
        response = client.post(
            path,
            json={"status": "", "unexpected": True},
            headers=trusted_headers(token),
        )

    assert response.status_code == 422
    service_mock.assert_not_awaited()


def test_change_lifecycle_maps_invalid_input_to_422(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    device = make_device()
    service_mock = AsyncMock(side_effect=DeviceInvalidInput())
    monkeypatch.setattr(
        devices_module.DeviceService,
        "change_lifecycle",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(device.workspace_id)}/{device.id}/lifecycle"
        )
        response = client.post(
            path,
            json={"status": "unknown"},
            headers=trusted_headers(token),
        )

    assert response.status_code == 422
    service_mock.assert_awaited_once()


def test_change_lifecycle_maps_device_not_found_to_404(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    device = make_device()
    service_mock = AsyncMock(side_effect=DeviceNotFound())
    monkeypatch.setattr(
        devices_module.DeviceService,
        "change_lifecycle",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(device.workspace_id)}/{device.id}/lifecycle"
        )
        response = client.post(
            path,
            json={"status": "active"},
            headers=trusted_headers(token),
        )

    assert response.status_code == 404
    service_mock.assert_awaited_once()


def test_change_lifecycle_maps_state_conflict_to_409(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    device = make_device()
    service_mock = AsyncMock(side_effect=DeviceStateConflict())
    monkeypatch.setattr(
        devices_module.DeviceService,
        "change_lifecycle",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(device.workspace_id)}/{device.id}/lifecycle"
        )
        response = client.post(
            path,
            json={"status": "retired"},
            headers=trusted_headers(token),
        )

    assert response.status_code == 409
    service_mock.assert_awaited_once()


def test_change_lifecycle_maps_permission_denied_to_403(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    device = make_device()
    service_mock = AsyncMock(side_effect=DevicePermissionDenied())
    monkeypatch.setattr(
        devices_module.DeviceService,
        "change_lifecycle",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(device.workspace_id)}/{device.id}/lifecycle"
        )
        response = client.post(
            path,
            json={"status": "active"},
            headers=trusted_headers(token),
        )

    assert response.status_code == 403
    service_mock.assert_awaited_once()


# ---------------------------------------------------------------------------
# Gateway registration API
# ---------------------------------------------------------------------------


def test_register_gateway_success(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    gateway = make_gateway()
    service_mock = AsyncMock(return_value=gateway)
    monkeypatch.setattr(
        devices_module.GatewayService,
        "register_gateway",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(gateway.workspace_id)}"
            f"/{gateway.device_id}/gateway"
        )
        response = client.post(
            path,
            json={
                "gateway_type": gateway.gateway_type,
                "adapter_key": gateway.adapter_key,
                "configuration": gateway.configuration,
            },
            headers=trusted_headers(token),
        )

    assert response.status_code == 201
    assert response.json()["device_id"] == str(gateway.device_id)
    assert response.json()["gateway_type"] == "mqtt"
    assert response.json()["adapter_key"] == "generic-mqtt"
    assert response.json()["configuration"] == gateway.configuration
    assert_service_call(
        service_mock,
        actor_id=user.id,
        workspace_id=gateway.workspace_id,
        device_id=gateway.device_id,
        gateway_type=gateway.gateway_type,
        adapter_key=gateway.adapter_key,
        configuration=gateway.configuration,
    )


def test_register_gateway_requires_csrf(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    gateway = make_gateway()
    service_mock = AsyncMock(return_value=gateway)
    monkeypatch.setattr(
        devices_module.GatewayService,
        "register_gateway",
        service_mock,
    )

    with client_context(user) as client:
        path = (
            f"{device_base_path(gateway.workspace_id)}"
            f"/{gateway.device_id}/gateway"
        )
        response = client.post(
            path,
            json={
                "gateway_type": "mqtt",
                "adapter_key": "generic-mqtt",
                "configuration": {},
            },
            headers={"Origin": TEST_ORIGIN},
        )

    assert response.status_code == 403
    service_mock.assert_not_awaited()


def test_register_gateway_rejects_invalid_body(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    gateway = make_gateway()
    service_mock = AsyncMock(return_value=gateway)
    monkeypatch.setattr(
        devices_module.GatewayService,
        "register_gateway",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(gateway.workspace_id)}"
            f"/{gateway.device_id}/gateway"
        )
        response = client.post(
            path,
            json={
                "gateway_type": "",
                "adapter_key": "generic-mqtt",
                "unexpected": True,
            },
            headers=trusted_headers(token),
        )

    assert response.status_code == 422
    service_mock.assert_not_awaited()


def test_register_gateway_maps_device_not_found_to_404(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    gateway = make_gateway()
    service_mock = AsyncMock(side_effect=DeviceNotFound())
    monkeypatch.setattr(
        devices_module.GatewayService,
        "register_gateway",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(gateway.workspace_id)}"
            f"/{gateway.device_id}/gateway"
        )
        response = client.post(
            path,
            json={
                "gateway_type": "mqtt",
                "adapter_key": "generic-mqtt",
                "configuration": {},
            },
            headers=trusted_headers(token),
        )

    assert response.status_code == 404
    service_mock.assert_awaited_once()


def test_register_gateway_maps_already_registered_to_409(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    gateway = make_gateway()
    service_mock = AsyncMock(side_effect=GatewayAlreadyRegistered())
    monkeypatch.setattr(
        devices_module.GatewayService,
        "register_gateway",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(gateway.workspace_id)}"
            f"/{gateway.device_id}/gateway"
        )
        response = client.post(
            path,
            json={
                "gateway_type": "mqtt",
                "adapter_key": "generic-mqtt",
                "configuration": {},
            },
            headers=trusted_headers(token),
        )

    assert response.status_code == 409
    service_mock.assert_awaited_once()


def test_register_gateway_maps_invalid_input_to_422(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    gateway = make_gateway()
    service_mock = AsyncMock(side_effect=DeviceInvalidInput())
    monkeypatch.setattr(
        devices_module.GatewayService,
        "register_gateway",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(gateway.workspace_id)}"
            f"/{gateway.device_id}/gateway"
        )
        response = client.post(
            path,
            json={
                "gateway_type": "mqtt",
                "adapter_key": "generic-mqtt",
                "configuration": {},
            },
            headers=trusted_headers(token),
        )

    assert response.status_code == 422
    service_mock.assert_awaited_once()


def test_register_gateway_maps_permission_denied_to_403(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    gateway = make_gateway()
    service_mock = AsyncMock(side_effect=DevicePermissionDenied())
    monkeypatch.setattr(
        devices_module.GatewayService,
        "register_gateway",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(gateway.workspace_id)}"
            f"/{gateway.device_id}/gateway"
        )
        response = client.post(
            path,
            json={
                "gateway_type": "mqtt",
                "adapter_key": "generic-mqtt",
                "configuration": {},
            },
            headers=trusted_headers(token),
        )

    assert response.status_code == 403
    service_mock.assert_awaited_once()


# ---------------------------------------------------------------------------
# Gateway update API
# ---------------------------------------------------------------------------


def test_update_gateway_success(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    gateway = make_gateway(adapter_key="updated-mqtt")
    service_mock = AsyncMock(return_value=gateway)
    monkeypatch.setattr(
        devices_module.GatewayService,
        "update_gateway",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(gateway.workspace_id)}"
            f"/{gateway.device_id}/gateway"
        )
        response = client.patch(
            path,
            json={"adapter_key": "updated-mqtt"},
            headers=trusted_headers(token),
        )

    assert response.status_code == 200
    assert response.json()["device_id"] == str(gateway.device_id)
    assert response.json()["adapter_key"] == "updated-mqtt"
    assert_service_call(
        service_mock,
        actor_id=user.id,
        workspace_id=gateway.workspace_id,
        device_id=gateway.device_id,
        adapter_key="updated-mqtt",
    )


def test_update_gateway_requires_csrf(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    gateway = make_gateway()
    service_mock = AsyncMock(return_value=gateway)
    monkeypatch.setattr(
        devices_module.GatewayService,
        "update_gateway",
        service_mock,
    )

    with client_context(user) as client:
        path = (
            f"{device_base_path(gateway.workspace_id)}"
            f"/{gateway.device_id}/gateway"
        )
        response = client.patch(
            path,
            json={"adapter_key": "updated-mqtt"},
            headers={"Origin": TEST_ORIGIN},
        )

    assert response.status_code == 403
    service_mock.assert_not_awaited()


def test_update_gateway_empty_body_maps_conflict_to_409(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    gateway = make_gateway()
    service_mock = AsyncMock(side_effect=GatewayMembershipConflict())
    monkeypatch.setattr(
        devices_module.GatewayService,
        "update_gateway",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(gateway.workspace_id)}"
            f"/{gateway.device_id}/gateway"
        )
        response = client.patch(
            path,
            json={},
            headers=trusted_headers(token),
        )

    assert response.status_code == 409
    service_mock.assert_awaited_once()


def test_update_gateway_maps_not_found_to_404(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    gateway = make_gateway()
    service_mock = AsyncMock(side_effect=GatewayNotFound())
    monkeypatch.setattr(
        devices_module.GatewayService,
        "update_gateway",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(gateway.workspace_id)}"
            f"/{gateway.device_id}/gateway"
        )
        response = client.patch(
            path,
            json={"adapter_key": "updated-mqtt"},
            headers=trusted_headers(token),
        )

    assert response.status_code == 404
    service_mock.assert_awaited_once()


def test_update_gateway_maps_invalid_input_to_422(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    gateway = make_gateway()
    service_mock = AsyncMock(side_effect=DeviceInvalidInput())
    monkeypatch.setattr(
        devices_module.GatewayService,
        "update_gateway",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(gateway.workspace_id)}"
            f"/{gateway.device_id}/gateway"
        )
        response = client.patch(
            path,
            json={"gateway_type": "unsupported"},
            headers=trusted_headers(token),
        )

    assert response.status_code == 422
    assert_service_call(
        service_mock,
        actor_id=user.id,
        workspace_id=gateway.workspace_id,
        device_id=gateway.device_id,
        gateway_type="unsupported",
    )


def test_update_gateway_rejects_invalid_body(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    gateway = make_gateway()
    service_mock = AsyncMock(return_value=gateway)
    monkeypatch.setattr(
        devices_module.GatewayService,
        "update_gateway",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(gateway.workspace_id)}"
            f"/{gateway.device_id}/gateway"
        )
        response = client.patch(
            path,
            json={"gateway_type": ""},
            headers=trusted_headers(token),
        )

    assert response.status_code == 422
    service_mock.assert_not_awaited()


# ---------------------------------------------------------------------------
# Gateway membership assignment API
# ---------------------------------------------------------------------------


def test_assign_gateway_success(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    membership = make_membership()
    service_mock = AsyncMock(return_value=membership)
    monkeypatch.setattr(
        devices_module.GatewayService,
        "assign_gateway",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(membership.workspace_id)}"
            f"/{membership.child_device_id}/gateway-membership"
        )
        response = client.put(
            path,
            json={"gateway_device_id": str(membership.gateway_device_id)},
            headers=trusted_headers(token),
        )

    assert response.status_code == 201
    assert response.json()["child_device_id"] == str(
        membership.child_device_id
    )
    assert response.json()["gateway_device_id"] == str(
        membership.gateway_device_id
    )
    assert_service_call(
        service_mock,
        actor_id=user.id,
        workspace_id=membership.workspace_id,
        child_device_id=membership.child_device_id,
        gateway_device_id=membership.gateway_device_id,
    )


def test_assign_gateway_requires_csrf(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    membership = make_membership()
    service_mock = AsyncMock(return_value=membership)
    monkeypatch.setattr(
        devices_module.GatewayService,
        "assign_gateway",
        service_mock,
    )

    with client_context(user) as client:
        path = (
            f"{device_base_path(membership.workspace_id)}"
            f"/{membership.child_device_id}/gateway-membership"
        )
        response = client.put(
            path,
            json={"gateway_device_id": str(membership.gateway_device_id)},
            headers={"Origin": TEST_ORIGIN},
        )

    assert response.status_code == 403
    service_mock.assert_not_awaited()


def test_assign_gateway_rejects_invalid_uuid(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    membership = make_membership()
    service_mock = AsyncMock(return_value=membership)
    monkeypatch.setattr(
        devices_module.GatewayService,
        "assign_gateway",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(membership.workspace_id)}"
            f"/{membership.child_device_id}/gateway-membership"
        )
        response = client.put(
            path,
            json={"gateway_device_id": "not-a-valid-uuid"},
            headers=trusted_headers(token),
        )

    assert response.status_code == 422
    service_mock.assert_not_awaited()


def test_assign_gateway_maps_device_not_found_to_404(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    membership = make_membership()
    service_mock = AsyncMock(side_effect=DeviceNotFound())
    monkeypatch.setattr(
        devices_module.GatewayService,
        "assign_gateway",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(membership.workspace_id)}"
            f"/{membership.child_device_id}/gateway-membership"
        )
        response = client.put(
            path,
            json={"gateway_device_id": str(membership.gateway_device_id)},
            headers=trusted_headers(token),
        )

    assert response.status_code == 404
    service_mock.assert_awaited_once()


def test_assign_gateway_maps_gateway_not_found_to_404(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    membership = make_membership()
    service_mock = AsyncMock(side_effect=GatewayNotFound())
    monkeypatch.setattr(
        devices_module.GatewayService,
        "assign_gateway",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(membership.workspace_id)}"
            f"/{membership.child_device_id}/gateway-membership"
        )
        response = client.put(
            path,
            json={"gateway_device_id": str(membership.gateway_device_id)},
            headers=trusted_headers(token),
        )

    assert response.status_code == 404
    service_mock.assert_awaited_once()


def test_assign_gateway_maps_membership_conflict_to_409(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    membership = make_membership()
    service_mock = AsyncMock(side_effect=GatewayMembershipConflict())
    monkeypatch.setattr(
        devices_module.GatewayService,
        "assign_gateway",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(membership.workspace_id)}"
            f"/{membership.child_device_id}/gateway-membership"
        )
        response = client.put(
            path,
            json={"gateway_device_id": str(membership.gateway_device_id)},
            headers=trusted_headers(token),
        )

    assert response.status_code == 409
    service_mock.assert_awaited_once()


def test_assign_gateway_maps_cycle_detected_to_409(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    membership = make_membership()
    service_mock = AsyncMock(side_effect=GatewayCycleDetected())
    monkeypatch.setattr(
        devices_module.GatewayService,
        "assign_gateway",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(membership.workspace_id)}"
            f"/{membership.child_device_id}/gateway-membership"
        )
        response = client.put(
            path,
            json={"gateway_device_id": str(membership.gateway_device_id)},
            headers=trusted_headers(token),
        )

    assert response.status_code == 409
    service_mock.assert_awaited_once()


def test_assign_gateway_maps_permission_denied_to_403(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    membership = make_membership()
    service_mock = AsyncMock(side_effect=DevicePermissionDenied())
    monkeypatch.setattr(
        devices_module.GatewayService,
        "assign_gateway",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(membership.workspace_id)}"
            f"/{membership.child_device_id}/gateway-membership"
        )
        response = client.put(
            path,
            json={"gateway_device_id": str(membership.gateway_device_id)},
            headers=trusted_headers(token),
        )

    assert response.status_code == 403
    service_mock.assert_awaited_once()


# ---------------------------------------------------------------------------
# Gateway membership removal API
# ---------------------------------------------------------------------------


def test_remove_gateway_membership_success(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    membership = make_membership()
    service_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(
        devices_module.GatewayService,
        "remove_gateway",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(membership.workspace_id)}"
            f"/{membership.child_device_id}/gateway-membership"
        )
        response = client.delete(
            path,
            headers=trusted_headers(token),
        )

    assert response.status_code == 204
    assert response.content == b""
    assert_service_call(
        service_mock,
        actor_id=user.id,
        workspace_id=membership.workspace_id,
        child_device_id=membership.child_device_id,
    )


def test_remove_gateway_membership_requires_csrf(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    membership = make_membership()
    service_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(
        devices_module.GatewayService,
        "remove_gateway",
        service_mock,
    )

    with client_context(user) as client:
        path = (
            f"{device_base_path(membership.workspace_id)}"
            f"/{membership.child_device_id}/gateway-membership"
        )
        response = client.delete(
            path,
            headers={"Origin": TEST_ORIGIN},
        )

    assert response.status_code == 403
    service_mock.assert_not_awaited()


def test_remove_gateway_membership_maps_conflict_to_409(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    membership = make_membership()
    service_mock = AsyncMock(side_effect=GatewayMembershipConflict())
    monkeypatch.setattr(
        devices_module.GatewayService,
        "remove_gateway",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(membership.workspace_id)}"
            f"/{membership.child_device_id}/gateway-membership"
        )
        response = client.delete(
            path,
            headers=trusted_headers(token),
        )

    assert response.status_code == 409
    service_mock.assert_awaited_once()


def test_remove_gateway_membership_maps_permission_denied_to_403(
    monkeypatch,
):
    user = SimpleNamespace(id=uuid4())
    membership = make_membership()
    service_mock = AsyncMock(side_effect=DevicePermissionDenied())
    monkeypatch.setattr(
        devices_module.GatewayService,
        "remove_gateway",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(membership.workspace_id)}"
            f"/{membership.child_device_id}/gateway-membership"
        )
        response = client.delete(
            path,
            headers=trusted_headers(token),
        )

    assert response.status_code == 403
    service_mock.assert_awaited_once()


# ---------------------------------------------------------------------------
# CSRF origin validation
# ---------------------------------------------------------------------------


def test_gateway_registration_rejects_untrusted_origin(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    gateway = make_gateway()
    service_mock = AsyncMock(return_value=gateway)
    monkeypatch.setattr(
        devices_module.GatewayService,
        "register_gateway",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(gateway.workspace_id)}"
            f"/{gateway.device_id}/gateway"
        )
        response = client.post(
            path,
            json={
                "gateway_type": "mqtt",
                "adapter_key": "generic-mqtt",
                "configuration": {},
            },
            headers={
                "Origin": "https://evil.example",
                CSRF_HEADER_NAME: token,
            },
        )

    assert response.status_code == 403
    service_mock.assert_not_awaited()


# GATEWAY_SECRET_API_TESTS_V1
# ---------------------------------------------------------------------------
# Gateway secret API
# ---------------------------------------------------------------------------


def make_gateway_secret(**overrides):
    now = datetime.now(timezone.utc)
    values = {
        "secret_name": "mqtt_password",
        "created_at": now,
        "updated_at": now,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_list_gateway_secrets_success(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    gateway = make_gateway()
    secret = make_gateway_secret()
    service_mock = AsyncMock(return_value=[secret])
    monkeypatch.setattr(
        devices_module.GatewaySecretService,
        "list_secrets",
        service_mock,
    )

    with client_context(user) as client:
        path = (
            f"{device_base_path(gateway.workspace_id)}"
            f"/{gateway.device_id}/gateway/secrets"
        )
        response = client.get(path)

    assert response.status_code == 200
    assert response.json()[0]["secret_name"] == "mqtt_password"
    assert "value" not in response.json()[0]
    assert "ciphertext" not in response.json()[0]
    assert_service_call(
        service_mock,
        actor_id=user.id,
        workspace_id=gateway.workspace_id,
        gateway_device_id=gateway.device_id,
    )


def test_create_gateway_secret_success_and_does_not_echo_value(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    gateway = make_gateway()
    secret = make_gateway_secret()
    secret_value = "sensitive-test-value"
    service_mock = AsyncMock(return_value=secret)
    monkeypatch.setattr(
        devices_module.GatewaySecretService,
        "create_secret",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(gateway.workspace_id)}"
            f"/{gateway.device_id}/gateway/secrets"
        )
        response = client.post(
            path,
            json={
                "secret_name": secret.secret_name,
                "value": secret_value,
            },
            headers=trusted_headers(token),
        )

    assert response.status_code == 201
    assert response.json()["secret_name"] == secret.secret_name
    assert "value" not in response.json()
    assert "ciphertext" not in response.json()
    assert secret_value not in response.text
    assert_service_call(
        service_mock,
        actor_id=user.id,
        workspace_id=gateway.workspace_id,
        gateway_device_id=gateway.device_id,
        secret_name=secret.secret_name,
        secret_value=secret_value,
    )


def test_create_gateway_secret_requires_csrf(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    gateway = make_gateway()
    service_mock = AsyncMock(return_value=make_gateway_secret())
    monkeypatch.setattr(
        devices_module.GatewaySecretService,
        "create_secret",
        service_mock,
    )

    with client_context(user) as client:
        path = (
            f"{device_base_path(gateway.workspace_id)}"
            f"/{gateway.device_id}/gateway/secrets"
        )
        response = client.post(
            path,
            json={
                "secret_name": "mqtt_password",
                "value": "sensitive-test-value",
            },
            headers={"Origin": TEST_ORIGIN},
        )

    assert response.status_code == 403
    service_mock.assert_not_awaited()


def test_create_gateway_secret_rejects_invalid_body(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    gateway = make_gateway()
    service_mock = AsyncMock(return_value=make_gateway_secret())
    monkeypatch.setattr(
        devices_module.GatewaySecretService,
        "create_secret",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(gateway.workspace_id)}"
            f"/{gateway.device_id}/gateway/secrets"
        )
        response = client.post(
            path,
            json={
                "secret_name": "",
                "value": "",
                "unexpected": True,
            },
            headers=trusted_headers(token),
        )

    assert response.status_code == 422
    service_mock.assert_not_awaited()


def test_update_gateway_secret_success_and_does_not_echo_value(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    gateway = make_gateway()
    secret = make_gateway_secret()
    secret_value = "updated-sensitive-value"
    service_mock = AsyncMock(return_value=secret)
    monkeypatch.setattr(
        devices_module.GatewaySecretService,
        "update_secret",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(gateway.workspace_id)}"
            f"/{gateway.device_id}/gateway/secrets/{secret.secret_name}"
        )
        response = client.put(
            path,
            json={"value": secret_value},
            headers=trusted_headers(token),
        )

    assert response.status_code == 200
    assert response.json()["secret_name"] == secret.secret_name
    assert "value" not in response.json()
    assert "ciphertext" not in response.json()
    assert secret_value not in response.text
    assert_service_call(
        service_mock,
        actor_id=user.id,
        workspace_id=gateway.workspace_id,
        gateway_device_id=gateway.device_id,
        secret_name=secret.secret_name,
        secret_value=secret_value,
    )


def test_update_gateway_secret_requires_csrf(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    gateway = make_gateway()
    service_mock = AsyncMock(return_value=make_gateway_secret())
    monkeypatch.setattr(
        devices_module.GatewaySecretService,
        "update_secret",
        service_mock,
    )

    with client_context(user) as client:
        path = (
            f"{device_base_path(gateway.workspace_id)}"
            f"/{gateway.device_id}/gateway/secrets/mqtt_password"
        )
        response = client.put(
            path,
            json={"value": "updated-sensitive-value"},
            headers={"Origin": TEST_ORIGIN},
        )

    assert response.status_code == 403
    service_mock.assert_not_awaited()


def test_delete_gateway_secret_success(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    gateway = make_gateway()
    service_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(
        devices_module.GatewaySecretService,
        "delete_secret",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(gateway.workspace_id)}"
            f"/{gateway.device_id}/gateway/secrets/mqtt_password"
        )
        response = client.delete(
            path,
            headers=trusted_headers(token),
        )

    assert response.status_code == 204
    assert_service_call(
        service_mock,
        actor_id=user.id,
        workspace_id=gateway.workspace_id,
        gateway_device_id=gateway.device_id,
        secret_name="mqtt_password",
    )


def test_delete_gateway_secret_requires_csrf(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    gateway = make_gateway()
    service_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(
        devices_module.GatewaySecretService,
        "delete_secret",
        service_mock,
    )

    with client_context(user) as client:
        path = (
            f"{device_base_path(gateway.workspace_id)}"
            f"/{gateway.device_id}/gateway/secrets/mqtt_password"
        )
        response = client.delete(
            path,
            headers={"Origin": TEST_ORIGIN},
        )

    assert response.status_code == 403
    service_mock.assert_not_awaited()


def test_gateway_secret_not_found_maps_to_404(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    gateway = make_gateway()
    service_mock = AsyncMock(side_effect=GatewaySecretNotFound())
    monkeypatch.setattr(
        devices_module.GatewaySecretService,
        "update_secret",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(gateway.workspace_id)}"
            f"/{gateway.device_id}/gateway/secrets/mqtt_password"
        )
        response = client.put(
            path,
            json={"value": "updated-sensitive-value"},
            headers=trusted_headers(token),
        )

    assert response.status_code == 404
    service_mock.assert_awaited_once()


def test_gateway_secret_already_exists_maps_to_409(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    gateway = make_gateway()
    service_mock = AsyncMock(side_effect=GatewaySecretAlreadyExists())
    monkeypatch.setattr(
        devices_module.GatewaySecretService,
        "create_secret",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(gateway.workspace_id)}"
            f"/{gateway.device_id}/gateway/secrets"
        )
        response = client.post(
            path,
            json={
                "secret_name": "mqtt_password",
                "value": "sensitive-test-value",
            },
            headers=trusted_headers(token),
        )

    assert response.status_code == 409
    service_mock.assert_awaited_once()


def test_gateway_secret_encryption_unavailable_maps_to_503(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    gateway = make_gateway()
    service_mock = AsyncMock(
        side_effect=GatewaySecretEncryptionUnavailable()
    )
    monkeypatch.setattr(
        devices_module.GatewaySecretService,
        "create_secret",
        service_mock,
    )

    with client_context(user) as client:
        token = set_session_csrf(client)
        path = (
            f"{device_base_path(gateway.workspace_id)}"
            f"/{gateway.device_id}/gateway/secrets"
        )
        response = client.post(
            path,
            json={
                "secret_name": "mqtt_password",
                "value": "sensitive-test-value",
            },
            headers=trusted_headers(token),
        )

    assert response.status_code == 503
    service_mock.assert_awaited_once()


def test_gateway_secret_permission_denied_maps_to_403(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    gateway = make_gateway()
    service_mock = AsyncMock(side_effect=DevicePermissionDenied())
    monkeypatch.setattr(
        devices_module.GatewaySecretService,
        "list_secrets",
        service_mock,
    )

    with client_context(user) as client:
        path = (
            f"{device_base_path(gateway.workspace_id)}"
            f"/{gateway.device_id}/gateway/secrets"
        )
        response = client.get(path)

    assert response.status_code == 403
    service_mock.assert_awaited_once()
