import asyncio

# Set Windows loop policy to SelectorEventLoop to avoid Proactor event loop errors on Windows
import sys
from collections.abc import AsyncGenerator, Generator

import pytest
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base import Base

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

TEST_DATABASE_URI = settings.ASYNC_DATABASE_URI.replace("@db:", "@localhost:")

test_engine = create_async_engine(
    TEST_DATABASE_URI,
    poolclass=pool.NullPool,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create a session-scoped event loop for test run consistency."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db() -> AsyncGenerator[None, None]:
    """Create tables in test database and drop them after all tests complete."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an AsyncSession instance, and safely clean up resources."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        await session.rollback()
        await session.close()
