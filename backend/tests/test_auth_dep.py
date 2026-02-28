"""Tests for the auth dependency — get_current_user."""

import pytest
from fastapi import HTTPException

from app.auth.dependencies import get_current_user
from app.auth.jwt import create_access_token, create_refresh_token


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_valid_token_returns_user_id(self):
        token = create_access_token("test-user-id")
        user_id = await get_current_user(authorization=f"Bearer {token}")
        assert user_id == "test-user-id"

    @pytest.mark.asyncio
    async def test_missing_header_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            await get_current_user(authorization=None)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            await get_current_user(authorization="Bearer invalid-token")
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_non_bearer_scheme_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            await get_current_user(authorization="Basic abc123")
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_rejected(self):
        """Refresh tokens must NOT be accepted as access tokens."""
        token = create_refresh_token("test-user-id")
        with pytest.raises(HTTPException) as exc:
            await get_current_user(authorization=f"Bearer {token}")
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_bearer_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            await get_current_user(authorization="Bearer ")
        assert exc.value.status_code == 401
