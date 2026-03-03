from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with async_session() as session:
        yield session


# Module-level engine for Celery tasks — NullPool avoids cross-event-loop issues
_task_engine = create_async_engine(
    settings.database_url, poolclass=NullPool, echo=False,
)
_task_factory = async_sessionmaker(
    _task_engine, class_=AsyncSession, expire_on_commit=False,
)


@asynccontextmanager
async def task_session():
    """Create a fresh DB session for Celery tasks.

    Uses a shared NullPool engine — NullPool already ensures no connection
    reuse between callers, so sharing the engine object is safe.
    """
    async with _task_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
