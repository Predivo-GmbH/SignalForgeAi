"""Tests for broker connection API."""
from app.core.encryption import generate_key


def test_mask_key():
    from app.api.broker import _mask_key

    assert _mask_key("abcdefgh1234") == "****1234"
    assert _mask_key("ab") == "****"
    assert _mask_key("") == "****"


def test_mask_key_exactly_four():
    from app.api.broker import _mask_key

    assert _mask_key("abcd") == "****"


def test_mask_key_five_chars():
    from app.api.broker import _mask_key

    assert _mask_key("abcde") == "****bcde"


def test_generate_key_produces_valid_fernet_key():
    key = generate_key()
    assert isinstance(key, str)
    assert len(key) > 0
