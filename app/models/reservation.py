import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, utcnow
from app.domain.enums import ReservationStatus

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.member import Member


class Reservation(Base, TimestampMixin):
    """ORM Model for the 'reservations' table.

    Tracks FIFO queues and hold allocations when books are out of stock.
    Inherits TimestampMixin directly as it preserves audits.
    """

    __tablename__ = "reservations"

    id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid.uuid4,
    )

    member_id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        ForeignKey("members.id", ondelete="RESTRICT"),
        nullable=False,
    )

    book_id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        ForeignKey("books.id", ondelete="RESTRICT"),
        nullable=False,
    )

    reserved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    status: Mapped[ReservationStatus] = mapped_column(
        SQLEnum(ReservationStatus),
        nullable=False,
        default=ReservationStatus.PENDING,
        server_default=ReservationStatus.PENDING.value,
    )

    # Relationships
    member: Mapped["Member"] = relationship("Member", back_populates="reservations")
    book: Mapped["Book"] = relationship("Book", back_populates="reservations")

    __table_args__ = (
        Index("idx_reservations_fifo", "book_id", "status", "reserved_at"),
        Index("idx_reservations_member", "member_id", "status"),
    )
