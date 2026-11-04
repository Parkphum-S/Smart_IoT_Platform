"""Unit tests for CSRF token utilities."""

import pytest

from app.core.csrf import generate_csrf_token, verify_csrf_token


SECRET_KEY = "test-secret-key-for-csrf-unit-tests-32-chars"


def test_generated_token_is_valid():
    token = generate_csrf_token(SECRET_KEY)

    assert verify_csrf_token(token, SECRET_KEY) is True


def test_generated_tokens_are_unique():
    first_token = generate_csrf_token(SECRET_KEY)
    second_token = generate_csrf_token(SECRET_KEY)

    assert first_token != second_token


def test_modified_token_is_rejected():
    token = generate_csrf_token(SECRET_KEY)
    modified_token = token[:-1] + ("0" if token[-1] != "0" else "1")

    assert verify_csrf_token(modified_token, SECRET_KEY) is False


def test_token_signed_with_different_key_is_rejected():
    token = generate_csrf_token(SECRET_KEY)

    assert verify_csrf_token(
        token,
        "another-test-secret-key-with-32-chars",
    ) is False


@pytest.mark.parametrize("token", ["", "invalid", "a.b", ".signature", None])
def test_invalid_token_is_rejected(token):
    assert verify_csrf_token(token, SECRET_KEY) is False


def test_short_secret_key_cannot_generate_token():
    with pytest.raises(ValueError):
        generate_csrf_token("too-short")


def test_session_bound_token_is_valid_for_matching_session():
    token = generate_csrf_token(
        SECRET_KEY,
        session_binding="session-token-a",
    )

    assert verify_csrf_token(
        token,
        SECRET_KEY,
        session_binding="session-token-a",
    ) is True


def test_session_bound_token_is_rejected_for_different_session():
    token = generate_csrf_token(
        SECRET_KEY,
        session_binding="session-token-a",
    )

    assert verify_csrf_token(
        token,
        SECRET_KEY,
        session_binding="session-token-b",
    ) is False


def test_session_bound_token_is_rejected_without_session_binding():
    token = generate_csrf_token(
        SECRET_KEY,
        session_binding="session-token-a",
    )

    assert verify_csrf_token(token, SECRET_KEY) is False


def test_unbound_token_is_rejected_when_session_binding_is_required():
    token = generate_csrf_token(SECRET_KEY)

    assert verify_csrf_token(
        token,
        SECRET_KEY,
        session_binding="session-token-a",
    ) is False


def test_empty_session_binding_is_rejected():
    with pytest.raises(ValueError):
        generate_csrf_token(SECRET_KEY, session_binding="")
