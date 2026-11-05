"""Unit tests for context-bound gateway secret encryption."""

import base64

import pytest

from app.infrastructure.security.encryption import (
    EncryptionError,
    GatewaySecretEncryption,
    GatewaySecretKeyring,
)


TEST_KEY = bytes(range(32))
TEST_KEY_BASE64 = base64.b64encode(TEST_KEY).decode("ascii")
WORKSPACE_A = "workspace-001"
WORKSPACE_B = "workspace-002"
GATEWAY_A = "gateway-001"
GATEWAY_B = "gateway-002"


@pytest.fixture
def encryption():
    return GatewaySecretEncryption(TEST_KEY, "v1")


def encrypt_test_value(service, plaintext="private-value"):
    return service.encrypt(
        plaintext,
        workspace_id=WORKSPACE_A,
        gateway_id=GATEWAY_A,
    )


def decrypt_test_value(service, ciphertext):
    return service.decrypt(
        ciphertext,
        "v1",
        workspace_id=WORKSPACE_A,
        gateway_id=GATEWAY_A,
    )


def test_encrypt_decrypt_round_trip(encryption):
    plaintext = "gateway-password-example"
    ciphertext = encrypt_test_value(encryption, plaintext)

    assert ciphertext != plaintext
    assert decrypt_test_value(encryption, ciphertext) == plaintext


def test_same_plaintext_produces_different_ciphertexts(encryption):
    first = encrypt_test_value(encryption, "same-secret")
    second = encrypt_test_value(encryption, "same-secret")

    assert first != second
    assert decrypt_test_value(encryption, first) == "same-secret"
    assert decrypt_test_value(encryption, second) == "same-secret"


def test_wrong_key_cannot_decrypt(encryption):
    ciphertext = encrypt_test_value(encryption)
    other = GatewaySecretEncryption(bytes(reversed(range(32))), "v1")

    with pytest.raises(EncryptionError):
        decrypt_test_value(other, ciphertext)


def test_wrong_key_version_is_rejected(encryption):
    ciphertext = encrypt_test_value(encryption)

    with pytest.raises(EncryptionError):
        encryption.decrypt(
            ciphertext,
            "v2",
            workspace_id=WORKSPACE_A,
            gateway_id=GATEWAY_A,
        )


def test_wrong_gateway_context_is_rejected(encryption):
    ciphertext = encrypt_test_value(encryption)

    with pytest.raises(EncryptionError):
        encryption.decrypt(
            ciphertext,
            "v1",
            workspace_id=WORKSPACE_A,
            gateway_id=GATEWAY_B,
        )


def test_wrong_workspace_context_is_rejected(encryption):
    ciphertext = encrypt_test_value(encryption)

    with pytest.raises(EncryptionError):
        encryption.decrypt(
            ciphertext,
            "v1",
            workspace_id=WORKSPACE_B,
            gateway_id=GATEWAY_A,
        )


def test_both_wrong_context_values_are_rejected(encryption):
    ciphertext = encrypt_test_value(encryption)

    with pytest.raises(EncryptionError):
        encryption.decrypt(
            ciphertext,
            "v1",
            workspace_id=WORKSPACE_B,
            gateway_id=GATEWAY_B,
        )


@pytest.mark.parametrize(
    "ciphertext",
    [
        "",
        "not-base64!",
        base64.b64encode(b"too-short").decode("ascii"),
    ],
)
def test_invalid_ciphertext_is_rejected(encryption, ciphertext):
    with pytest.raises(EncryptionError):
        decrypt_test_value(encryption, ciphertext)


def test_tampered_ciphertext_is_rejected(encryption):
    payload = bytearray(base64.b64decode(encrypt_test_value(encryption)))
    payload[-1] ^= 1
    tampered = base64.b64encode(payload).decode("ascii")

    with pytest.raises(EncryptionError):
        decrypt_test_value(encryption, tampered)


def test_empty_plaintext_is_rejected(encryption):
    with pytest.raises(ValueError):
        encrypt_test_value(encryption, "")


def test_invalid_key_length_is_rejected():
    with pytest.raises(ValueError):
        GatewaySecretEncryption(b"short", "v1")


