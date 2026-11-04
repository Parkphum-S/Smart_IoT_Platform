"""Unit tests for shared password security utilities."""

from argon2 import PasswordHasher

from app.core.security import (
    hash_password,
    needs_rehash,
    verify_password,
)


def test_hash_password_uses_argon2id():
    password_hash = hash_password("Test-Password-Only")

    assert password_hash.startswith("$argon2id$")
    assert password_hash != "Test-Password-Only"


def test_verify_password_accepts_correct_password():
    password_hash = hash_password("Test-Password-Only")

    assert verify_password("Test-Password-Only", password_hash) is True


def test_verify_password_rejects_incorrect_password():
    password_hash = hash_password("Test-Password-Only")

    assert verify_password("Wrong-Password", password_hash) is False


def test_needs_rehash_returns_false_for_current_parameters():
    password_hash = hash_password("Test-Password-Only")

    assert needs_rehash(password_hash) is False


def test_needs_rehash_returns_true_for_legacy_parameters():
    legacy_hasher = PasswordHasher(
        time_cost=1,
        memory_cost=8192,
        parallelism=1,
    )
    legacy_hash = legacy_hasher.hash("Test-Password-Only")

    assert needs_rehash(legacy_hash) is True


def test_invalid_hash_is_handled_safely():
    assert verify_password("Test-Password-Only", "invalid-hash") is False
    assert needs_rehash("invalid-hash") is True
