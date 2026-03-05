"""Shared rate-limiter instance (slowapi)."""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _rate_limit_key(request: Request) -> str:
    """Use user ID for authenticated requests, IP for unauthenticated."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            from app.auth.jwt import decode_token

            payload = decode_token(auth.removeprefix("Bearer "))
            if payload and payload.get("sub"):
                return f"user:{payload['sub']}"
        except Exception:
            pass
    return get_remote_address(request)


limiter = Limiter(key_func=_rate_limit_key)
