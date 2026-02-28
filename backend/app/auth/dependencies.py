"""Auth dependencies for FastAPI route protection."""

from fastapi import Header, HTTPException, status

from app.auth.jwt import decode_token


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
    return payload["sub"]
