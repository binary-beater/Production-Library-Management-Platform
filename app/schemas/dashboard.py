import uuid

from pydantic import BaseModel, ConfigDict, Field


class InventorySummary(BaseModel):
    """Summarized stats of physical/digital books inventory."""

    total_titles: int = Field(..., description="Total unique book titles (excluding soft-deleted)")
    total_copies: int = Field(..., description="Sum of total_copies across all books")
    checked_out_copies: int = Field(..., description="Total copies currently checked out")
    available_copies: int = Field(..., description="Total copies currently available on shelves")

    model_config = ConfigDict(from_attributes=True)


class BorrowingVelocity(BaseModel):
    """Loan transaction rates over different rolling periods."""

    today: int = Field(..., description="Total checkouts today")
    last_7_days: int = Field(..., description="Total checkouts in the last 7 days")
    last_30_days: int = Field(..., description="Total checkouts in the last 30 days")

    model_config = ConfigDict(from_attributes=True)


class CirculationSummary(BaseModel):
    """General loan activity and circulation velocity info."""

    total_borrows_in_window: int = Field(..., description="Total borrows placed in custom window")
    borrowing_velocity: BorrowingVelocity

    model_config = ConfigDict(from_attributes=True)


class MemberSummary(BaseModel):
    """Aggregate statistics on library membership distribution."""

    active_count: int = Field(..., description="Total active members")
    suspended_count: int = Field(..., description="Total suspended members")

    model_config = ConfigDict(from_attributes=True)


class ReservationSummary(BaseModel):
    """Aggregate stats of reservation hold queue statuses."""

    pending: int = Field(..., description="Total active reservations waiting in queue (PENDING)")
    hold: int = Field(..., description="Total active reservations held for member checkout (HOLD)")
    expired_today: int = Field(..., description="Total reservations expired today (EXPIRED)")

    model_config = ConfigDict(from_attributes=True)


class OverdueSummary(BaseModel):
    """Analytics on late checkouts and return delays."""

    count: int = Field(..., description="Total active overdue borrow records")
    ratio: float = Field(..., description="Ratio of overdue loans to total active borrows")
    average_days_overdue: float = Field(
        ..., description="Average days overdue across currently overdue books"
    )

    model_config = ConfigDict(from_attributes=True)


class PopularBookItem(BaseModel):
    """Data item representing a highly borrowed book."""

    book_id: uuid.UUID
    title: str
    author: str
    checkout_count: int

    model_config = ConfigDict(from_attributes=True)


class DashboardSummaryResponse(BaseModel):
    """Consolidated payload containing librarian operational insights."""

    inventory: InventorySummary
    circulation: CirculationSummary
    members: MemberSummary
    reservations: ReservationSummary
    overdue: OverdueSummary
    popular_books: list[PopularBookItem]
    generated_at: str = Field(
        ..., description="ISO-8601 UTC timestamp when this dashboard was computed"
    )

    model_config = ConfigDict(from_attributes=True)
