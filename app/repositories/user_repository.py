from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository
from app.repositories.interfaces.user_repository import UserRepositoryInterface


class UserRepository(BaseRepository[User], UserRepositoryInterface):
    """UserRepository implementation matching UserRepositoryInterface."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        """Lookup user record by unique email address."""
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
