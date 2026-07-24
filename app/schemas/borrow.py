"""Pydantic validation schemas for Borrow domain entities and API contracts."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BorrowRequest(BaseModel):
    """Validation schema for creating a borrowing record."""

    book_id: str = Field(..., description="Unique database ID of the book being borrowed")


class ReturnResponse(BaseModel):
    """JSON response envelope schema representing a completed return operation details."""

    model_config = ConfigDict(from_attributes=True)

    borrow_id: str = Field(..., description="Unique DB identifier for the borrow record")
    book_id: str = Field(..., description="Unique database ID of the returned book")
    member_id: str = Field(..., description="Unique database ID of the returning member")
    return_date: datetime = Field(..., description="Timestamp of when the return was processed")
    status: str = Field(..., description="Final status transition (e.g. 'RETURNED')")
    fine_amount: float = Field(0.0, description="Calculated fine incurred for overdue duration")

    @field_validator("borrow_id", "book_id", "member_id", mode="before")
    @classmethod
    def coerce_ids_to_str(cls, v: Any) -> str:
        """Coerce incoming UUID instances to string to prevent serialization errors."""
        if isinstance(v, uuid.UUID):
            return str(v)
        return str(v)


class BorrowHistoryResponse(BaseModel):
    """JSON response envelope schema representing a borrow history entry."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique DB identifier for this borrow record")
    book_id: str = Field(..., description="Unique database ID of the book")
    book_title: str = Field(..., description="Title of the borrowed book")
    borrow_date: datetime = Field(..., description="Timestamp of when book was borrowed")
    due_date: datetime = Field(..., description="Timestamp of when book is due for return")
    return_date: datetime | None = Field(
        None, description="Timestamp of when book was returned (if returned)"
    )
    status: str = Field(..., description="Current status of the checkout")
    renewal_count: int = Field(..., description="Total successful renewal counts performed")

    @field_validator("id", "book_id", mode="before")
    @classmethod
    def coerce_ids_to_str(cls, v: Any) -> str:
        """Coerce incoming UUID instances to string to prevent serialization errors."""
        if isinstance(v, uuid.UUID):
            return str(v)
        return str(v)
