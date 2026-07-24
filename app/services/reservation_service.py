"""ReservationService module implementing FIFO queues, soft cancellations, and promotion loops."""

import datetime
import json
import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AlreadyReservedException,
    BookAlreadyBorrowedException,
    BookNotFoundException,
    MemberInactiveException,
    MemberSuspendedException,
    ReservationLimitExceededException,
    ReservationNotFoundException,
)
from app.db.transaction import transactional
from app.domain.enums import BorrowStatus, MembershipStatus, ReservationStatus
from app.models.reservation import Reservation
from app.repositories.book_repository import BookRepository
from app.repositories.borrow_repository import BorrowRecordRepository
from app.repositories.member_repository import MemberRepository
from app.repositories.reservation_repository import ReservationRepository
from app.services.base import BaseService

logger = logging.getLogger(__name__)

MAX_ACTIVE_RESERVATIONS = 3


class ReservationService(BaseService):
    """Business service coordinating all books reservation queues and holds promotion tasks."""

    def __init__(
        self,
        session: AsyncSession,
        reservation_repo: ReservationRepository,
        book_repo: BookRepository,
        member_repo: MemberRepository,
        borrow_repo: BorrowRecordRepository,
    ) -> None:
        super().__init__(session)
        self.reservation_repo = reservation_repo
        self.book_repo = book_repo
        self.member_repo = member_repo
        self.borrow_repo = borrow_repo

    def _log_event(self, event: str, level: str = "info", **kwargs: Any) -> None:
        """Log events as structured JSON strings for observability ingestion."""
        log_data = {"event": event, "timestamp": datetime.datetime.now(datetime.UTC).isoformat()}
        log_data.update(kwargs)
        msg = json.dumps(log_data)
        if level == "error":
            logger.error(msg)
        elif level == "warning":
            logger.warning(msg)
        else:
            logger.info(msg)

    @transactional
    async def place_reservation(self, member_id: uuid.UUID, book_id: uuid.UUID) -> Reservation:
        """Create a new reservation for an out-of-stock book under transaction scope."""
        self._log_event(
            "reservation_placement_start", member_id=str(member_id), book_id=str(book_id)
        )

        # Concurrency order: 1. Book -> 2. Reservation -> 3. Member
        book = await self.book_repo.get_by_id_for_update(book_id)
        if not book or book.is_deleted:
            raise BookNotFoundException()

        if book.available_copies > 0:
            raise ValueError("Cannot reserve a book that is currently available in stock")

        # Check active limits for the member
        active_count = await self.reservation_repo.get_active_by_member_id_count(member_id)
        if active_count >= MAX_ACTIVE_RESERVATIONS:
            raise ReservationLimitExceededException()

        # Uniqueness check: at most one active reservation per member for this book
        existing_active = await self.reservation_repo.get_active_by_member_and_book(
            member_id, book_id
        )
        if existing_active:
            raise AlreadyReservedException()

        # Member status checks
        member = await self.member_repo.get_by_id_for_update(member_id)
        if not member or member.is_deleted:
            raise MemberInactiveException()
        if member.membership_status == MembershipStatus.INACTIVE:
            raise MemberInactiveException()
        if member.membership_status == MembershipStatus.SUSPENDED:
            raise MemberSuspendedException()

        # Verify member doesn't already have this book borrowed (active checkouts)
        active_borrows = await self.borrow_repo.get_history_by_member_id(member_id, limit=20)
        for br in active_borrows:
            if str(br.book_id) == str(book_id) and br.status in [
                BorrowStatus.BORROWED,
                BorrowStatus.RENEWED,
                BorrowStatus.OVERDUE,
            ]:
                raise BookAlreadyBorrowedException()

        # Place reservation
        reservation = Reservation(
            id=uuid.uuid4(),
            member_id=member_id,
            book_id=book_id,
            reserved_at=datetime.datetime.now(datetime.UTC),
            status=ReservationStatus.PENDING,
        )
        await self.reservation_repo.create(reservation)
        await self.session.flush()
        await self.session.refresh(reservation)

        self._log_event(
            "reservation_created",
            reservation_id=str(reservation.id),
            member_id=str(member_id),
            book_id=str(book_id),
        )
        return reservation

    @transactional
    async def cancel_reservation(
        self, reservation_id: uuid.UUID, member_id: uuid.UUID
    ) -> Reservation:
        """Soft-cancel a pending or hold reservation, immediately promoting the next user in line."""
        self._log_event(
            "reservation_cancellation_start",
            reservation_id=str(reservation_id),
            member_id=str(member_id),
        )

        # Concurrency order: 1. Book -> 2. Reservation -> 3. Member
        res = await self.reservation_repo.get_by_id_for_update(reservation_id)
        if not res or str(res.member_id) != str(member_id):
            raise ReservationNotFoundException()

        if res.status not in [ReservationStatus.PENDING, ReservationStatus.HOLD]:
            raise ValueError("Can only cancel pending or active hold reservations")

        was_hold = res.status == ReservationStatus.HOLD
        res.status = ReservationStatus.CANCELLED
        res.expires_at = None
        await self.reservation_repo.update(res, update_data={})
        await self.session.flush()

        self._log_event(
            "reservation_cancelled",
            reservation_id=str(res.id),
            member_id=str(member_id),
            book_id=str(res.book_id),
        )

        # If we cancelled a HOLD reservation, promote next waiting member immediately
        if was_hold:
            await self.promote_next_reservation(res.book_id)

        await self.session.refresh(res)
        return res

    @transactional
    async def promote_next_reservation(self, book_id: uuid.UUID) -> None:
        """Search and promote the oldest PENDING reservation for a book to HOLD state.

        Assumes we already hold the transaction locks.
        """
        # oldest PENDING reservation
        next_res = await self.reservation_repo.get_fifo_pending_by_book_id(book_id)
        if next_res:
            next_res.status = ReservationStatus.HOLD
            now = datetime.datetime.now(datetime.UTC)
            next_res.expires_at = now + datetime.timedelta(hours=settings.HOLD_DURATION_HOURS)
            await self.reservation_repo.update(next_res, update_data={})
            await self.session.flush()

            # Dynamic position is 1 since they are now promoted
            self._log_event(
                "reservation_promoted",
                reservation_id=str(next_res.id),
                member_id=str(next_res.member_id),
                book_id=str(book_id),
                queue_position=1,
            )
        else:
            # If no reservations, restore book inventory copies
            book = await self.book_repo.get_by_id_for_update(book_id)
            if book:
                book.available_copies += 1
                await self.book_repo.update(book, update_data={})
                await self.session.flush()

    @transactional
    async def process_expired_holds(self) -> int:
        """Sweep all expired HOLD reservations and promote next pending users.

        Idempotent background job.
        """
        now = datetime.datetime.now(datetime.UTC)
        self._log_event("reservation_expiration_sweep_start", now=now.isoformat())

        expired_count = 0
        expired_holds = await self.reservation_repo.get_expired_holds(now)
        for res in expired_holds:
            res.status = ReservationStatus.EXPIRED
            res.expires_at = None
            await self.reservation_repo.update(res, update_data={})
            await self.session.flush()

            self._log_event(
                "reservation_expired",
                reservation_id=str(res.id),
                book_id=str(res.book_id),
                member_id=str(res.member_id),
            )
            expired_count += 1

            # Promote next waiting member for this book immediately
            await self.promote_next_reservation(res.book_id)

        self._log_event("reservation_expiration_sweep_complete", expired_count=expired_count)
        return expired_count

    async def get_active_reservations(self, member_id: uuid.UUID) -> list[dict[str, Any]]:
        """Get active reservations for a member, computing dynamic positions on the fly."""
        active_list = await self.reservation_repo.get_active_reservations_by_member(member_id)
        results = []
        for r in active_list:
            pos = None
            if r.status == ReservationStatus.PENDING:
                pos = await self.reservation_repo.compute_queue_position(r.book_id, r.reserved_at)

            results.append(
                {
                    "id": r.id,
                    "member_id": r.member_id,
                    "book_id": r.book_id,
                    "reserved_at": r.reserved_at,
                    "expires_at": r.expires_at,
                    "status": r.status,
                    "queue_position": pos,
                    "book": r.book,
                }
            )
        return results
