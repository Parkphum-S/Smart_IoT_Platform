"""Tests for API Origin and CSRF security dependencies."""

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.api.security import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    SESSION_COOKIE_NAME,
    require_prelogin_csrf,
    require_session_csrf,
    require_trusted_origin,
)
from app.core.config import Settings
from app.core.csrf import generate_csrf_token


TEST_DATABASE_URL = (
    "postgresql+asyncpg://test_user:test_password@127.0.0.1:5432/test_db"
)
TEST_SECRET = "test-secret-key-that-is-at-least-32-characters"


def make_request(
    *,
    origin: str | None = "https://example.com",
    csrf_cookie: str | None = None,
    csrf_header: str | None = None,
    session_cookie: str | None = None,
) -> Request:
    """Build a Starlette request with the supplied security headers."""
    headers = []

    if origin is not None:
        headers.append((b"origin", origin.encode("latin-1")))

    if csrf_header is not None:
        headers.append((b"x-csrf-token", csrf_header.encode("latin-1")))

    cookies = []

    if csrf_cookie is not None:
        cookies.append(f"{CSRF_COOKIE_NAME}={csrf_cookie}")

    if session_cookie is not None:
        cookies.append(f"{SESSION_COOKIE_NAME}={session_cookie}")

    if cookies:
        headers.append((b"cookie", "; ".join(cookies).encode("latin-1")))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "https",
        "path": "/api/v1/auth/login",
        "raw_path": b"/api/v1/auth/login",
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 443),
    }

    return Request(scope)


def make_settings(
    *,
    secret_key: str | None = TEST_SECRET,
    trusted_origins: list[str] | None = None,
) -> Settings:
    """Build isolated application settings for security tests."""
    return Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        secret_key=secret_key,
        trusted_origins=(
            ["https://example.com"]
            if trusted_origins is None
            else trusted_origins
        ),
    )


def test_trusted_origin_accepts_exact_allowed_origin():
    request = make_request()
    settings = make_settings()

    assert require_trusted_origin(request, settings) is None


@pytest.mark.parametrize(
    "origin",
    [
        None,
        "https://attacker.example",
        "https://example.com.evil.test",
        "http://example.com",
        "null",
    ],
)
def test_trusted_origin_rejects_missing_or_untrusted_origin(origin):
    request = make_request(origin=origin)
    settings = make_settings()

    with pytest.raises(HTTPException) as exc_info:
        require_trusted_origin(request, settings)

    assert exc_info.value.status_code == 403


def test_prelogin_csrf_accepts_valid_unbound_token():
    settings = make_settings()
    token = generate_csrf_token(TEST_SECRET)
    request = make_request(csrf_cookie=token, csrf_header=token)

    assert require_prelogin_csrf(request, settings, None) is None


def test_prelogin_csrf_rejects_cookie_header_mismatch():
    settings = make_settings()
    cookie_token = generate_csrf_token(TEST_SECRET)
    header_token = generate_csrf_token(TEST_SECRET)
    request = make_request(
        csrf_cookie=cookie_token,
        csrf_header=header_token,
    )

    with pytest.raises(HTTPException) as exc_info:
        require_prelogin_csrf(request, settings, None)

    assert exc_info.value.status_code == 403


def test_prelogin_csrf_rejects_token_bound_to_session():
    settings = make_settings()
    token = generate_csrf_token(
        TEST_SECRET,
        session_binding="some-session-token",
    )
    request = make_request(csrf_cookie=token, csrf_header=token)

    with pytest.raises(HTTPException) as exc_info:
        require_prelogin_csrf(request, settings, None)

    assert exc_info.value.status_code == 403


def test_prelogin_csrf_rejects_missing_token():
    settings = make_settings()
    request = make_request()

    with pytest.raises(HTTPException) as exc_info:
        require_prelogin_csrf(request, settings, None)

    assert exc_info.value.status_code == 403


def test_prelogin_csrf_rejects_missing_secret_key():
    settings = make_settings(secret_key=None)
    token = generate_csrf_token(TEST_SECRET)
    request = make_request(csrf_cookie=token, csrf_header=token)

    with pytest.raises(HTTPException) as exc_info:
        require_prelogin_csrf(request, settings, None)

    assert exc_info.value.status_code == 503


