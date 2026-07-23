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
