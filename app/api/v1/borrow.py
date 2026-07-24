"""API Router controllers managing books checkouts, returns, renewals, and history queries."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException
from app.db.session import get_db
from app.dependencies.auth import get_borrow_service, get_current_user
from app.models.user import User
from app.repositories.member_repository import MemberRepository
from app.schemas.book import APIResponse
from app.schemas.borrow import BorrowHistoryResponse, BorrowRequest, ReturnResponse
from app.services.borrow_service import BorrowService

router = APIRouter(prefix="/borrow", tags=["Borrowing & Returns Operations"])


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def borrow_book(
    dto: BorrowRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    borrow_service: Annotated[BorrowService, Depends(get_borrow_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse:
    """Check out a book (All authenticated members)."""
    # Retrieve member record associated with user ID
    member_repo = MemberRepository(db)
    member = await member_repo.get_by_user_id(current_user.id)
    if not member:
        raise ForbiddenException("User does not have an active Member profile")

    record = await borrow_service.borrow_book(member_id=member.id, book_id=uuid.UUID(dto.book_id))
    return APIResponse(
        success=True,
        message="Book checked out successfully",
        data={
            "borrow_record_id": str(record.id),
            "due_date": record.due_date.isoformat(),
        },
    )


@router.post("/{borrow_id}/return", response_model=APIResponse)
async def return_book(
    borrow_id: uuid.UUID,
    borrow_service: Annotated[BorrowService, Depends(get_borrow_service)],
) -> APIResponse:
    """Return a borrowed book (All authenticated users / Librarians)."""
    record = await borrow_service.return_book(borrow_id)
    response_data = ReturnResponse(
        borrow_id=str(record.id),
        book_id=str(record.book_id),
        member_id=str(record.member_id),
        return_date=record.return_date,  # type: ignore[arg-type] # return_date is set in return_book
        status=record.status.value,
        fine_amount=getattr(record, "fine_amount", 0.0),
    )
    return APIResponse(
        success=True,
        message="Book returned successfully",
        data=response_data,
    )


@router.post("/{borrow_id}/renew", response_model=APIResponse)
async def renew_book(
    borrow_id: uuid.UUID,
    borrow_service: Annotated[BorrowService, Depends(get_borrow_service)],
) -> APIResponse:
    """Renew a checked-out book (All authenticated members)."""
    record = await borrow_service.renew_book(borrow_id)
    return APIResponse(
        success=True,
        message="Borrowing renewed successfully",
        data={
            "borrow_record_id": str(record.id),
            "due_date": record.due_date.isoformat(),
            "renewal_count": record.renewal_count,
        },
    )


@router.get("/history", response_model=APIResponse)
async def get_history(
    current_user: Annotated[User, Depends(get_current_user)],
    borrow_service: Annotated[BorrowService, Depends(get_borrow_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size limit"),
) -> APIResponse:
    """Retrieve full checkout history for the current member (All authenticated members)."""
    member_repo = MemberRepository(db)
    member = await member_repo.get_by_user_id(current_user.id)
    if not member:
        raise ForbiddenException("User does not have an active Member profile")

    # Fetch borrow records with relation joins or manual updates
    records = await borrow_service.get_borrow_history(
        member_id=member.id, page=page, page_size=page_size
    )

    # Convert to response structures
    items = []
    # Eagerly load book titles for response serialization.
    # Because book relation is mapped in model, SQLAlchemy loads it automatically when accessed.
    for r in records:
        items.append(
            BorrowHistoryResponse(
                id=str(r.id),
                book_id=str(r.book_id),
                book_title=r.book.title,
                borrow_date=r.borrow_date,
                due_date=r.due_date,
                return_date=r.return_date,
                status=r.status.value,
                renewal_count=r.renewal_count,
            )
        )

    return APIResponse(
        success=True,
        message="Borrowing history retrieved successfully",
        data=items,
    )
