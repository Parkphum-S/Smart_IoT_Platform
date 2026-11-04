"""Unit tests for secure session token utilities."""

import re

import pytest

from app.core.session_tokens import (
    generate_session_token,
    hash_session_token,
)


def test_generate_session_token_returns_non_empty_url_safe_token():
    token = generate_session_token()

    assert isinstance(token, str)
    assert token
    assert re.fullmatch(r"[A-Za-z0-9_-]+", token)


def test_generate_session_token_generates_unique_values():
    tokens = {generate_session_token() for _ in range(100)}

    assert len(tokens) == 100


def test_hash_session_token_returns_sha256_hex_digest():
    token_hash = hash_session_token("test-session-token")

    assert len(token_hash) == 64
    assert re.fullmatch(r"[0-9a-f]{64}", token_hash)


def test_hash_session_token_is_deterministic():
    token = "test-session-token"

    assert hash_session_token(token) == hash_session_token(token)


def test_different_tokens_produce_different_hashes():
    assert hash_session_token("token-one") != hash_session_token("token-two")


def test_hash_session_token_rejects_empty_token():
    with pytest.raises(ValueError):
        hash_session_token("")
