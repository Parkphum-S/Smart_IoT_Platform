"""CSRF token generation and validation utilities."""

import hashlib
import hmac
import secrets


def _build_signed_message(
    nonce: str,
    session_binding: str | None,
) -> bytes:
    """Build an unambiguous message for HMAC signing."""
    message = nonce.encode("ascii")

    if session_binding is not None:
        message += b"." + session_binding.encode("utf-8")

    return message


def generate_csrf_token(
    secret_key: str,
    *,
    session_binding: str | None = None,
) -> str:
    """Generate a signed, URL-safe CSRF token."""
    if len(secret_key) < 32:
        raise ValueError("CSRF signing key must contain at least 32 characters.")

    if session_binding is not None and not session_binding:
        raise ValueError("Session binding must not be empty.")

    nonce = secrets.token_urlsafe(32)
    signature = hmac.new(
        secret_key.encode("utf-8"),
        _build_signed_message(nonce, session_binding),
        hashlib.sha256,
    ).hexdigest()

    return f"{nonce}.{signature}"


def verify_csrf_token(
    token: str | None,
    secret_key: str,
    *,
    session_binding: str | None = None,
) -> bool:
    """Verify token format, HMAC signature, and optional session binding."""
    if not token or len(secret_key) < 32:
        return False

    if session_binding == "":
        return False

    try:
        nonce, supplied_signature = token.split(".", maxsplit=1)

        if not nonce or len(supplied_signature) != 64:
            return False

        expected_signature = hmac.new(
            secret_key.encode("utf-8"),
            _build_signed_message(nonce, session_binding),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(
            supplied_signature,
            expected_signature,
        )
    except (ValueError, UnicodeEncodeError):
        return False
