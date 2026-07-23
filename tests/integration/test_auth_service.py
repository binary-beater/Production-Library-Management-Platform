import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    EmailAlreadyExistsException,
    InactiveUserException,
    InvalidCredentialsException,
    TokenRevokedException,
)
from app.core.security import PasswordHasher
from app.dependencies.auth import jwt_manager
from app.domain.enums import MembershipStatus, UserStatus
from app.repositories.member_repository import MemberRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import ClientMetadata, UserLoginRequest, UserRegisterRequest
from app.services.auth_service import AuthService


@pytest.fixture
def auth_service(db_session: AsyncSession) -> AuthService:
    """Fixture providing AuthService instance."""
    user_repo = UserRepository(db_session)
    member_repo = MemberRepository(db_session)
    token_repo = RefreshTokenRepository(db_session)
    return AuthService(
        session=db_session,
        user_repo=user_repo,
        member_repo=member_repo,
        token_repo=token_repo,
        password_hasher=PasswordHasher(),
        jwt_manager=jwt_manager,
    )


@pytest.mark.asyncio
async def test_password_hasher_matches() -> None:
    hasher = PasswordHasher()
    pwd = "SecurePassword123!"
    h = hasher.hash_password(pwd)
    assert h != pwd
    assert hasher.verify_password(pwd, h) is True
    assert hasher.verify_password("wrong_password", h) is False


@pytest.mark.asyncio
async def test_auth_register_creates_user_and_member(
    db_session: AsyncSession, auth_service: AuthService
) -> None:
    db = auth_service.session
    dto = UserRegisterRequest(
        name="John Doe",
        email="john_doe@example.com",
        password="SecurePassword123!",
    )

    # 1. Register User
    user = await auth_service.register(dto)
    await db.flush()
    assert user.id is not None
    assert user.email == "john_doe@example.com"

    # 2. Verify Member auto-creation
    member_repo = MemberRepository(db)
    member = await member_repo.get_by_user_id(user.id)
    assert member is not None
    assert member.membership_status == MembershipStatus.ACTIVE
    assert member.membership_number.startswith("LMP-")


@pytest.mark.asyncio
async def test_auth_register_email_duplication_fails(
    auth_service: AuthService, db_session: AsyncSession
) -> None:
    dto = UserRegisterRequest(
        name="Jane",
        email="auth_duplicate@example.com",
        password="SecurePassword123!",
    )
    await auth_service.register(dto)
    await db_session.flush()

    with pytest.raises(EmailAlreadyExistsException):
        await auth_service.register(dto)


@pytest.mark.asyncio
async def test_auth_login_verifies_successfully(
    auth_service: AuthService, db_session: AsyncSession
) -> None:
    # 1. Register User
    dto_reg = UserRegisterRequest(
        name="Alice",
        email="alice@example.com",
        password="SecurePassword123!",
    )
    await auth_service.register(dto_reg)
    await db_session.flush()

    # 2. Login
    dto_login = UserLoginRequest(email="alice@example.com", password="SecurePassword123!")
    meta = ClientMetadata(ip_address="127.0.0.1", user_agent="Mozilla/5.0", device_name="Chrome")

    access_token, refresh_token = await auth_service.login(dto_login, meta)
    assert access_token is not None
    assert refresh_token is not None


@pytest.mark.asyncio
async def test_auth_login_mismatched_password_fails(
    auth_service: AuthService, db_session: AsyncSession
) -> None:
    dto_reg = UserRegisterRequest(
        name="Bob",
        email="bob@example.com",
        password="SecurePassword123!",
    )
    await auth_service.register(dto_reg)
    await db_session.flush()

    dto_login = UserLoginRequest(email="bob@example.com", password="WrongPassword123!")
    meta = ClientMetadata(ip_address="127.0.0.1")

    with pytest.raises(InvalidCredentialsException):
        await auth_service.login(dto_login, meta)


@pytest.mark.asyncio
async def test_auth_login_inactive_user_fails(
    auth_service: AuthService, db_session: AsyncSession
) -> None:
    # Register and manually deactivate User
    dto_reg = UserRegisterRequest(
        name="Charlie",
        email="charlie@example.com",
        password="SecurePassword123!",
    )
    user = await auth_service.register(dto_reg)
    await db_session.flush()

    user.status = UserStatus.SUSPENDED
    db_session.add(user)
    await db_session.flush()

    dto_login = UserLoginRequest(email="charlie@example.com", password="SecurePassword123!")
    meta = ClientMetadata(ip_address="127.0.0.1")

    with pytest.raises(InactiveUserException):
        await auth_service.login(dto_login, meta)


@pytest.mark.asyncio
async def test_refresh_token_rotation_succeeds(
    auth_service: AuthService, db_session: AsyncSession
) -> None:
    # 1. Register & Login
    dto_reg = UserRegisterRequest(
        name="Dave",
        email="dave@example.com",
        password="SecurePassword123!",
    )
    await auth_service.register(dto_reg)
    await db_session.flush()

    dto_login = UserLoginRequest(email="dave@example.com", password="SecurePassword123!")
    meta = ClientMetadata(ip_address="127.0.0.1")
    _, refresh_token = await auth_service.login(dto_login, meta)

    # 2. Refresh (RTR)
    new_access, new_refresh = await auth_service.refresh_token(refresh_token, meta)
    assert new_access is not None
    assert new_refresh != refresh_token


@pytest.mark.asyncio
async def test_refresh_token_reuse_revokes_entire_family(
    auth_service: AuthService, db_session: AsyncSession
) -> None:
    # 1. Register & Login
    dto_reg = UserRegisterRequest(
        name="Eve",
        email="eve@example.com",
        password="SecurePassword123!",
    )
    await auth_service.register(dto_reg)
    await db_session.flush()

    dto_login = UserLoginRequest(email="eve@example.com", password="SecurePassword123!")
    meta = ClientMetadata(ip_address="127.0.0.1")
    _, refresh_token = await auth_service.login(dto_login, meta)

    # 2. Refresh First Time (Clean rotation)
    _, new_refresh = await auth_service.refresh_token(refresh_token, meta)

    # 3. Reuse original refresh_token (Simulation of Replay Attack)
    with pytest.raises(TokenRevokedException):
        await auth_service.refresh_token(refresh_token, meta)

    # 4. Verify new_refresh is also invalidated
    with pytest.raises(TokenRevokedException):
        await auth_service.refresh_token(new_refresh, meta)


@pytest.mark.asyncio
async def test_logout_invalidates_session(
    auth_service: AuthService, db_session: AsyncSession
) -> None:
    # 1. Register & Login
    dto_reg = UserRegisterRequest(
        name="Frank",
        email="frank@example.com",
        password="SecurePassword123!",
    )
    await auth_service.register(dto_reg)
    await db_session.flush()

    dto_login = UserLoginRequest(email="frank@example.com", password="SecurePassword123!")
    meta = ClientMetadata(ip_address="127.0.0.1")
    _, refresh_token = await auth_service.login(dto_login, meta)

    # 2. Logout
    await auth_service.logout(refresh_token)

    # 3. Verify it cannot be refreshed anymore
    with pytest.raises(TokenRevokedException):
        await auth_service.refresh_token(refresh_token, meta)
