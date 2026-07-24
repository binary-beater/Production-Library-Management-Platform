import datetime
import uuid
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ReservationStatus

T = TypeVar("T")


class ReservationCreateRequest(BaseModel):
    """Validation schema for creating a new book reservation."""

    book_id: uuid.UUID = Field(..., description="ID of the book to reserve")


class ReservationBookInfo(BaseModel):
    """Core book details for nested reservation lists to avoid lazy loading timestamp audit fields."""

    id: uuid.UUID
    title: str
    author: str
    isbn: str

    model_config = ConfigDict(from_attributes=True)


class ReservationResponse(BaseModel):
    """Serialization schema for returning reservation details."""

    id: uuid.UUID
    member_id: uuid.UUID
    book_id: uuid.UUID
    reserved_at: datetime.datetime
    expires_at: datetime.datetime | None = None
    status: ReservationStatus
    queue_position: int | None = Field(
        None, description="Dynamic position in the FIFO queue (0 if hold/completed/etc)"
    )

    model_config = ConfigDict(from_attributes=True)


class ReservationDetailResponse(ReservationResponse):
    """Detailed reservation response containing nested book info, used in listing views."""

    book: ReservationBookInfo | None = None


class ReservationHistoryResponse(BaseModel):
    """Schema for a reservation history item, with detailed book metadata."""

    id: uuid.UUID
    book_id: uuid.UUID
    book_title: str
    book_author: str
    reserved_at: datetime.datetime
    expires_at: datetime.datetime | None = None
    status: ReservationStatus
    queue_position: int | None = None

    model_config = ConfigDict(from_attributes=True)


class APIResponse(BaseModel, Generic[T]):
    """Standard success API envelope matching Milestone 3 definitions."""

    success: bool = True
    message: str | None = None
    data: T | None = None


class PaginatedAPIResponse(BaseModel, Generic[T]):
    """Standard paginated listing API envelope matching Milestone 3 definitions."""

    success: bool = True
    message: str | None = None
    data: T
