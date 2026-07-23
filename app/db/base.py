"""
app/db/base.py — SQLAlchemy Declarative Base and Column Mixins

Mixin hierarchy:
    Base
    └── TimestampMixin   (created_at, updated_at)
        └── AuditMixin   (created_by, updated_by — filled by auth middleware)
            └── SoftDeleteMixin (is_deleted, deleted_at)

All production models compose from this hierarchy.
BorrowRecord uses only TimestampMixin (immutable audit log — never soft deleted).
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Return current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """
    SQLAlchemy 2.0 declarative base.

    All ORM models inherit from this class. Using DeclarativeBase (2.0 style)
    instead of declarative_base() (1.4 style) enables full Mypy type inference
    on mapped_column() attributes.
    """

    pass


class TimestampMixin:
    """
    Adds created_at and updated_at columns to any model.

    - created_at: Set once at INSERT time using server_default.
    - updated_at: Updated on every UPDATE using onupdate.

    server_default=func.now() delegates the default to MySQL's NOW()
    rather than Python — ensuring consistency even if records are
    inserted via direct SQL or migrations.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AuditMixin(TimestampMixin):
    """
    Extends TimestampMixin with created_by and updated_by UUID references.

    These are nullable CHAR(36) columns (not FK constraints) because:
      1. The creator may not always be a system user (e.g., migration scripts).
      2. Circular FK dependencies with the users table are avoided.
      3. Auth middleware fills these during the request lifecycle.
    """

    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True, default=None)
    updated_by: Mapped[str | None] = mapped_column(String(36), nullable=True, default=None)


class SoftDeleteMixin(AuditMixin):
    """
    Extends AuditMixin with soft-delete support.

    Why soft delete?
      Physical deletion of Books or Members breaks referential integrity with
      historical borrow_records (BR-009). Soft delete preserves the record
      while hiding it from normal queries.

    is_deleted: Boolean flag. Repositories filter WHERE is_deleted = FALSE by default.
    deleted_at: Timestamp of deletion. Enables time-based auditing of deletions.
    """

    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
