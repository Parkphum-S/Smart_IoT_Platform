"""Request and response contract tests for device enrollment."""

import json
from uuid import uuid4

import pytest
from pydantic import ValidationError, SecretStr

from app.modules.devices.schemas import (
    DeviceEnrollmentRequest,
    DeviceEnrollmentResponse,
)


def valid_request(**overrides):
    values = {
        "bootstrap_token": "bootstrap-token-value",
        "credential_identifier": "device-credential-01",
        "password": "Strong-Enrollment-Password",
    }
    values.update(overrides)
    return values


def test_enrollment_request_accepts_valid_payload():
    request = DeviceEnrollmentRequest.model_validate(valid_request())

    assert isinstance(request.bootstrap_token, SecretStr)
    assert isinstance(request.password, SecretStr)
    assert request.bootstrap_token.get_secret_value() == "bootstrap-token-value"
    assert request.password.get_secret_value() == "Strong-Enrollment-Password"


@pytest.mark.parametrize(
    "field",
    ["bootstrap_token", "password"],
)
def test_enrollment_request_rejects_empty_secrets(field):
    with pytest.raises(ValidationError):
        DeviceEnrollmentRequest.model_validate(valid_request(**{field: ""}))


@pytest.mark.parametrize(
    ("field", "length"),
    [
        ("bootstrap_token", 513),
        ("credential_identifier", 161),
        ("password", 1025),
    ],
)
def test_enrollment_request_rejects_oversized_fields(field, length):
    with pytest.raises(ValidationError):
        DeviceEnrollmentRequest.model_validate(
            valid_request(**{field: "x" * length})
        )


@pytest.mark.parametrize(
    "extra_field",
    [
        "broker_key",
        "workspace_id",
        "device_id",
        "credential_status",
        "lifecycle_status",
        "secret_hash",
    ],
)
def test_enrollment_request_rejects_server_controlled_fields(extra_field):
    with pytest.raises(ValidationError):
        DeviceEnrollmentRequest.model_validate(
            valid_request(**{extra_field: "attacker-controlled"})
        )


def test_enrollment_request_masks_secrets_in_repr_and_json():
    token = "bootstrap-secret-that-must-not-leak"
    password = "password-that-must-not-leak"

    request = DeviceEnrollmentRequest.model_validate(
        valid_request(
            bootstrap_token=token,
            password=password,
        )
    )

    assert token not in repr(request)
    assert password not in repr(request)

    serialized = request.model_dump_json()

    assert token not in serialized
    assert password not in serialized
    assert "**********" in serialized


def test_enrollment_request_does_not_expose_plaintext_in_json_dump():
    request = DeviceEnrollmentRequest.model_validate(valid_request())

    dumped = json.loads(request.model_dump_json())

    assert dumped["bootstrap_token"] == "**********"
    assert dumped["password"] == "**********"


def test_enrollment_response_accepts_successful_service_result():
    device_id = uuid4()
    credential_id = uuid4()

    response = DeviceEnrollmentResponse(
        device_id=device_id,
        credential_id=credential_id,
        lifecycle_status="active",
        credential_status="active",
    )

    assert response.device_id == device_id
    assert response.credential_id == credential_id
    assert response.lifecycle_status == "active"
    assert response.credential_status == "active"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("lifecycle_status", "pending_provisioning"),
        ("credential_status", "pending"),
    ],
)
def test_enrollment_response_rejects_non_active_status(field, value):
    values = {
        "device_id": uuid4(),
        "credential_id": uuid4(),
        "lifecycle_status": "active",
        "credential_status": "active",
    }
    values[field] = value

    with pytest.raises(ValidationError):
        DeviceEnrollmentResponse.model_validate(values)


def test_enrollment_response_rejects_unexpected_fields():
    with pytest.raises(ValidationError):
        DeviceEnrollmentResponse(
            device_id=uuid4(),
            credential_id=uuid4(),
            lifecycle_status="active",
            credential_status="active",
            password="must-not-be-returned",
        )
