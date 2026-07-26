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
        if not hasattr(self.session, "_transactional_depth"):
            self.session._transactional_depth = 0

        if self.session._transactional_depth > 0:
            self.session._transactional_depth += 1
            try:
                return await func(self, *args, **kwargs)
            finally:
                self.session._transactional_depth -= 1
        else:
            self.session._transactional_depth = 1
            try:
                # If the session has an active implicit transaction (from prior read queries),
                # commit it first to clear the transaction state before starting our explicit write block.
                if self.session.in_transaction():
                    await self.session.commit()

                async with self.session.begin():
                    return await func(self, *args, **kwargs)
            finally:
                self.session._transactional_depth -= 1

    return wrapper  # type: ignore[return-value]
