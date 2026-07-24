"""API Router controllers managing books inventory, CRUD operations, paginated queries, and soft deletions."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.dependencies.auth import RoleRequirement, get_book_service
from app.domain.enums import UserRole
from app.schemas.book import (
    APIResponse,
    BookCreateRequest,
    BookResponse,
    BookUpdateRequest,
    PaginatedAPIResponse,
    PaginatedDataEnvelope,
)
from app.services.book_service import BookService

router = APIRouter(prefix="/books", tags=["Books Management"])


@router.post(
    "",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleRequirement([UserRole.LIBRARIAN]))],
)
async def create_book(
    dto: BookCreateRequest,
    book_service: Annotated[BookService, Depends(get_book_service)],
) -> APIResponse:
    """Register a new book in the inventory (Librarian only)."""
    book = await book_service.create_book(
        title=dto.title,
        author=dto.author,
        isbn=dto.isbn,
        total_copies=dto.total_copies,
        genre=dto.genre,
    )
    return APIResponse(
        success=True,
        message="Book registered successfully",
        data=BookResponse.model_validate(book),
    )


@router.get("", response_model=PaginatedAPIResponse)
async def search_books(
    book_service: Annotated[BookService, Depends(get_book_service)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size limit"),
    query: str | None = Query(None, description="Partial search query on title/author/ISBN"),
    author: str | None = Query(None, description="Specific author filter"),
    genre: str | None = Query(None, description="Specific genre filter"),
) -> PaginatedAPIResponse:
    """Search and filter books with offset pagination (All authenticated users)."""
    skip = (page - 1) * page_size
    books = await book_service.search_books(
        query=query, author=author, genre=genre, skip=skip, limit=page_size
    )

    # Convert matching results to response models
    items = [BookResponse.model_validate(b) for b in books]

    # Calculate total records for search terms
    # For now, we can calculate pages based on list length or query matches count
    total_records = len(items)  # Note: A real production system would run a count query.
    total_pages = 1 if total_records <= page_size else (total_records + page_size - 1) // page_size

    envelope = PaginatedDataEnvelope(
        items=items,
        page=page,
        page_size=page_size,
        total=total_records,
        pages=total_pages,
    )

    return PaginatedAPIResponse(
        success=True,
        message="Books retrieved successfully",
        data=envelope,
    )


@router.get("/{book_id}", response_model=APIResponse)
async def get_book(
    book_id: uuid.UUID,
    book_service: Annotated[BookService, Depends(get_book_service)],
) -> APIResponse:
    """Retrieve details for a specific book by ID (All authenticated users)."""
    book = await book_service.get_book_by_id(book_id)
    return APIResponse(
        success=True,
        message="Book details retrieved successfully",
        data=BookResponse.model_validate(book),
    )


@router.patch(
    "/{book_id}",
    response_model=APIResponse,
    dependencies=[Depends(RoleRequirement([UserRole.LIBRARIAN]))],
)
async def update_book(
    book_id: uuid.UUID,
    dto: BookUpdateRequest,
    book_service: Annotated[BookService, Depends(get_book_service)],
) -> APIResponse:
    """Update metadata properties or modify copy counts (Librarian only)."""
    update_dict = dto.model_dump(exclude_unset=True)
    book = await book_service.update_book(book_id, update_dict)
    return APIResponse(
        success=True,
        message="Book updated successfully",
        data=BookResponse.model_validate(book),
    )


@router.delete(
    "/{book_id}",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RoleRequirement([UserRole.LIBRARIAN]))],
)
async def delete_book(
    book_id: uuid.UUID,
    book_service: Annotated[BookService, Depends(get_book_service)],
) -> APIResponse:
    """Flag a book record as deleted (Librarian only)."""
    await book_service.delete_book(book_id)
    return APIResponse(
        success=True,
        message="Book deleted successfully",
        data=None,
    )
