import datetime
import uuid
from typing import Protocol

from app.models.reservation import Reservation
from app.repositories.interfaces.base import BaseRepositoryInterface


class ReservationRepositoryInterface(BaseRepositoryInterface[Reservation], Protocol):
    """Protocol interface defining data access layers for the Reservation domain."""

    async def get_by_id_for_update(self, id: uuid.UUID) -> Reservation | None:
        """Fetch reservation by ID with pessimistic write lock (FOR UPDATE)."""
        ...

    async def get_active_by_member_id_count(self, member_id: uuid.UUID) -> int:
        """Count active reservations (PENDING/HOLD) for a member."""
        ...

    async def get_active_by_member_and_book(
        self, member_id: uuid.UUID, book_id: uuid.UUID
    ) -> Reservation | None:
        """Fetch active reservation (PENDING/HOLD) for member and book."""
        ...

    async def get_fifo_pending_by_book_id(self, book_id: uuid.UUID) -> Reservation | None:
        """Fetch the oldest PENDING reservation for a book."""
        ...

    async def compute_queue_position(
        self, book_id: uuid.UUID, reserved_at: datetime.datetime
    ) -> int:
        """Compute the dynamic FIFO position of a PENDING reservation."""
        ...

    async def get_expired_holds(self, now: datetime.datetime) -> list[Reservation]:
        """Fetch all HOLD reservations where expires_at is before now."""
        ...

    async def get_active_reservations_by_member(self, member_id: uuid.UUID) -> list[Reservation]:
        """Fetch active reservations (PENDING/HOLD) for a member."""
        ...
