"""AuthService module implementing registration, login, token rotations (RTR), and logout business logic."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    EmailAlreadyExistsException,
    InactiveUserException,
    InvalidCredentialsException,
    InvalidRefreshTokenException,
    TokenExpiredException,
    TokenRevokedException,
)
from app.core.security import JWTManager, PasswordHasher, TokenManager
from app.db.transaction import transactional
from app.domain.enums import MembershipStatus, UserRole, UserStatus
from app.models.member import Member
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.member_repository import MemberRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import ClientMetadata, UserLoginRequest, UserRegisterRequest
from app.services.base import BaseService


class AuthService(BaseService):
    """AuthService coordinating authentication lifecycle and security operations."""

    def __init__(
        self,
        session: AsyncSession,
        user_repo: UserRepository,
        member_repo: MemberRepository,
        token_repo: RefreshTokenRepository,
        password_hasher: PasswordHasher,
        jwt_manager: JWTManager,
    ) -> None:
        """Initialize the AuthService with required repository instances and managers."""
        super().__init__(session)
        self.user_repo = user_repo
        self.member_repo = member_repo
        self.token_repo = token_repo
        self.password_hasher = password_hasher
        self.jwt_manager = jwt_manager

    @transactional
    async def register(self, dto: UserRegisterRequest) -> User:
        """Register a new user and automatically create a corresponding Member profile.

        All creations are wrapped inside an atomic transactional block.

        Args:
            dto: Registration details.

        Returns:
            The created User model instance.
        """
        # Verify email uniqueness
        existing_user = await self.user_repo.get_by_email(dto.email)
        if existing_user:
            raise EmailAlreadyExistsException()

        # Hash password using Argon2id
        hashed_password = self.password_hasher.hash_password(dto.password)

        # Create user
        user = User(
            name=dto.name,
            email=dto.email,
            password_hash=hashed_password,
            role=UserRole.MEMBER,
            status=UserStatus.ACTIVE,
        )
        # Register in session
        await self.user_repo.create(user)
        # Flush session to generate user ID for Member foreign key lookup
        await self.session.flush()

        # Generate unique membership number (e.g. LMP-[YEAR]-[RANDOM])
        now = datetime.now(UTC)
        random_suffix = uuid.uuid4().hex[:6].upper()
        membership_num = f"LMP-{now.year}-{random_suffix}"

        # Create member profile linked to the User
        member = Member(
            user_id=user.id,
            membership_number=membership_num,
            joined_date=now.date(),
            membership_status=MembershipStatus.ACTIVE,
        )
        await self.member_repo.create(member)
        await self.session.flush()

        return user

    @transactional
    async def login(
        self, dto: UserLoginRequest, client_metadata: ClientMetadata
    ) -> tuple[str, str]:
        """Authenticate user credentials and issue access and refresh tokens.

        Args:
            dto: Login payload (email and password).
            client_metadata: Metadata context parsed from request headers.

        Returns:
            A tuple of (access_token, raw_refresh_token).
        """
        # Lookup user profile
        user = await self.user_repo.get_by_email(dto.email)
        if not user:
            raise InvalidCredentialsException()

        # Check account status locks
        if user.status != UserStatus.ACTIVE:
            raise InactiveUserException()

        # Verify password hash match
        if not self.password_hasher.verify_password(dto.password, user.password_hash):
            raise InvalidCredentialsException()

        # Generate access token
        access_token_id = str(uuid.uuid4())
        access_token = self.jwt_manager.create_access_token(
            subject=str(user.id),
            jti=access_token_id,
            additional_claims={"role": user.role.value},
        )

        # Generate stateful rotated refresh token
        raw_refresh_token = TokenManager.generate_random_token()
        token_fingerprint = TokenManager.generate_token_fingerprint(raw_refresh_token)

        # Build refresh token model entry
        family_id = uuid.uuid4()
        expires_at = datetime.now(UTC) + timedelta(days=7)

        refresh_token_record = RefreshToken(
            user_id=user.id,
            family_id=family_id,
            token_hash=token_fingerprint,
            expires_at=expires_at,
            ip_address=client_metadata.ip_address,
            user_agent=client_metadata.user_agent,
            device_name=client_metadata.device_name,
        )

        await self.token_repo.create(refresh_token_record)
        await self.session.flush()

        return access_token, raw_refresh_token

    @transactional
    async def refresh_token(
        self, raw_refresh_token: str, client_metadata: ClientMetadata
    ) -> tuple[str, str]:
        """Exchange rotated refresh token for a brand new pair.

        Enforces Single-Use RTR family revocation lineage checks.

        Args:
            raw_refresh_token: The incoming refresh token string.
            client_metadata: Context parsed from request headers.

        Returns:
            A tuple of (new_access_token, new_refresh_token).
        """
        token_fingerprint = TokenManager.generate_token_fingerprint(raw_refresh_token)

        # Find matching token record
        token_record = await self.token_repo.get_by_token_hash(token_fingerprint)
        if not token_record:
            raise InvalidRefreshTokenException()

        # Breach Detection Check: If token is already marked revoked, someone else used it!
        # Revoke the entire family lineage immediately (potential session theft)
        if token_record.revoked:
            # Query all tokens in the same family family_id
            from sqlalchemy import select

            # Fetch all tokens of the family
            stmt = select(RefreshToken).where(RefreshToken.family_id == str(token_record.family_id))
            res = await self.session.execute(stmt)
            family_tokens = res.scalars().all()
            for tok in family_tokens:
                tok.revoked = True
                self.session.add(tok)
            await self.session.commit()
            raise TokenRevokedException(
                "This token session has been revoked due to reuse detection. All family keys invalidated."
            )

        # Check expiration date
        expires_at = (
            token_record.expires_at.replace(tzinfo=None)
            if token_record.expires_at.tzinfo
            else token_record.expires_at
        )
        now = datetime.now(UTC).replace(tzinfo=None)
        if expires_at < now:
            token_record.revoked = True
            self.session.add(token_record)
            await self.session.flush()
            raise TokenExpiredException()

        # Rotate: Invalidate current refresh token
        token_record.revoked = True
        self.session.add(token_record)

        # Generate new credentials
        user_id = token_record.user_id

        # Load associated user to read role for JWT claim builder
        user = await self.user_repo.get_by_id(user_id)
        if not user or user.status != UserStatus.ACTIVE:
            raise InactiveUserException()

        # Generate new JWT access token
        access_token_id = str(uuid.uuid4())
        access_token = self.jwt_manager.create_access_token(
            subject=str(user.id),
            jti=access_token_id,
            additional_claims={"role": user.role.value},
        )

        # Generate new rotated refresh token in the same family
        new_raw_refresh_token = TokenManager.generate_random_token()
        new_token_fingerprint = TokenManager.generate_token_fingerprint(new_raw_refresh_token)
        new_expires_at = datetime.now(UTC) + timedelta(days=7)

        new_refresh_record = RefreshToken(
            user_id=user_id,
            family_id=token_record.family_id,  # Preserve family_id lineage
            token_hash=new_token_fingerprint,
            expires_at=new_expires_at,
            ip_address=client_metadata.ip_address,
            user_agent=client_metadata.user_agent,
            device_name=client_metadata.device_name,
        )

        await self.token_repo.create(new_refresh_record)
        await self.session.flush()

        return access_token, new_raw_refresh_token

    @transactional
    async def logout(self, raw_refresh_token: str) -> None:
        """Revoke the current refresh token session invalidating it.

        Args:
            raw_refresh_token: The refresh token to revoke.
        """
        token_fingerprint = TokenManager.generate_token_fingerprint(raw_refresh_token)
        token_record = await self.token_repo.get_by_token_hash(token_fingerprint)
        if token_record:
            token_record.revoked = True
            self.session.add(token_record)
            await self.session.flush()
