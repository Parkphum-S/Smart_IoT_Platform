"""Mock regression tests for the trusted public key resolver."""

import base64
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.infrastructure.database.trust.trusted_key_store import (
    TrustedKeyError,
    TrustedPublicKeyRecord,
    resolve_trusted_public_key,
)


NOW = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)
TEST_PUBLIC_KEY = bytes(range(32))


def _record(**overrides):
    data = {
        "key_id": "local-test-key-01",
        "algorithm": "Ed25519",
        "status": "active",
        "public_key": base64.b64encode(TEST_PUBLIC_KEY).decode("ascii"),
        "not_before": "2029-01-01T00:00:00Z",
        "not_after": "2031-01-01T00:00:00Z",
    }
    data.update(overrides)
    return data


def test_resolves_exact_key_id():
    result = resolve_trusted_public_key(
        "local-test-key-01",
        [_record()],
        now=NOW,
    )
    assert result == TEST_PUBLIC_KEY


def test_key_id_matching_is_exact():
    with pytest.raises(TrustedKeyError, match="not found"):
        resolve_trusted_public_key(
            "local-test-key",
            [_record()],
            now=NOW,
        )


def test_unknown_key_is_rejected():
    with pytest.raises(TrustedKeyError, match="not found"):
        resolve_trusted_public_key(
            "unknown-key",
            [_record()],
            now=NOW,
        )


def test_revoked_key_is_rejected():
    with pytest.raises(TrustedKeyError, match="revoked"):
        resolve_trusted_public_key(
            "local-test-key-01",
            [_record(status="revoked")],
            now=NOW,
        )


def test_not_yet_valid_key_is_rejected():
    with pytest.raises(TrustedKeyError, match="not yet valid"):
        resolve_trusted_public_key(
            "local-test-key-01",
            [_record(not_before="2030-02-01T00:00:00Z")],
            now=NOW,
        )


def test_expired_key_is_rejected_at_expiry_boundary():
    with pytest.raises(TrustedKeyError, match="expired"):
        resolve_trusted_public_key(
            "local-test-key-01",
            [_record(not_after="2030-01-01T12:00:00Z")],
            now=NOW,
        )


def test_duplicate_key_ids_are_rejected():
    with pytest.raises(TrustedKeyError, match="duplicate"):
        resolve_trusted_public_key(
            "local-test-key-01",
            [_record(), _record()],
            now=NOW,
        )


@pytest.mark.parametrize(
    "public_key",
    [
        "not-base64!",
        base64.b64encode(b"short").decode("ascii"),
        base64.b64encode(TEST_PUBLIC_KEY).decode("ascii").rstrip("="),
    ],
)
def test_invalid_public_key_encoding_is_rejected(public_key):
    with pytest.raises(ValidationError):
        TrustedPublicKeyRecord.model_validate(
            _record(public_key=public_key)
        )


def test_unknown_registry_fields_are_rejected():
    with pytest.raises(ValidationError):
        TrustedPublicKeyRecord.model_validate(
            _record(unexpected="value")
        )


def test_unsupported_algorithm_is_rejected():
    with pytest.raises(ValidationError):
        TrustedPublicKeyRecord.model_validate(
            _record(algorithm="Other")
        )


def test_naive_validity_timestamp_is_rejected():
    with pytest.raises(ValidationError):
        TrustedPublicKeyRecord.model_validate(
            _record(not_before=datetime(2029, 1, 1))
        )


def test_invalid_validity_window_is_rejected():
    with pytest.raises(ValidationError):
        TrustedPublicKeyRecord.model_validate(
            _record(
                not_before="2031-01-01T00:00:00Z",
                not_after="2030-01-01T00:00:00Z",
            )
        )


def test_naive_resolution_time_is_rejected():
    with pytest.raises(TrustedKeyError, match="timezone-aware"):
        resolve_trusted_public_key(
            "local-test-key-01",
            [_record()],
            now=datetime(2030, 1, 1),
        )


def test_invalid_key_id_is_rejected():
    with pytest.raises(TrustedKeyError, match="invalid requested"):
        resolve_trusted_public_key("../key", [_record()], now=NOW)


def test_registry_entry_with_wrong_type_is_rejected():
    with pytest.raises(TrustedKeyError, match="registry entry"):
        resolve_trusted_public_key(
            "local-test-key-01",
            [object()],
            now=NOW,
        )
