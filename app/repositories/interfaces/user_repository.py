from typing import Protocol

from app.models.user import User
from app.repositories.interfaces.base import BaseRepositoryInterface


class UserRepositoryInterface(BaseRepositoryInterface[User], Protocol):
    """Protocol defining user-specific database queries."""

    async def get_by_email(self, email: str) -> User | None: ...
