import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Index, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin
from app.domain.enums import MembershipStatus

if TYPE_CHECKING:
    from app.models.borrow_record import BorrowRecord
    from app.models.user import User


class Member(Base, SoftDeleteMixin):
    """
    ORM Model for the 'members' table.

    Inherits SoftDeleteMixin (which inherits AuditMixin & TimestampMixin).
    Soft deleted to maintain borrow history metrics referential integrity.
    """

    __tablename__ = "members"

    id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )

    membership_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
    )

    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    joined_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)

    membership_status: Mapped[MembershipStatus] = mapped_column(
        SQLEnum(MembershipStatus),
        nullable=False,
        default=MembershipStatus.ACTIVE,
        server_default=MembershipStatus.ACTIVE.value,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="member")

    borrow_records: Mapped[list["BorrowRecord"]] = relationship(
        "BorrowRecord",
        back_populates="member",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_members_user_id", "user_id", unique=True),
        Index("idx_members_membership_num", "membership_number", unique=True),
        Index("idx_members_status", "membership_status"),
    )
