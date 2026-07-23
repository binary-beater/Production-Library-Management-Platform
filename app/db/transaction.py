"""
app/db/transaction.py — @transactional Decorator

Provides a decorator that wraps async service methods in an explicit
SQLAlchemy database transaction (session.begin()).

Without this pattern every service method must repeat:
    async with self.session.begin():
        ...

With @transactional:
    @transactional
    async def borrow_book(self, ...) -> BorrowRecord:
        ...  # Transaction is managed automatically

Design:
  - The decorated method must belong to a class that exposes `self.session` as
    an AsyncSession attribute.
  - On success: the transaction is committed automatically.
  - On any exception: the transaction is rolled back and the exception re-raised,
    preserving the original traceback for logging and error handling.

This is a senior-level infrastructure pattern that eliminates boilerplate
transaction management from business logic while maintaining atomicity guarantees.
"""

import functools
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Coroutine[Any, Any, Any]])


def transactional(func: F) -> F:
    """
    Decorator that wraps an async method in a database transaction.

    Requires the decorated method's class to have `self.session: AsyncSession`.
    """

    @functools.wraps(func)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        async with self.session.begin():
            return await func(self, *args, **kwargs)

    return wrapper  # type: ignore[return-value]
