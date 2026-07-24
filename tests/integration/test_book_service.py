import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BookNotFoundException
from app.repositories.book_repository import BookRepository
from app.services.book_service import BookService


@pytest.fixture
def book_service(db_session: AsyncSession) -> BookService:
    book_repo = BookRepository(db_session)
    return BookService(session=db_session, book_repo=book_repo)


@pytest.mark.asyncio
async def test_create_and_get_book_succeeds(book_service: BookService) -> None:
    # 1. Create a book
    book = await book_service.create_book(
        title="Software Engineering Principles",
        author="John Doe",
        isbn="9780131103327",
        total_copies=5,
        genre="Computer Science",
    )
    assert book.id is not None
    assert book.title == "Software Engineering Principles"
    assert book.available_copies == 5

    # 2. Retrieve the book
    fetched = await book_service.get_book_by_id(book.id)
    assert fetched.title == "Software Engineering Principles"
    assert fetched.isbn == "9780131103327"


@pytest.mark.asyncio
async def test_create_duplicate_isbn_fails(book_service: BookService) -> None:
    await book_service.create_book(
        title="Book A", author="Author A", isbn="9781111111111", total_copies=3
    )
    with pytest.raises(ValueError, match="already exists"):
        await book_service.create_book(
            title="Book B", author="Author B", isbn="9781111111111", total_copies=1
        )


@pytest.mark.asyncio
async def test_update_book_metadata_and_copies(book_service: BookService) -> None:
    book = await book_service.create_book(
        title="Refactoring", author="Martin Fowler", isbn="9780201485677", total_copies=3
    )

    # Update title and increase total copies
    updated = await book_service.update_book(
        book.id, {"title": "Refactoring (2nd Edition)", "total_copies": 5}
    )
    assert updated.title == "Refactoring (2nd Edition)"
    assert updated.total_copies == 5
    assert updated.available_copies == 5


@pytest.mark.asyncio
async def test_update_book_invalid_copies_reduction_fails(book_service: BookService) -> None:
    book = await book_service.create_book(
        title="Refactoring", author="Martin Fowler", isbn="9780201485677", total_copies=3
    )
    # Reducing below negative is caught by value check
    with pytest.raises(ValueError):
        await book_service.update_book(book.id, {"total_copies": -1})


@pytest.mark.asyncio
async def test_soft_delete_book(book_service: BookService) -> None:
    book = await book_service.create_book(
        title="Design Patterns", author="Gang of Four", isbn="9780201633610", total_copies=2
    )

    # Soft delete the book
    await book_service.delete_book(book.id)

    # Fetching should raise BookNotFoundException
    with pytest.raises(BookNotFoundException):
        await book_service.get_book_by_id(book.id)


@pytest.mark.asyncio
async def test_search_books_paginated(book_service: BookService) -> None:
    await book_service.create_book(
        title="Clean Code", author="Robert Martin", isbn="9780132350884", total_copies=5
    )
    await book_service.create_book(
        title="Clean Architecture", author="Robert Martin", isbn="9780134494166", total_copies=3
    )

    # Search for Martin's books
    results = await book_service.search_books(query="Martin", limit=10)
    assert len(results) == 2

    # Filter by specific genre
    results_cs = await book_service.search_books(query="Clean", limit=1)
    assert len(results_cs) == 1