def test_session_csrf_accepts_token_bound_to_current_session():
    settings = make_settings()
    session_token = "valid-session-token"
    csrf_token = generate_csrf_token(
        TEST_SECRET,
        session_binding=session_token,
    )
    request = make_request(
        csrf_cookie=csrf_token,
        csrf_header=csrf_token,
        session_cookie=session_token,
    )

    assert require_session_csrf(request, settings, None) is None


def test_session_csrf_rejects_token_bound_to_another_session():
    settings = make_settings()
    csrf_token = generate_csrf_token(
        TEST_SECRET,
        session_binding="another-session-token",
    )
    request = make_request(
        csrf_cookie=csrf_token,
        csrf_header=csrf_token,
        session_cookie="current-session-token",
    )

    with pytest.raises(HTTPException) as exc_info:
        require_session_csrf(request, settings, None)

    assert exc_info.value.status_code == 403


def test_session_csrf_rejects_unbound_token():
    settings = make_settings()
    csrf_token = generate_csrf_token(TEST_SECRET)
    request = make_request(
        csrf_cookie=csrf_token,
        csrf_header=csrf_token,
        session_cookie="current-session-token",
    )

    with pytest.raises(HTTPException) as exc_info:
        require_session_csrf(request, settings, None)

    assert exc_info.value.status_code == 403


def test_session_csrf_rejects_missing_session_cookie():
    settings = make_settings()
    csrf_token = generate_csrf_token(TEST_SECRET)
    request = make_request(
        csrf_cookie=csrf_token,
        csrf_header=csrf_token,
    )

    with pytest.raises(HTTPException) as exc_info:
        require_session_csrf(request, settings, None)

    assert exc_info.value.status_code == 403


def test_session_csrf_rejects_untrusted_origin():
    settings = make_settings()
    session_token = "valid-session-token"
    csrf_token = generate_csrf_token(
        TEST_SECRET,
        session_binding=session_token,
    )
    request = make_request(
        origin="https://attacker.example",
        csrf_cookie=csrf_token,
        csrf_header=csrf_token,
        session_cookie=session_token,
    )

    with pytest.raises(HTTPException) as exc_info:
        require_trusted_origin(request, settings)

    assert exc_info.value.status_code == 403



def create_security_test_app(settings: Settings) -> FastAPI:
    """Create an isolated FastAPI app for dependency integration tests."""
    app = FastAPI()
    app.dependency_overrides[
        __import__("app.core.config", fromlist=["get_settings"]).get_settings
    ] = lambda: settings

    @app.post("/prelogin")
    def prelogin_endpoint(
        _: None = Depends(require_prelogin_csrf),
    ):
        return {"status": "ok"}

    @app.post("/session")
    def session_endpoint(
        _: None = Depends(require_session_csrf),
    ):
        return {"status": "ok"}

    return app


def test_fastapi_prelogin_dependency_accepts_trusted_origin():
    settings = make_settings()
    token = generate_csrf_token(TEST_SECRET)
    app = create_security_test_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/prelogin",
            headers={
                "Origin": "https://example.com",
                CSRF_HEADER_NAME: token,
            },
            cookies={CSRF_COOKIE_NAME: token},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_fastapi_prelogin_dependency_rejects_untrusted_origin():
    settings = make_settings()
    token = generate_csrf_token(TEST_SECRET)
    app = create_security_test_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/prelogin",
            headers={
                "Origin": "https://attacker.example",
                CSRF_HEADER_NAME: token,
            },
            cookies={CSRF_COOKIE_NAME: token},
        )

    assert response.status_code == 403


def test_fastapi_session_dependency_accepts_trusted_origin():
    settings = make_settings()
    session_token = "integration-test-session"
    csrf_token = generate_csrf_token(
        TEST_SECRET,
        session_binding=session_token,
    )
    app = create_security_test_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/session",
            headers={
                "Origin": "https://example.com",
                CSRF_HEADER_NAME: csrf_token,
            },
            cookies={
                CSRF_COOKIE_NAME: csrf_token,
                SESSION_COOKIE_NAME: session_token,
            },
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_fastapi_session_dependency_rejects_untrusted_origin():
    settings = make_settings()
    session_token = "integration-test-session"
    csrf_token = generate_csrf_token(
        TEST_SECRET,
        session_binding=session_token,
    )
    app = create_security_test_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/session",
            headers={
                "Origin": "https://attacker.example",
                CSRF_HEADER_NAME: csrf_token,
            },
            cookies={
                CSRF_COOKIE_NAME: csrf_token,
                SESSION_COOKIE_NAME: session_token,
            },
        )

    assert response.status_code == 403
