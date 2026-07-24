import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.enums import BorrowStatus
from app.models.borrow_record import BorrowRecord
from app.repositories.base import BaseRepository
from app.repositories.interfaces.borrow_repository import (
    BorrowRecordRepositoryInterface,
)


class BorrowRecordRepository(BaseRepository[BorrowRecord], BorrowRecordRepositoryInterface):
    """BorrowRecordRepository implementation matching BorrowRecordRepositoryInterface."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(BorrowRecord, session)

    async def get_active_by_member_id(self, member_id: uuid.UUID) -> list[BorrowRecord]:
        """Fetch all active loan records currently associated with a member."""
        result = await self.session.execute(
            select(BorrowRecord).where(
                BorrowRecord.member_id == str(member_id),
                BorrowRecord.status.in_([BorrowStatus.BORROWED, BorrowStatus.RENEWED]),
            )
        )
        return list(result.scalars().all())

    async def get_all_by_status(
        self, status: BorrowStatus, *, skip: int = 0, limit: int = 20
    ) -> list[BorrowRecord]:
        """Fetch all borrowing records matching specific status state."""
        result = await self.session.execute(
            select(BorrowRecord).where(BorrowRecord.status == status).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_overdue_by_member_id_count(self, member_id: uuid.UUID) -> int:
        """Count overdue borrow records for a specific member."""
        import datetime

        from sqlalchemy import func

        now = datetime.datetime.now(datetime.UTC)
        result = await self.session.execute(
            select(func.count(BorrowRecord.id)).where(
                BorrowRecord.member_id == str(member_id),
                BorrowRecord.status.in_([BorrowStatus.BORROWED, BorrowStatus.RENEWED]),
                BorrowRecord.due_date < now,
            )
        )
        return result.scalar() or 0

    async def get_history_by_member_id(
        self, member_id: uuid.UUID, *, skip: int = 0, limit: int = 20
    ) -> list[BorrowRecord]:
        """Retrieve historical borrow records for a member, descending from newest borrow."""
        result = await self.session.execute(
            select(BorrowRecord)
            .where(BorrowRecord.member_id == str(member_id))
            .options(selectinload(BorrowRecord.book))
            .order_by(BorrowRecord.borrow_date.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
