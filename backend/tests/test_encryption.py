"""Tests for Fernet encryption module."""
from unittest.mock import patch

import pytest

from app.core.encryption import decrypt_value, encrypt_value, generate_key


def test_encrypt_decrypt_roundtrip():
    key = generate_key()
    with patch("app.core.encryption.settings") as mock_settings:
        mock_settings.encryption_key = key
        plaintext = "my-secret-api-key-12345"
        encrypted = encrypt_value(plaintext)
        assert encrypted != plaintext.encode()
        decrypted = decrypt_value(encrypted)
        assert decrypted == plaintext


def test_decrypt_wrong_key_raises():
    key1 = generate_key()
    key2 = generate_key()
    with patch("app.core.encryption.settings") as mock_settings:
        mock_settings.encryption_key = key1
        encrypted = encrypt_value("secret")
    with patch("app.core.encryption.settings") as mock_settings:
        mock_settings.encryption_key = key2
        with pytest.raises(ValueError, match="Failed to decrypt"):
            decrypt_value(encrypted)


def test_no_key_raises():
    with patch("app.core.encryption.settings") as mock_settings:
        mock_settings.encryption_key = ""
        with pytest.raises(ValueError, match="SF_ENCRYPTION_KEY not set"):
            encrypt_value("test")
