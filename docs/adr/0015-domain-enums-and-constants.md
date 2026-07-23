# 0015 - Domain Enums and Business Constants Separation

## Context
Business rules like borrow limits and page sizes, and domain values like user roles and borrow statuses, need to live somewhere in the codebase. The wrong placement leads to magic strings and scattered duplication.

## Decision
We split them into two distinct modules:

### `app/domain/enums.py` — Domain State Values
Values representing the *state* of domain entities. They belong to the domain model, not infrastructure.
```python
class UserRole(str, Enum): ADMIN, LIBRARIAN, MEMBER
class BorrowStatus(str, Enum): BORROWED, RETURNED, RENEWED, OVERDUE
class MembershipStatus(str, Enum): ACTIVE, INACTIVE, SUSPENDED
class BookCondition(str, Enum): NEW, GOOD, FAIR, POOR
class TokenType(str, Enum): REFRESH
```

### `app/core/constants.py` — Business Rule Constants
Numeric thresholds and limits that govern business rules. They are stable, reviewed in code, and not configurable at runtime.
```python
MAX_BORROW_LIMIT: int = 5
MAX_RENEWALS: int = 2
DEFAULT_LOAN_DAYS: int = 14
DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100
```

## Why Not Environment Variables for Constants?
Environment variables are for **deployment-specific secrets and configuration** (DB passwords, API keys, hostnames). Business rules like "max 5 borrowed books" are domain decisions — they should be visible in code review, not hidden in infrastructure configuration.

## Why `str, Enum` for All Enums?
Using `class UserRole(str, Enum)` means enum values serialize to their string representation in JSON automatically. FastAPI and Pydantic both handle `str` subclasses natively without custom serializers.
