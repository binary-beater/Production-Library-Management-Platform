# 0013 - Async SQLAlchemy 2.0 with aiomysql

## Context
FastAPI runs on an async event loop (Uvicorn + asyncio). Synchronous database drivers block the event loop — a single slow query pauses all concurrent request handling.

## Decision
We use **SQLAlchemy 2.0** with `AsyncSession` and the **`aiomysql`** async MySQL driver.

## Architecture Impact
```
FastAPI (async) → AsyncSession → aiomysql → MySQL 8.0
```
All database I/O is non-blocking. The event loop can handle other requests while waiting for MySQL to respond.

## SQLAlchemy 2.0 Model Syntax
```python
# 1.4 style (untyped, Mypy cannot check)
class User(Base):
    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False)

# 2.0 style (fully typed, Mypy understands)
class User(Base):
    id: Mapped[uuid.UUID] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
```

## Dual Driver Strategy
- **`aiomysql`**: Used by the application's `AsyncEngine` for all runtime queries.
- **`pymysql`**: Used only by Alembic CLI migrations — Alembic does not support async drivers.

## Connection Pool Configuration
```python
create_async_engine(
    uri,
    pool_size=10,        # Persistent connections kept open
    max_overflow=20,     # Burst connections under spike load
    pool_timeout=30,     # Wait time before raising PoolTimeout
    pool_recycle=1800,   # Recycle connections every 30 minutes
)                        # Prevents MySQL "server has gone away" errors
```
