"""Mock-only tests for the local trusted manifest schema."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.infrastructure.database.trust.trusted_manifest import (
    TrustedManifestPayload,
    validate_manifest_payload,
)


TEST_NOW = datetime(
    2026, 11, 18, 12, 0, tzinfo=timezone.utc
)


def valid_payload():
    return {
        "schema_version": 1,
        "target": {
            "target_id": "smart-iot-integration",
            "environment": "testing",
            "manifest_version": 1,
        },
        "connection": {
            "database": "smart_iot_integration_test",
            "hostname": "127.0.0.1",
            "port": 5432,
            "tls_server_name": None,
        },
        "cluster": {
            "postgresql_major": 18,
            "system_identifier": "1234567890123456789",
            "data_directory": "/data/postgresql/18/main",
            "instance_identity": "local-main-18",
            "is_standby": False,
        },
        "authorization": {
            "login_role": "smart_iot_test_migrator",
            "effective_role": "smart_iot_test_owner",
            "allowed_operations": ["migration"],
        },
        "isolation": {
            "level": "database",
            "shared_cluster_with_production": True,
            "production_database": "smart_iot",
        },
        "validity": {
            "issued_at": "2026-11-18T00:00:00Z",
            "expires_at": "2027-11-18T00:00:00Z",
        },
    }


def test_valid_manifest_payload_is_accepted():
    result = validate_manifest_payload(valid_payload(), now=TEST_NOW)

    assert isinstance(result, TrustedManifestPayload)
    assert result.connection.database == "smart_iot_integration_test"
    assert result.authorization.allowed_operations == ("migration",)


def test_operations_are_deeply_immutable():
    result = validate_manifest_payload(valid_payload(), now=TEST_NOW)
    with pytest.raises(AttributeError):
        result.authorization.allowed_operations.append("fixture")
    with pytest.raises(TypeError):
        result.authorization.allowed_operations[0] = "fixture"


def test_manifest_is_valid_at_issued_at_boundary():
    payload = valid_payload()
    payload["validity"]["issued_at"] = "2026-11-18T12:00:00Z"
    validate_manifest_payload(payload, now=TEST_NOW)


def test_manifest_is_rejected_before_issued_at():
    payload = valid_payload()
    payload["validity"]["issued_at"] = "2026-11-18T12:00:01Z"
    with pytest.raises(ValueError, match="not yet valid"):
        validate_manifest_payload(payload, now=TEST_NOW)


def test_manifest_is_rejected_at_expiry_boundary():
    payload = valid_payload()
    payload["validity"]["expires_at"] = "2026-11-18T12:00:00Z"
    with pytest.raises(ValueError, match="expired"):
        validate_manifest_payload(payload, now=TEST_NOW)


def test_manifest_is_rejected_after_expiry():
    payload = valid_payload()
    payload["validity"]["expires_at"] = "2026-11-18T11:59:59Z"
    with pytest.raises(ValueError, match="expired"):
        validate_manifest_payload(payload, now=TEST_NOW)


def test_naive_validation_clock_is_rejected():
    naive_now = datetime(2026, 11, 18, 12, 0)
    with pytest.raises(ValueError, match="timezone"):
        validate_manifest_payload(valid_payload(), now=naive_now)


def test_non_datetime_validation_clock_is_rejected():
    with pytest.raises(ValueError, match="datetime"):
        validate_manifest_payload(
            valid_payload(), now="2026-11-18T12:00:00Z"
        )


def test_non_object_payload_is_rejected():
    with pytest.raises(ValueError):
        validate_manifest_payload([])


def test_unknown_top_level_field_is_rejected():
    payload = valid_payload()
    payload["unexpected"] = True

    with pytest.raises(ValidationError):
        validate_manifest_payload(payload, now=TEST_NOW)


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("connection", "database", "smart_iot"),
        ("connection", "hostname", "example.com"),
        ("connection", "port", 55432),
        ("cluster", "is_standby", True),
        ("authorization", "login_role", "postgres"),
        ("authorization", "effective_role", "postgres"),
        ("isolation", "shared_cluster_with_production", False),
        ("isolation", "production_database", "other_database"),
        ("target", "manifest_version", 0),
        ("validity", "expires_at", "2025-01-01T00:00:00Z"),
    ],
)
def test_untrusted_identity_or_policy_is_rejected(
    section, field, value
):
    payload = valid_payload()
    payload[section][field] = value

    with pytest.raises(ValidationError):
        validate_manifest_payload(payload, now=TEST_NOW)


def test_naive_timestamp_is_rejected():
    payload = valid_payload()
    payload["validity"]["issued_at"] = "2026-11-18T00:00:00"

    with pytest.raises(ValidationError):
        validate_manifest_payload(payload, now=TEST_NOW)


def test_duplicate_operations_are_rejected():
    payload = valid_payload()
    payload["authorization"]["allowed_operations"] = [
        "migration",
        "migration",
    ]

    with pytest.raises(ValidationError):
        validate_manifest_payload(payload, now=TEST_NOW)


def test_boolean_is_not_accepted_as_integer_version():
    payload = valid_payload()
    payload["schema_version"] = True

    with pytest.raises(ValidationError):
        validate_manifest_payload(payload, now=TEST_NOW)
