"""Authentication dependencies for FastAPI routes (hashing context, JWT validation, and RBAC)."""

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    ForbiddenException,
    InactiveUserException,
    UnauthorizedException,
)
from app.core.security import JWTManager, PasswordHasher
from app.db.session import get_db
from app.domain.enums import UserRole, UserStatus
from app.models.user import User
from app.repositories.book_repository import BookRepository
from app.repositories.borrow_repository import BorrowRecordRepository
from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.member_repository import MemberRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.book_service import BookService
from app.services.borrow_service import BorrowService
from app.services.dashboard_service import DashboardService
from app.services.reservation_service import ReservationService

security_scheme = HTTPBearer(auto_error=False)

# Singleton instances of managers
password_hasher = PasswordHasher()
jwt_manager = JWTManager(
    signing_key=settings.SECRET_KEY,
    algorithm="HS256",
    issuer="library-management-platform",
    audience="library-management-platform-clients",
    access_token_expire_minutes=15,
)


def get_auth_service(db: Annotated[AsyncSession, Depends(get_db)]) -> AuthService:
    """Dependency provider for AuthService."""
    user_repo = UserRepository(db)
    member_repo = MemberRepository(db)
    token_repo = RefreshTokenRepository(db)
    return AuthService(
        session=db,
        user_repo=user_repo,
        member_repo=member_repo,
        token_repo=token_repo,
        password_hasher=password_hasher,
        jwt_manager=jwt_manager,
    )


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Validate bearer token credentials and return current User database instance.

    Args:
        request: The incoming HTTP request.
        credentials: The parsed Authorization header.
        db: Database session.

    Returns:
        User model instance if token checks pass.
    """
    if not credentials or credentials.scheme.lower() != "bearer":
        raise UnauthorizedException("Missing or invalid Authorization header")

    try:
        # Validate signature, expiration, NBF, aud, and iss
        payload = jwt_manager.decode_and_validate_token(credentials.credentials)
    except JWTError as e:
        raise UnauthorizedException(f"Token validation failed: {e}") from e

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Missing subject (sub) claim")

    # Retrieve matching user record
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)  # type: ignore[arg-type] # get_by_id accepts UUID, user_id is str string
    if not user:
        raise UnauthorizedException("User associated with token does not exist")

    # Check user account status locks
    if user.status != UserStatus.ACTIVE:
        raise InactiveUserException()

    return user


class RoleRequirement:
    """Factory dependency class to enforce Role-Based Access Control (RBAC)."""

    def __init__(self, allowed_roles: list[UserRole]) -> None:
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: Annotated[User, Depends(get_current_user)]) -> User:
        """Enforce role constraint on current user context.

        Args:
            current_user: Currently authenticated user model instance.

        Returns:
            The User instance if their role is allowed.
        """
        if current_user.role not in self.allowed_roles:
            raise ForbiddenException()
        return current_user


def get_book_service(db: Annotated[AsyncSession, Depends(get_db)]) -> BookService:
    """Dependency provider for BookService."""
    book_repo = BookRepository(db)
    return BookService(session=db, book_repo=book_repo)


def get_reservation_service(db: Annotated[AsyncSession, Depends(get_db)]) -> ReservationService:
    """Dependency provider for ReservationService."""
    reservation_repo = ReservationRepository(db)
    book_repo = BookRepository(db)
    member_repo = MemberRepository(db)
    borrow_repo = BorrowRecordRepository(db)
    return ReservationService(
        session=db,
        reservation_repo=reservation_repo,
        book_repo=book_repo,
        member_repo=member_repo,
        borrow_repo=borrow_repo,
    )


def get_borrow_service(db: Annotated[AsyncSession, Depends(get_db)]) -> BorrowService:
    """Dependency provider for BorrowService."""
    member_repo = MemberRepository(db)
    book_repo = BookRepository(db)
    borrow_repo = BorrowRecordRepository(db)
    # Instantiate ReservationService manually to avoid circular dependencies
    reservation_repo = ReservationRepository(db)
    reservation_service = ReservationService(
        session=db,
        reservation_repo=reservation_repo,
        book_repo=book_repo,
        member_repo=member_repo,
        borrow_repo=borrow_repo,
    )
    return BorrowService(
        session=db,
        member_repo=member_repo,
        book_repo=book_repo,
        borrow_repo=borrow_repo,
        reservation_service=reservation_service,
    )


def get_dashboard_service(db: Annotated[AsyncSession, Depends(get_db)]) -> DashboardService:
    """Dependency provider for DashboardService."""
    dashboard_repo = DashboardRepository(db)
    return DashboardService(session=db, dashboard_repo=dashboard_repo)
