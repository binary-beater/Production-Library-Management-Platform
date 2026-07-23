# 0002 - Use SQLAlchemy 2.0 Async ORM

## Context
Relational persistence in Python requires an Object-Relational Mapper (ORM) capable of handling transactions, complex queries, and async I/O.

## Decision
We adopt **SQLAlchemy 2.0** with `aiomysql` as our async database driver.

## Rationale & Benefits
1. **Type Safety & 2.0 Declarative Syntax**: Explicit type hints on models using `Mapped[T]` and `mapped_column()`.
2. **Asynchronous Execution**: Eliminates thread blocking during I/O operations via `AsyncSession` and `create_async_engine`.
3. **Repository Pattern Compatibility**: Cleanly abstracts database access away from business logic services.

## Trade-offs
- Steeper learning curve than standard synchronous ORMs.
- Explicit async session management (`async with AsyncSession()`) is required.
