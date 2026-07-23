# 0010 - Transactional Decorator Pattern

## Context
Services coordinating multi-step database operations (e.g., borrow a book: check availability → decrement copies → create borrow record) must be atomic. If the borrow record creation fails after decrementing copies, inventory becomes corrupted.

## Decision
We implement a `@transactional` decorator in `app/db/transaction.py` that wraps async service methods in a SQLAlchemy `session.begin()` context automatically.

## Without This Pattern (Repeated Boilerplate)
```python
async def borrow_book(self, ...) -> BorrowRecord:
    async with self.session.begin():
        book = await self.book_repo.get_by_id(book_id)
        book.available_copies -= 1
        record = BorrowRecord(...)
        self.session.add(record)
        return record
```

## With `@transactional`
```python
@transactional
async def borrow_book(self, ...) -> BorrowRecord:
    book = await self.book_repo.get_by_id(book_id)
    book.available_copies -= 1
    record = BorrowRecord(...)
    self.session.add(record)
    return record
```

## Benefits
1. Eliminates repeated `async with session.begin()` boilerplate.
2. Makes atomicity intent explicit at the method signature level.
3. Automatically rolls back on any unhandled exception.
4. Senior-level pattern — most tutorials never reach this.

## Alternatives Considered
- *Manual `session.begin()` in every method*: Works but pollutes business logic with infrastructure concerns.
- *Unit of Work pattern*: More powerful but significantly more complex. Documented as a future evolution path.
