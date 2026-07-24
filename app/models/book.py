import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Index, SmallInteger, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin
from app.domain.enums import BookCondition

if TYPE_CHECKING:
    from app.models.borrow_record import BorrowRecord
    from app.models.reservation import Reservation


class Book(Base, SoftDeleteMixin):
    """
    ORM Model for the 'books' table.

    Inherits SoftDeleteMixin (which inherits AuditMixin & TimestampMixin).
    Includes CheckConstraints to prevent negative count numbers.
    """

    __tablename__ = "books"

    id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid.uuid4,
    )

    isbn: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False)

    author: Mapped[str] = mapped_column(String(255), nullable=False)

    genre: Mapped[str | None] = mapped_column(String(100), nullable=True)

    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)

    publication_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    total_copies: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=1,
        server_default="1",
    )

    available_copies: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=1,
        server_default="1",
    )

    condition: Mapped[BookCondition] = mapped_column(
        SQLEnum(BookCondition),
        nullable=False,
        default=BookCondition.GOOD,
        server_default=BookCondition.GOOD.value,
    )

    borrow_records: Mapped[list["BorrowRecord"]] = relationship(
        "BorrowRecord",
        back_populates="book",
        cascade="all, delete-orphan",
    )

    reservations: Mapped[list["Reservation"]] = relationship(
        "Reservation",
        back_populates="book",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_books_isbn", "isbn", unique=True),
        Index("idx_books_title", "title"),
        Index("idx_books_author", "author"),
        Index("idx_books_genre", "genre"),
        CheckConstraint("total_copies >= 0", name="chk_books_total_copies_non_negative"),
        CheckConstraint(
            "available_copies >= 0",
            name="chk_books_available_copies_non_negative",
        ),
        CheckConstraint(
            "available_copies <= total_copies",
            name="chk_books_available_copies_lte_total",
        ),
    )
