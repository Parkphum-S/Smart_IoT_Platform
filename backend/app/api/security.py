"""Reusable API security dependencies."""

import hmac
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.core.config import Settings, get_settings
from app.core.csrf import verify_csrf_token


SESSION_COOKIE_NAME = "smart_iot_session"
CSRF_COOKIE_NAME = "smart_iot_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"


def require_trusted_origin(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Reject requests without an explicitly trusted Origin."""
    origin = request.headers.get("origin")

    if not origin or origin not in settings.trusted_origins:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Request origin is not allowed.",
        )


def _validate_csrf_token(
    request: Request,
    settings: Settings,
    *,
    session_binding: str | None,
) -> None:
    """Validate matching CSRF cookie/header and its HMAC signature."""
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get(CSRF_HEADER_NAME)

    if (
        not cookie_token
        or not header_token
        or not hmac.compare_digest(cookie_token, header_token)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token is missing or invalid.",
        )

    if settings.secret_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CSRF protection is not configured.",
        )

    secret_key = settings.secret_key.get_secret_value()

    if not verify_csrf_token(
        cookie_token,
        secret_key,
        session_binding=session_binding,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token is missing or invalid.",
        )


def require_prelogin_csrf(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[None, Depends(require_trusted_origin)],
) -> None:
    """Validate an unbound CSRF token for pre-login requests."""
    _validate_csrf_token(
        request,
        settings,
        session_binding=None,
    )


def require_session_csrf(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[None, Depends(require_trusted_origin)],
) -> None:
    """Validate a CSRF token bound to the current session cookie."""
    session_token = request.cookies.get(SESSION_COOKIE_NAME)

    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated session is required.",
        )

    _validate_csrf_token(
        request,
        settings,
        session_binding=session_token,
    )
