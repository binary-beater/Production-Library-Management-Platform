import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.repositories.base import BaseRepository
from app.repositories.interfaces.book_repository import BookRepositoryInterface


class BookRepository(BaseRepository[Book], BookRepositoryInterface):
    """BookRepository implementation matching BookRepositoryInterface."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Book, session)

    async def get_by_id(self, id: uuid.UUID) -> Book | None:
        """Fetch a single book by ID, enforcing soft delete checks."""
        result = await self.session.execute(
            select(Book).where(Book.id == str(id), Book.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def get_all(self, *, skip: int = 0, limit: int = 20) -> list[Book]:
        """Fetch active books, excluding soft deleted ones."""
        result = await self.session.execute(
            select(Book).where(Book.is_deleted == False).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_isbn(self, isbn: str) -> Book | None:
        """Fetch book by isbn (only active records)."""
        result = await self.session.execute(
            select(Book).where(Book.isbn == isbn, Book.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def search_books(
        self,
        *,
        query: str | None = None,
        author: str | None = None,
        genre: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Book]:
        """Flexible search with filters, excluding soft deleted books."""
        stmt = select(Book).where(Book.is_deleted == False)

        if query:
            stmt = stmt.where(
                or_(
                    Book.title.icontains(query),
                    Book.author.icontains(query),
                    Book.isbn.icontains(query),
                )
            )
        if author:
            stmt = stmt.where(Book.author.icontains(author))
        if genre:
            stmt = stmt.where(Book.genre.icontains(genre))

        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, id: uuid.UUID) -> bool:
        """Enforce soft delete action instead of hard row purge."""
        book = await self.get_by_id(id)
        if not book:
            return False
        book.is_deleted = True
        import datetime

        book.deleted_at = datetime.datetime.now(datetime.UTC)
        self.session.add(book)
        return True
