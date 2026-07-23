"""
app/db/transaction.py — @transactional Decorator

Provides a decorator that wraps async service methods in an explicit
SQLAlchemy database transaction (session.begin()).

If a transaction is already active on the session (e.g., from nested calls or active test session environments),
the decorator propagates the active transaction block rather than beginning a duplicate one.
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
        # If transaction is already active, run the function under the active boundary
        if self.session.in_transaction():
            return await func(self, *args, **kwargs)

        # Start a new transaction
        async with self.session.begin():
            return await func(self, *args, **kwargs)

    return wrapper  # type: ignore[return-value]
