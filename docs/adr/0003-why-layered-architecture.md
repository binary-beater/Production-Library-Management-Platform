# 0003 - Layered Architecture & Separation of Concerns

## Context
Tutorial-style backend projects often mix business logic, database queries, and route handlers directly inside API controllers or `crud.py` files.

## Decision
We enforce a strict **Layered Architecture (API -> Service -> Repository -> Database)**.

## Layer Rules
1. **API Layer (`app/api/v1/`)**: Handles HTTP requests/responses, status codes, and input/output Pydantic schemas. NO database queries or business rules allowed.
2. **Service Layer (`app/services/`)**: Enforces ALL domain business rules, atomic transactions, and validations. NO direct ORM queries or HTTP exception dependencies.
3. **Repository Layer (`app/repositories/`)**: Encapsulates ALL database queries via Async SQLAlchemy sessions. NO business rules allowed.

## Benefits
- High testability: Services can be unit-tested in isolation by mocking Repositories.
- Decoupling: Persistence layers can be swapped or refactored without breaking API contracts.
