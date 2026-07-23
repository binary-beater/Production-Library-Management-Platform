import uuid
from typing import Protocol

from app.models.member import Member
from app.repositories.interfaces.base import BaseRepositoryInterface


class MemberRepositoryInterface(BaseRepositoryInterface[Member], Protocol):
    """Protocol defining member-specific database queries."""

    async def get_by_membership_number(self, membership_number: str) -> Member | None: ...

    async def get_by_user_id(self, user_id: uuid.UUID) -> Member | None: ...