def test_invalid_key_version_is_rejected():
    with pytest.raises(ValueError):
        GatewaySecretEncryption(TEST_KEY, "../invalid")


def test_missing_workspace_context_is_rejected(encryption):
    with pytest.raises(TypeError):
        encryption.encrypt("secret", gateway_id=GATEWAY_A)


def test_empty_gateway_context_is_rejected(encryption):
    with pytest.raises(ValueError):
        encryption.encrypt(
            "secret",
            workspace_id=WORKSPACE_A,
            gateway_id="",
        )


def test_oversized_context_is_rejected(encryption):
    with pytest.raises(ValueError):
        encryption.encrypt(
            "secret",
            workspace_id="w" * 256,
            gateway_id=GATEWAY_A,
        )


def test_from_base64_round_trip():
    service = GatewaySecretEncryption.from_base64(TEST_KEY_BASE64, "v1")
    ciphertext = encrypt_test_value(service)

    assert decrypt_test_value(service, ciphertext) == "private-value"


def test_from_base64_rejects_invalid_encoding():
    with pytest.raises(ValueError):
        GatewaySecretEncryption.from_base64("invalid-base64!", "v1")


def test_from_base64_rejects_wrong_key_length():
    short_key = base64.b64encode(b"short").decode("ascii")

    with pytest.raises(ValueError):
        GatewaySecretEncryption.from_base64(short_key, "v1")

def test_keyring_encrypts_with_active_version_and_decrypts_old_version():
    key_v2 = bytes(reversed(range(32)))
    keyring = GatewaySecretKeyring(
        {"v1": TEST_KEY, "v2": key_v2},
        active_key_version="v2",
    )
    old_cipher = GatewaySecretEncryption(TEST_KEY, "v1").encrypt(
        "old-secret",
        workspace_id=WORKSPACE_A,
        gateway_id=GATEWAY_A,
    )

    new_cipher = keyring.encrypt(
        "new-secret",
        workspace_id=WORKSPACE_A,
        gateway_id=GATEWAY_A,
    )

    assert keyring.decrypt(
        old_cipher,
        "v1",
        workspace_id=WORKSPACE_A,
        gateway_id=GATEWAY_A,
    ) == "old-secret"
    assert keyring.decrypt(
        new_cipher,
        "v2",
        workspace_id=WORKSPACE_A,
        gateway_id=GATEWAY_A,
    ) == "new-secret"


def test_keyring_rejects_unknown_key_version():
    keyring = GatewaySecretKeyring({"v1": TEST_KEY}, "v1")

    with pytest.raises(EncryptionError):
        keyring.decrypt(
            "invalid",
            "v2",
            workspace_id=WORKSPACE_A,
            gateway_id=GATEWAY_A,
        )


def test_keyring_exposes_active_key_version():
    keyring = GatewaySecretKeyring(
        {"v1": TEST_KEY, "v2": bytes(reversed(range(32)))},
        "v2",
    )

    assert keyring.key_version == "v2"


def test_keyring_requires_active_key_version():
    with pytest.raises(ValueError):
        GatewaySecretKeyring({"v1": TEST_KEY}, "v2")


def test_keyring_rejects_invalid_key_version():
    with pytest.raises(ValueError):
        GatewaySecretKeyring({"../invalid": TEST_KEY}, "../invalid")


def test_keyring_from_base64():
    key_v2 = bytes(reversed(range(32)))
    encoded = base64.b64encode(key_v2).decode("ascii")
    keyring = GatewaySecretKeyring.from_base64(
        {"v1": TEST_KEY_BASE64, "v2": encoded},
        "v2",
    )

    assert keyring.key_versions == frozenset({"v1", "v2"})


def test_keyring_from_base64_rejects_invalid_key():
    with pytest.raises(ValueError):
        GatewaySecretKeyring.from_base64({"v1": "invalid!"}, "v1")


def test_keyring_rejects_duplicate_key_material():
    import pytest
    from app.infrastructure.security.encryption import GatewaySecretKeyring

    duplicate = bytes(range(32))
    with pytest.raises(ValueError, match="unique"):
        GatewaySecretKeyring(
            {"v1": duplicate, "v2": duplicate},
            "v2",
        )
