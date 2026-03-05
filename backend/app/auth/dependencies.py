"""Auth dependencies for FastAPI route protection."""

from fastapi import Header, HTTPException, status

from app.auth.jwt import decode_token
from app.core.token_blacklist import are_user_tokens_invalid


async def get_current_user(authorization: str | None = Header(None)) -> str:
    """Extract and validate the current user from the Authorization header.

    Returns the user_id (sub claim) from a valid access token.
    Raises HTTP 401 for missing, malformed, or invalid tokens.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )
    token = authorization.removeprefix("Bearer ")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload["sub"]

    # Check if all user tokens issued before a certain time have been invalidated
    # (e.g. after password change or 2FA disable)
    iat = payload.get("iat")
    if iat is not None:
        if await are_user_tokens_invalid(user_id, float(iat)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )

    return user_id
