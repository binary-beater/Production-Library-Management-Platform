"""Pydantic validation schemas for Book domain entities and API contracts."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BookCreateRequest(BaseModel):
    """Validation schema for creating a new library Book."""

    title: str = Field(..., min_length=1, max_length=255, description="The title of the book")
    author: str = Field(..., min_length=1, max_length=255, description="The author of the book")
    isbn: str = Field(
        ..., min_length=10, max_length=13, description="The unique ISBN code of the book"
    )
    genre: str | None = Field(None, max_length=100, description="The genre or category of the book")
    total_copies: int = Field(
        ..., ge=0, description="The total number of physical copies in inventory"
    )


class BookUpdateRequest(BaseModel):
    """Validation schema for updating properties of an existing Book."""

    title: str | None = Field(
        None, min_length=1, max_length=255, description="The updated title of the book"
    )
    author: str | None = Field(
        None, min_length=1, max_length=255, description="The updated author of the book"
    )
    isbn: str | None = Field(
        None, min_length=10, max_length=13, description="The updated ISBN code of the book"
    )
    genre: str | None = Field(
        None, max_length=100, description="The updated genre or category of the book"
    )
    total_copies: int | None = Field(
        None, ge=0, description="The updated total number of physical copies"
    )


class BookResponse(BaseModel):
    """JSON response envelope schema representing a Book's details."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique DB identifier for the book")
    title: str = Field(..., description="Title of the book")
    author: str = Field(..., description="Author of the book")
    isbn: str = Field(..., description="Unique ISBN of the book")
    genre: str | None = Field(None, description="Genre of the book")
    total_copies: int = Field(..., description="Total copies registered")
    available_copies: int = Field(..., description="Current available physical copies in library")
    is_deleted: bool = Field(..., description="Soft delete state flag")
    created_at: datetime = Field(..., description="Entity creation timestamp")
    updated_at: datetime = Field(..., description="Entity last updated timestamp")

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id_to_str(cls, v: Any) -> str:
        """Coerce incoming UUID instances to string to prevent serialization errors."""
        if isinstance(v, uuid.UUID):
            return str(v)
        return str(v)


class APIResponse(BaseModel):
    """Standard successful API response envelope structure."""

    success: bool = Field(True, description="Indicates operation success")
    message: str = Field(..., description="Success messaging / description")
    data: Any | None = Field(None, description="Payload containing response details")


class PaginatedDataEnvelope(BaseModel):
    """Details containing paginated metadata inside response envelope."""

    items: list[Any]
    page: int
    page_size: int
    total: int
    pages: int


class PaginatedAPIResponse(BaseModel):
    """Standard envelope format for paginated collections."""

    success: bool = Field(True, description="Indicates operation success")
    message: str = Field(..., description="Success messaging / description")
    data: PaginatedDataEnvelope
