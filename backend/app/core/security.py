"""Shared security utilities for password hashing and verification."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError


_password_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=19456,
    parallelism=1,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against an existing Argon2id hash."""
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """Check whether a password hash needs updated parameters."""
    try:
        return _password_hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True
