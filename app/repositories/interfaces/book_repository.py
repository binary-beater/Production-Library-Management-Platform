from typing import Protocol

from app.models.book import Book
from app.repositories.interfaces.base import BaseRepositoryInterface


class BookRepositoryInterface(BaseRepositoryInterface[Book], Protocol):
    """Protocol defining book-specific database queries."""

    async def get_by_isbn(self, isbn: str) -> Book | None: ...

    async def search_books(
        self,
        *,
        query: str | None = None,
        author: str | None = None,
        genre: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Book]: ...
