import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.main import app
from app.models.base import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)


test_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with test_session() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


# ---------------------------------------------------------------------------
# Disable rate limiter for all tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _disable_rate_limit():
    """Disable slowapi rate limiting so tests don't hit 429."""
    limiter.enabled = False
    yield
    limiter.enabled = True


# ---------------------------------------------------------------------------
# Mock Redis token blacklist to avoid event loop / connection issues in tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _mock_token_blacklist(monkeypatch):
    """Replace Redis-backed token blacklist with no-op stubs for all tests."""

    async def _fake_is_blacklisted(jti):
        return False

    async def _fake_are_invalid(user_id, iat):
        return False

    async def _fake_blacklist(jti, ttl_seconds=1800):
        pass

    async def _fake_blacklist_all(user_id, ttl_seconds=1800):
        pass

    monkeypatch.setattr(
        "app.core.token_blacklist.is_token_blacklisted", _fake_is_blacklisted
    )
    monkeypatch.setattr(
        "app.core.token_blacklist.are_user_tokens_invalid", _fake_are_invalid
    )
    monkeypatch.setattr(
        "app.core.token_blacklist.blacklist_token", _fake_blacklist
    )
    monkeypatch.setattr(
        "app.core.token_blacklist.blacklist_all_user_tokens", _fake_blacklist_all
    )
    # Also patch where it's imported directly in dependencies
    monkeypatch.setattr(
        "app.auth.dependencies.are_user_tokens_invalid", _fake_are_invalid
    )


@pytest.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
