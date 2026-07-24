"""
Domain Enums — Library Management Platform

All enum values use (str, Enum) so they:
  1. Serialize to plain strings in JSON responses automatically
  2. Are stored as VARCHAR/ENUM in MySQL
  3. Work natively with Pydantic v2 without custom serializers
"""

from enum import Enum


class UserRole(str, Enum):
    """Roles assigned to user accounts for RBAC enforcement."""

    ADMIN = "ADMIN"
    LIBRARIAN = "LIBRARIAN"
    MEMBER = "MEMBER"


class UserStatus(str, Enum):
    """Lifecycle status of a user account."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class MembershipStatus(str, Enum):
    """Operational status of a library member profile."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class BorrowStatus(str, Enum):
    """
    State machine for a borrow transaction lifecycle.

    Transitions:
        BORROWED → RETURNED  (book returned)
        BORROWED → RENEWED   (loan extended, renewal_count += 1)
        BORROWED → OVERDUE   (due_date passed without return)
        RENEWED  → RETURNED  (returned after renewal)
        RENEWED  → OVERDUE   (overdue after renewal)
    """

    BORROWED = "BORROWED"
    RETURNED = "RETURNED"
    RENEWED = "RENEWED"
    OVERDUE = "OVERDUE"


class BookCondition(str, Enum):
    """Physical condition of a book copy."""

    NEW = "NEW"
    GOOD = "GOOD"
    FAIR = "FAIR"
    POOR = "POOR"


class TokenType(str, Enum):
    """
    Type of authentication token stored in the refresh_tokens table.
    Extensible for future token types (e.g., EMAIL_VERIFICATION, PASSWORD_RESET).
    """

    REFRESH = "REFRESH"


class ReservationStatus(str, Enum):
    """State machine status representing the lifecycle of a book reservation."""

    PENDING = "PENDING"
    HOLD = "HOLD"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
