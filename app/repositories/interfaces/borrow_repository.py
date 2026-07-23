import uuid
from typing import Protocol

from app.domain.enums import BorrowStatus
from app.models.borrow_record import BorrowRecord
from app.repositories.interfaces.base import BaseRepositoryInterface


class BorrowRecordRepositoryInterface(BaseRepositoryInterface[BorrowRecord], Protocol):
    """Protocol defining borrow record database queries."""

    async def get_active_by_member_id(self, member_id: uuid.UUID) -> list[BorrowRecord]: ...

    async def get_all_by_status(
        self, status: BorrowStatus, *, skip: int = 0, limit: int = 20
    ) -> list[BorrowRecord]: ...
