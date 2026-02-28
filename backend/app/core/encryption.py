"""Fernet symmetric encryption for broker API credentials."""

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _get_fernet() -> Fernet:
    key = settings.encryption_key
    if not key:
        raise ValueError("SF_ENCRYPTION_KEY not set — cannot encrypt/decrypt broker credentials")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_value(plaintext: str) -> bytes:
    """Encrypt a string value. Returns encrypted bytes."""
    return _get_fernet().encrypt(plaintext.encode())


def decrypt_value(ciphertext: bytes) -> str:
    """Decrypt encrypted bytes back to string."""
    try:
        return _get_fernet().decrypt(ciphertext).decode()
    except InvalidToken as e:
        raise ValueError("Failed to decrypt — wrong key or corrupted data") from e


def generate_key() -> str:
    """Generate a new Fernet encryption key."""
    return Fernet.generate_key().decode()
