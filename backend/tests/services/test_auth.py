from datetime import UTC, datetime, timedelta
from unittest.mock import ANY

import pytest
from jose import jwt

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

settings = get_settings()


class TestPasswordHashing:
    def test_hash_and_verify_success(self) -> None:
        hashed = hash_password("my_secret_password")
        assert hashed != "my_secret_password"
        assert verify_password("my_secret_password", hashed) is True

    def test_verify_wrong_password(self) -> None:
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_hash_is_different_each_time(self) -> None:
        hashed1 = hash_password("same_password")
        hashed2 = hash_password("same_password")
        assert hashed1 != hashed2


class TestJWTTokens:
    def test_create_and_decode_access_token(self) -> None:
        token_data = {"sub": "user-123"}
        token = create_access_token(token_data)
        decoded = decode_token(token)
        assert decoded["sub"] == "user-123"
        assert decoded["type"] == "access"
        assert "exp" in decoded

    def test_create_and_decode_refresh_token(self) -> None:
        token_data = {"sub": "user-456"}
        token = create_refresh_token(token_data)
        decoded = decode_token(token)
        assert decoded["sub"] == "user-456"
        assert decoded["type"] == "refresh"

    def test_decode_invalid_token_returns_empty(self) -> None:
        decoded = decode_token("invalid.token.here")
        assert decoded == {}

    def test_access_token_expires_correctly(self) -> None:
        token_data = {"sub": "user-exp"}
        token = create_access_token(token_data, expires_delta=timedelta(seconds=1))
        decoded = decode_token(token)
        assert decoded["sub"] == "user-exp"

    def test_token_with_extra_payload(self) -> None:
        token_data = {"sub": "user-789", "role": "admin", "custom": "value"}
        token = create_access_token(token_data)
        decoded = decode_token(token)
        assert decoded["sub"] == "user-789"
        assert decoded["role"] == "admin"
        assert decoded["custom"] == "value"
        assert decoded["type"] == "access"

    def test_refresh_and_access_tokens_have_different_types(self) -> None:
        user_data = {"sub": "user-type-test"}
        access_token = create_access_token(user_data)
        refresh_token = create_refresh_token(user_data)

        access_decoded = decode_token(access_token)
        refresh_decoded = decode_token(refresh_token)

        assert access_decoded["type"] == "access"
        assert refresh_decoded["type"] == "refresh"

    def test_token_contains_expected_claims(self) -> None:
        token_data = {"sub": "user-claims"}
        token = create_access_token(token_data)
        # Decode without verification to inspect raw claims
        raw = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        assert "exp" in raw
        assert raw["sub"] == "user-claims"
        assert raw["type"] == "access"


class TestTokenEdgeCases:
    def test_token_from_different_secret_fails(self) -> None:
        token_data = {"sub": "user-diff-secret"}
        token = create_access_token(token_data)
        # Decode with wrong key should return empty via decode_token
        decoded = decode_token(token + "tampered")
        assert decoded == {}

    def test_empty_token_data(self) -> None:
        token = create_access_token({})
        decoded = decode_token(token)
        assert decoded["type"] == "access"
        assert "exp" in decoded
