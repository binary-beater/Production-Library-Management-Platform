"""BookService module managing books CRUD, soft-deletion, and metadata updates."""

import json
import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BookNotFoundException
from app.models.book import Book
from app.repositories.book_repository import BookRepository
from app.services.base import BaseService

logger = logging.getLogger(__name__)


class BookService(BaseService):
    """Service managing book inventory operations and metadata logic."""

    def __init__(self, session: AsyncSession, book_repo: BookRepository) -> None:
        """Initialize service with session and book repository."""
        super().__init__(session)
        self.book_repo = book_repo

    def _log_event(self, event: str, level: str = "info", **kwargs: Any) -> None:
        """Helper to write structured JSON log entries."""
        log_payload = {"event": event, "service": "BookService", **kwargs}
        if level == "error":
            logger.error(json.dumps(log_payload))
        else:
            logger.info(json.dumps(log_payload))

    async def get_book_by_id(self, book_id: uuid.UUID) -> Book:
        """Fetch a book by ID, enforcing soft delete checks.

        Args:
            book_id: Database identifier.

        Returns:
            The Book instance.

        Raises:
            BookNotFoundException: If book is not found or is soft-deleted.
        """
        self._log_event("book_get_start", book_id=str(book_id))
        book = await self.book_repo.get_by_id(book_id)
        if not book or book.is_deleted:
            self._log_event("book_get_not_found", level="error", book_id=str(book_id))
            raise BookNotFoundException()
        self._log_event("book_get_success", book_id=str(book_id))
        return book

    async def create_book(
        self, title: str, author: str, isbn: str, total_copies: int, genre: str | None = None
    ) -> Book:
        """Register a new book in the inventory.

        Args:
            title: Title of the book.
            author: Author of the book.
            isbn: Unique ISBN string.
            total_copies: Initial copies.
            genre: Optional category.

        Returns:
            The created Book record.
        """
        self._log_event(
            "book_created_start", title=title, author=author, isbn=isbn, total_copies=total_copies
        )
        existing_book = await self.book_repo.get_by_isbn(isbn)
        if existing_book:
            self._log_event("book_creation_failed_isbn_conflict", level="error", isbn=isbn)
            raise ValueError(f"Book with ISBN {isbn} already exists")

        book = Book(
            id=uuid.uuid4(),
            title=title,
            author=author,
            isbn=isbn,
            total_copies=total_copies,
            available_copies=total_copies,
            genre=genre,
            is_deleted=False,
        )
        await self.book_repo.create(book)
        await self.session.flush()
        await self.session.refresh(book)
        self._log_event("book_created", book_id=str(book.id), isbn=isbn)
        return book

    async def update_book(self, book_id: uuid.UUID, update_data: dict[str, Any]) -> Book:
        """Update metadata properties or modify copy inventories.

        Args:
            book_id: ID of book to update.
            update_data: Dict of attributes to change.

        Returns:
            The updated Book instance.
        """
        self._log_event(
            "book_update_start", book_id=str(book_id), update_fields=list(update_data.keys())
        )
        book = await self.book_repo.get_by_id_for_update(book_id)
        if not book or book.is_deleted:
            self._log_event("book_update_not_found", level="error", book_id=str(book_id))
            raise BookNotFoundException()

        # Handle copy total count adjustments safely
        if "total_copies" in update_data:
            new_total = update_data["total_copies"]
            if new_total < 0:
                raise ValueError("Total copies cannot be negative")

            diff = new_total - book.total_copies
            new_available = book.available_copies + diff
            if new_available < 0:
                self._log_event(
                    "book_update_failed_negative_available",
                    level="error",
                    book_id=str(book_id),
                    new_total=new_total,
                )
                raise ValueError("Cannot reduce total copies below currently checked out copies")

            book.total_copies = new_total
            book.available_copies = new_available

        # Remove total copies from update_data before calling base update to avoid double setting
        clean_update = {k: v for k, v in update_data.items() if k != "total_copies"}
        await self.book_repo.update(book, update_data=clean_update)
        await self.session.flush()
        await self.session.refresh(book)

        self._log_event("inventory_updated", book_id=str(book_id))
        return book

    async def delete_book(self, book_id: uuid.UUID) -> None:
        """Flag a book record as deleted (soft delete).

        Args:
            book_id: ID of book to delete.
        """
        self._log_event("book_delete_start", book_id=str(book_id))
        success = await self.book_repo.delete(book_id)
        if not success:
            self._log_event("book_delete_failed_not_found", level="error", book_id=str(book_id))
            raise BookNotFoundException()
        await self.session.flush()
        self._log_event("book_deleted", book_id=str(book_id))

    async def search_books(
        self,
        query: str | None = None,
        author: str | None = None,
        genre: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Book]:
        """Search and list books with pagination and criteria filters.

        Args:
            query: Keyword searching title/author/ISBN.
            author: Specific author filter.
            genre: Specific genre filter.
            skip: Page offset.
            limit: Page size limit.

        Returns:
            A list of matching Book instances.
        """
        self._log_event(
            "book_search", query=query, author=author, genre=genre, skip=skip, limit=limit
        )
        return await self.book_repo.search_books(
            query=query, author=author, genre=genre, skip=skip, limit=limit
        )
