"""TOTP two-factor authentication utilities."""

import base64
import io
import secrets
import string

import bcrypt
import pyotp
import qrcode  # type: ignore[import-untyped]

from app.core.encryption import decrypt_value, encrypt_value

APP_NAME = "SignalForge"


def generate_totp_secret() -> str:
    """Generate a random base32 TOTP secret."""
    return pyotp.random_base32()


def encrypt_totp_secret(secret: str) -> bytes:
    """Encrypt a TOTP secret for database storage."""
    return encrypt_value(secret)


def decrypt_totp_secret(encrypted: bytes) -> str:
    """Decrypt a stored TOTP secret."""
    return decrypt_value(encrypted)


def get_provisioning_uri(secret: str, email: str) -> str:
    """Build an otpauth:// URI for authenticator apps."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=APP_NAME)


def generate_qr_code_data_uri(uri: str) -> str:
    """Generate a QR code as a data:image/png;base64 string."""
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


def verify_totp_code(secret: str, code: str) -> bool:
    """Verify a 6-digit TOTP code (allows 1 step of clock drift)."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def generate_backup_codes(count: int = 8) -> list[str]:
    """Generate human-readable backup codes in XXXX-XXXX format."""
    chars = string.digits
    codes: list[str] = []
    for _ in range(count):
        part1 = "".join(secrets.choice(chars) for _ in range(4))
        part2 = "".join(secrets.choice(chars) for _ in range(4))
        codes.append(f"{part1}-{part2}")
    return codes


def hash_backup_codes(codes: list[str]) -> list[str]:
    """Bcrypt-hash each backup code for storage."""
    return [bcrypt.hashpw(c.encode(), bcrypt.gensalt()).decode() for c in codes]


def verify_backup_code(code: str, hashed_codes: list[str]) -> int | None:
    """Check a backup code against the hashed list. Returns the index if valid, else None."""
    for i, h in enumerate(hashed_codes):
        if bcrypt.checkpw(code.encode(), h.encode()):
            return i
    return None
