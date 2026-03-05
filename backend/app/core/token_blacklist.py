"""JWT token blacklist backed by Redis."""

import time

from app.core.redis_client import redis_client


async def blacklist_token(jti: str, ttl_seconds: int = 1800) -> None:
    """Add a JWT token ID to the blacklist."""
    await redis_client.set(f"signalforge:blacklist:{jti}", "1", ex=ttl_seconds)


async def is_token_blacklisted(jti: str) -> bool:
    """Check if a JWT token ID has been blacklisted."""
    return await redis_client.exists(f"signalforge:blacklist:{jti}") > 0


async def blacklist_all_user_tokens(user_id: str, ttl_seconds: int = 1800) -> None:
    """Blacklist all tokens for a user by storing a 'tokens_invalid_before' timestamp."""
    await redis_client.set(
        f"signalforge:user_tokens_invalid:{user_id}", str(time.time()), ex=ttl_seconds
    )


async def are_user_tokens_invalid(user_id: str, token_iat: float) -> bool:
    """Check if a user's tokens issued before a certain time are invalid."""
    invalid_before = await redis_client.get(f"signalforge:user_tokens_invalid:{user_id}")
    if invalid_before is None:
        return False
    return token_iat < float(invalid_before)
