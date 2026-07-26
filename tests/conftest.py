import asyncio

# Set Windows loop policy to SelectorEventLoop to avoid Proactor event loop errors on Windows
import sys
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

TEST_DATABASE_URI = settings.ASYNC_DATABASE_URI.replace("@db:", "@localhost:")
if not TEST_DATABASE_URI.endswith("/lmp_db_test"):
    TEST_DATABASE_URI = TEST_DATABASE_URI.replace("/lmp_db", "/lmp_db_test")

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


@pytest.fixture(autouse=True)
async def setup_test_db() -> AsyncGenerator[None, None]:
    """Create tables in test database and drop them after each test completes.

    Function-scoped to provide complete isolation and prevent loop crossover errors.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an AsyncSession instance, and override FastAPI dependency injection."""
    async with TestSessionLocal() as session:
        # Override get_db dependency in the application so that routers run on this exact session
        app.dependency_overrides[get_db] = lambda: session
        try:
            yield session
        finally:
            # Clear overrides
            app.dependency_overrides.clear()
            await session.rollback()
            await session.close()
