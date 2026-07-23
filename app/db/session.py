"""
app/db/session.py — Async SQLAlchemy Engine and Session Dependency

Provides:
  - async_engine: The single shared AsyncEngine instance with connection pooling.
  - AsyncSessionLocal: Factory producing AsyncSession instances per request.
  - get_db(): FastAPI dependency that yields a session and closes it after the request.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# ─── Async Engine ─────────────────────────────────────────────────────────────
#
# create_async_engine uses aiomysql under the hood (mysql+aiomysql://...).
# The connection pool is shared across all requests for the lifetime of the app.
#
# Pool parameters (from Settings):
#   pool_size         → persistent connections kept open (default: 10)
#   max_overflow      → additional burst connections allowed (default: 20)
#   pool_timeout      → seconds to wait for a connection from the pool (default: 30)
#   pool_recycle      → recycle connections after N seconds to prevent MySQL
#                       "server has gone away" on idle connections (default: 1800)
#   pool_pre_ping     → execute a lightweight SELECT 1 before giving a connection
#                       from the pool — drops and replaces stale connections silently.

async_engine = create_async_engine(
    settings.ASYNC_DATABASE_URI,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
    echo=settings.DEBUG,  # Log all SQL statements in DEBUG mode only
)

# ─── Session Factory ──────────────────────────────────────────────────────────
#
# async_sessionmaker is the 2.0-style replacement for sessionmaker().
# expire_on_commit=False prevents SQLAlchemy from expiring all attributes
# after a commit — without this, accessing an attribute after commit triggers
# a lazy-load which fails in async context.

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ─── FastAPI Dependency ───────────────────────────────────────────────────────
#
# get_db() is injected into route handlers and services via Depends(get_db).
# It creates a new AsyncSession per request and guarantees cleanup on completion
# or exception via the finally block.
#
# Usage:
#   async def some_route(db: AsyncSession = Depends(get_db)):
#       ...


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
