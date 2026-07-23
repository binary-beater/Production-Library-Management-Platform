# 0008 - Use Repository Pattern for Data Access

## Context
Services need to query and persist data. Placing database queries directly inside service methods or API routes creates tightly-coupled code that is impossible to unit test without a real database.

## Decision
We implement the **Repository Pattern** — every entity has a dedicated repository class that encapsulates all database interactions. Services depend on repository interfaces (Protocols), not concrete implementations.

## Structure
```
repositories/
    base.py                  → Generic BaseRepository[T]
    interfaces/
        user_repository.py   → UserRepositoryInterface (Protocol)
        book_repository.py
        member_repository.py
        borrow_repository.py
    user_repository.py       → Concrete implementation
    book_repository.py
    member_repository.py
    borrow_repository.py
```

## Benefits
1. **Testability**: Services can be unit tested by injecting a mock that satisfies the Protocol — no database required.
2. **Single Responsibility**: Services never write SQL. Repositories never enforce business rules.
3. **Swappability**: Switching from MySQL to PostgreSQL only requires replacing repository implementations, not touching services or APIs.

## Trade-offs
- More files than a simple `crud.py`.
- Requires discipline to enforce the separation — developers must resist the temptation to add business logic into repositories.

## Alternatives Considered
- *Active Record*: Models contain their own query methods (Django ORM style). Rejected because it violates Single Responsibility and makes testing harder.
- *Plain `crud.py`*: Single file holding all database operations. Rejected because it becomes unmaintainable as query complexity grows.
