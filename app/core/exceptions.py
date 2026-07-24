"""Custom application exceptions mapping directly to HTTP status categories."""

from fastapi import HTTPException, status


class ApplicationException(HTTPException):
    """Base exception class for all custom domain exceptions."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "An unexpected error occurred"

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(
            status_code=self.status_code,
            detail=detail or self.detail,
        )


# ─── Auth Exception Classes ───────────────────────────────────────────────────


class InvalidCredentialsException(ApplicationException):
    """Raised when email or password verification fails."""

    status_code: int = status.HTTP_401_UNAUTHORIZED
    detail: str = "Invalid email or password"


class EmailAlreadyExistsException(ApplicationException):
    """Raised when registering an email address already stored in DB."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Email address is already registered"


class InactiveUserException(ApplicationException):
    """Raised when an authenticated user has an INACTIVE or SUSPENDED account status."""

    status_code: int = status.HTTP_403_FORBIDDEN
    detail: str = "User account is suspended or inactive"


class TokenExpiredException(ApplicationException):
    """Raised when validation checks confirm a JWT access or refresh token is expired."""

    status_code: int = status.HTTP_401_UNAUTHORIZED
    detail: str = "Authentication token has expired"


class TokenRevokedException(ApplicationException):
    """Raised when validating a token marked revoked inside MySQL."""

    status_code: int = status.HTTP_401_UNAUTHORIZED
    detail: str = "Authentication token has been revoked"


class InvalidRefreshTokenException(ApplicationException):
    """Raised when refresh token fingerprint checks fail validation."""

    status_code: int = status.HTTP_401_UNAUTHORIZED
    detail: str = "Invalid refresh token session"


class UnauthorizedException(ApplicationException):
    """Raised when access token validation fails or header is missing."""

    status_code: int = status.HTTP_401_UNAUTHORIZED
    detail: str = "Could not validate authentication credentials"


class ForbiddenException(ApplicationException):
    """Raised when RBAC rules restrict user capabilities."""

    status_code: int = status.HTTP_403_FORBIDDEN
    detail: str = "You do not have permission to access this resource"


# ─── Library Operations Exception Classes ──────────────────────────────────────


class BookNotFoundException(ApplicationException):
    """Raised when a requested book is not found in the inventory."""

    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Book not found"


class BookUnavailableException(ApplicationException):
    """Raised when a book exists but has 0 available copies."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Book is currently out of stock"


class BookDeletedException(ApplicationException):
    """Raised when trying to perform operations on a soft-deleted book."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Book is soft-deleted and cannot be modified or borrowed"


class BorrowLimitExceededException(ApplicationException):
    """Raised when a member has reached the maximum borrowing limit (5 books)."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Member has reached maximum borrowing limit"


class MemberInactiveException(ApplicationException):
    """Raised when trying to borrow books with an inactive member status."""

    status_code: int = status.HTTP_403_FORBIDDEN
    detail: str = "Member profile is inactive"


class MemberSuspendedException(ApplicationException):
    """Raised when trying to borrow books with a suspended member status."""

    status_code: int = status.HTTP_403_FORBIDDEN
    detail: str = "Member profile is suspended"


class BookAlreadyReturnedException(ApplicationException):
    """Raised when trying to return or renew an already returned borrow record."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Book has already been returned"


class RenewalLimitExceededException(ApplicationException):
    """Raised when a borrow record has already been renewed the maximum allowed times (2 times)."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Maximum renewal limit has been reached"


class OverdueMemberException(ApplicationException):
    """Raised when a member is blocked from checking out due to having active overdue loans."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Member is blocked due to active overdue borrow records"


class ConcurrentBorrowException(ApplicationException):
    """Raised when concurrent operations conflict on lock states."""

    status_code: int = status.HTTP_409_CONFLICT
    detail: str = "Operation failed due to concurrent modification conflicts"


class ReservationLimitExceededException(ApplicationException):
    """Raised when a member has reached the active reservation limit (3 books)."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Member has reached maximum active reservations limit"


class AlreadyReservedException(ApplicationException):
    """Raised when a member already has an active reservation for this book."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Member already has an active reservation for this book"


class BookAlreadyBorrowedException(ApplicationException):
    """Raised when a member tries to reserve a book they already have checked out."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Member already has this book checked out"


class ReservationNotFoundException(ApplicationException):
    """Raised when a requested reservation is not found."""

    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Reservation not found"


class ReservationNotHeldException(ApplicationException):
    """Raised when trying to checkout a book reserved for another member."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "This book is currently held for another member's reservation"
