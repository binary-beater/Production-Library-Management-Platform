import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, utcnow
from app.domain.enums import BorrowStatus

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.member import Member


class BorrowRecord(Base, TimestampMixin):
    """
    ORM Model for the 'borrow_records' table.

    Inherits TimestampMixin directly since it acts as an immutable audit record.
    SoftDelete and AuditMixins are excluded.
    """

    __tablename__ = "borrow_records"

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

    borrow_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    due_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    return_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    renewal_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default="0",
    )

    status: Mapped[BorrowStatus] = mapped_column(
        SQLEnum(BorrowStatus),
        nullable=False,
        default=BorrowStatus.BORROWED,
        server_default=BorrowStatus.BORROWED.value,
    )

    # Relationships
    member: Mapped["Member"] = relationship("Member", back_populates="borrow_records")

    book: Mapped["Book"] = relationship("Book", back_populates="borrow_records")

    __table_args__ = (
        Index("idx_borrow_member_id", "member_id"),
        Index("idx_borrow_book_id", "book_id"),
        Index("idx_borrow_status", "status"),
        Index("idx_borrow_due_date", "due_date", "status"),
        CheckConstraint("renewal_count >= 0", name="chk_borrow_renewal_count_non_negative"),
        CheckConstraint("renewal_count <= 2", name="chk_borrow_renewal_count_max_limit"),
    )
