"""Тесты модуля app/core/security.py."""
import time

import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_returns_string(self):
        h = get_password_hash("mypassword")
        assert isinstance(h, str)
        assert len(h) > 0

    def test_hash_is_different_from_plain(self):
        h = get_password_hash("mypassword")
        assert h != "mypassword"

    def test_two_hashes_differ(self):
        """Bcrypt использует случайную соль — хэши разные."""
        h1 = get_password_hash("mypassword")
        h2 = get_password_hash("mypassword")
        assert h1 != h2

    def test_verify_correct_password(self):
        h = get_password_hash("correctpassword")
        assert verify_password("correctpassword", h) is True

    def test_verify_wrong_password(self):
        h = get_password_hash("correctpassword")
        assert verify_password("wrongpassword", h) is False

    def test_long_password_no_truncation(self):
        """SHA-256 пре-хэш не даёт обрезать пароли длиннее 72 байт."""
        long_pw = "a" * 100
        h = get_password_hash(long_pw)
        assert verify_password(long_pw, h) is True
        assert verify_password("a" * 72, h) is False

    def test_unicode_password(self):
        pw = "пароль_123_!@#"
        h = get_password_hash(pw)
        assert verify_password(pw, h) is True


class TestJWT:
    def test_create_and_decode_token(self):
        token = create_access_token({"sub": "42"})
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "42"

    def test_decode_invalid_token_returns_none(self):
        assert decode_access_token("invalid.token.here") is None

    def test_decode_empty_string_returns_none(self):
        assert decode_access_token("") is None

    def test_token_contains_exp(self):
        token = create_access_token({"sub": "1"})
        payload = decode_access_token(token)
        assert "exp" in payload

    def test_custom_data_preserved(self):
        token = create_access_token({"sub": "7", "role": "admin"})
        payload = decode_access_token(token)
        assert payload["role"] == "admin"
