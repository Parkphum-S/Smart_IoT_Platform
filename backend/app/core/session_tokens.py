"""Secure opaque session token generation and hashing utilities."""

import hashlib
import secrets


def generate_session_token() -> str:
    """Generate a cryptographically secure opaque session token."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """Return the SHA-256 hexadecimal digest of a session token."""
    if not token:
        raise ValueError("Session token must not be empty.")

    return hashlib.sha256(token.encode("utf-8")).hexdigest()
