from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with async_session() as session:
        yield session


@asynccontextmanager
async def task_session():
    """Create a fresh DB session for Celery tasks.

    Each Celery task calls asyncio.run() with a new event loop, so we
    need a separate engine with NullPool to avoid sharing connections
    across event loops.
    """
    task_engine = create_async_engine(
        settings.database_url, poolclass=NullPool, echo=False,
    )
    factory = async_sessionmaker(
        task_engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with factory() as session:
        try:
            yield session
        finally:
            await task_engine.dispose()
