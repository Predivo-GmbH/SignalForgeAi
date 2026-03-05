import uuid
from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import PyJWTError

from app.config import settings


def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.jwt_expiry_minutes)
    payload = {"sub": user_id, "exp": expires, "iat": now.timestamp(), "type": "access"}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=settings.jwt_refresh_expiry_days)
    payload = {
        "sub": user_id,
        "exp": expires,
        "iat": now.timestamp(),
        "type": "refresh",
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_2fa_pending_token(user_id: str) -> str:
    """Short-lived token for the 2FA login second step.

    Has type="2fa_pending" so get_current_user rejects it —
    it can only be exchanged via POST /auth/2fa/login.
    """
    expires = datetime.now(timezone.utc) + timedelta(minutes=5)
    payload = {"sub": user_id, "exp": expires, "type": "2fa_pending"}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except PyJWTError:
        return None
