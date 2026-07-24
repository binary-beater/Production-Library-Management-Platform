import datetime
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.enums import ReservationStatus
from app.models.reservation import Reservation
from app.repositories.base import BaseRepository
from app.repositories.interfaces.reservation_repository import (
    ReservationRepositoryInterface,
)


class ReservationRepository(BaseRepository[Reservation], ReservationRepositoryInterface):
    """ReservationRepository implementation conforming to ReservationRepositoryInterface."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Reservation, session)

    async def get_by_id_for_update(self, id: uuid.UUID) -> Reservation | None:
        """Fetch reservation by ID with pessimistic write lock (FOR UPDATE)."""
        result = await self.session.execute(
            select(Reservation).where(Reservation.id == str(id)).with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_active_by_member_id_count(self, member_id: uuid.UUID) -> int:
        """Count active reservations (PENDING/HOLD) for a member."""
        result = await self.session.execute(
            select(func.count(Reservation.id)).where(
                Reservation.member_id == str(member_id),
                Reservation.status.in_([ReservationStatus.PENDING, ReservationStatus.HOLD]),
            )
        )
        return result.scalar() or 0

    async def get_active_by_member_and_book(
        self, member_id: uuid.UUID, book_id: uuid.UUID
    ) -> Reservation | None:
        """Fetch active reservation (PENDING/HOLD) for member and book."""
        result = await self.session.execute(
            select(Reservation).where(
                Reservation.member_id == str(member_id),
                Reservation.book_id == str(book_id),
                Reservation.status.in_([ReservationStatus.PENDING, ReservationStatus.HOLD]),
            )
        )
        return result.scalar_one_or_none()

    async def get_fifo_pending_by_book_id(self, book_id: uuid.UUID) -> Reservation | None:
        """Fetch the oldest PENDING reservation for a book."""
        result = await self.session.execute(
            select(Reservation)
            .where(
                Reservation.book_id == str(book_id),
                Reservation.status == ReservationStatus.PENDING,
            )
            .order_by(Reservation.reserved_at.asc())
            .limit(1)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def compute_queue_position(
        self, book_id: uuid.UUID, reserved_at: datetime.datetime
    ) -> int:
        """Compute the dynamic FIFO position of a PENDING reservation.

        Returns 1 for the oldest pending, 2 for the second, etc.
        """
        result = await self.session.execute(
            select(func.count(Reservation.id)).where(
                Reservation.book_id == str(book_id),
                Reservation.status == ReservationStatus.PENDING,
                Reservation.reserved_at < reserved_at,
            )
        )
        count_ahead = result.scalar() or 0
        return count_ahead + 1

    async def get_expired_holds(self, now: datetime.datetime) -> list[Reservation]:
        """Fetch all HOLD reservations where expires_at is before now."""
        result = await self.session.execute(
            select(Reservation)
            .where(
                Reservation.status == ReservationStatus.HOLD,
                Reservation.expires_at < now,
            )
            .with_for_update()
        )
        return list(result.scalars().all())

    async def get_active_reservations_by_member(self, member_id: uuid.UUID) -> list[Reservation]:
        """Fetch active reservations (PENDING/HOLD) for a member with eager book details."""
        result = await self.session.execute(
            select(Reservation)
            .where(
                Reservation.member_id == str(member_id),
                Reservation.status.in_([ReservationStatus.PENDING, ReservationStatus.HOLD]),
            )
            .options(selectinload(Reservation.book))
            .order_by(Reservation.reserved_at.asc())
        )
        return list(result.scalars().all())
