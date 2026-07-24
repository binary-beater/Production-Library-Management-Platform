import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.member import Member
from app.repositories.base import BaseRepository
from app.repositories.interfaces.member_repository import (
    MemberRepositoryInterface,
)


class MemberRepository(BaseRepository[Member], MemberRepositoryInterface):
    """MemberRepository implementation matching MemberRepositoryInterface."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Member, session)

    async def get_by_id(self, id: uuid.UUID) -> Member | None:
        """Fetch a single member by ID, enforcing soft delete checks."""
        result = await self.session.execute(
            select(Member).where(Member.id == str(id), Member.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def get_all(self, *, skip: int = 0, limit: int = 20) -> list[Member]:
        """Fetch active members list, excluding soft deleted ones."""
        result = await self.session.execute(
            select(Member).where(Member.is_deleted == False).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_membership_number(self, membership_number: str) -> Member | None:
        """Fetch member profile by code number."""
        result = await self.session.execute(
            select(Member).where(
                Member.membership_number == membership_number,
                Member.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: uuid.UUID) -> Member | None:
        """Fetch member profile associated with user account identifier."""
        result = await self.session.execute(
            select(Member).where(Member.user_id == str(user_id), Member.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, id: uuid.UUID) -> Member | None:
        """Fetch a single member by ID, acquiring a write lock (FOR UPDATE)."""
        result = await self.session.execute(
            select(Member).where(Member.id == str(id), Member.is_deleted == False).with_for_update()
        )
        return result.scalar_one_or_none()

    async def delete(self, id: uuid.UUID) -> bool:
        """Enforce soft delete action instead of hard row purge."""
        member = await self.get_by_id(id)
        if not member:
            return False
        member.is_deleted = True
        import datetime

        member.deleted_at = datetime.datetime.now(datetime.UTC)
        self.session.add(member)
        return True
