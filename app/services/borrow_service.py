"""BorrowService module implementing checkout, return, renewal, and fine validation logic."""

import datetime
import json
import logging
import uuid
from typing import Any, Protocol

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BookAlreadyReturnedException,
    BookNotFoundException,
    BookUnavailableException,
    BorrowLimitExceededException,
    ConcurrentBorrowException,
    MemberInactiveException,
    MemberSuspendedException,
    OverdueMemberException,
    RenewalLimitExceededException,
    ReservationNotHeldException,
)
from app.domain.enums import BorrowStatus, MembershipStatus
from app.models.borrow_record import BorrowRecord
from app.models.member import Member
from app.repositories.book_repository import BookRepository
from app.repositories.borrow_repository import BorrowRecordRepository
from app.repositories.member_repository import MemberRepository
from app.services.base import BaseService

logger = logging.getLogger(__name__)


# ─── Fine Calculator Strategy Pattern ──────────────────────────────────────────


class FineCalculator(Protocol):
    """Strategy interface defining overdue fine calculations (OCP conformity)."""

    def calculate_fine(self, due_date: datetime.datetime, return_date: datetime.datetime) -> float:
        """Calculate dynamic fine based on overdue duration."""
        ...


class FlatDailyFineStrategy:
    """Calculates flat daily rate fines with a configurable maximum ceiling."""

    def __init__(self, daily_rate: float = 0.50, max_limit: float = 50.00) -> None:
        self.daily_rate = daily_rate
        self.max_limit = max_limit

    def calculate_fine(self, due_date: datetime.datetime, return_date: datetime.datetime) -> float:
        """Calculate fine: days overdue * daily_rate, rounded to 2 decimal places."""
        # Convert to offset-naive for comparison
        due_naive = due_date.replace(tzinfo=None) if due_date.tzinfo else due_date
        return_naive = return_date.replace(tzinfo=None) if return_date.tzinfo else return_date

        if return_naive <= due_naive:
            return 0.0

        overdue_delta = return_naive - due_naive
        # Count any partial day as a full day overdue
        days_overdue = overdue_delta.days
        if overdue_delta.seconds > 0:
            days_overdue += 1

        fine = days_overdue * self.daily_rate
        fine = min(fine, self.max_limit)
        return round(fine, 2)


# ─── Reservation Policy Interface ──────────────────────────────────────────────


class ReservationPolicy(Protocol):
    """Protocol for checking active reservations holds on books (Dependency Inversion)."""

    async def has_pending_reservations(self, member_id: uuid.UUID, book_id: uuid.UUID) -> bool:
        """Verify if a renewal or checkout is blocked due to active holds."""
        ...


class NoReservationPolicy:
    """Default reservation policy allowing all checkouts and renewals."""

    async def has_pending_reservations(self, member_id: uuid.UUID, book_id: uuid.UUID) -> bool:
        """Always allow operation by returning False (no blocks)."""
        return False


# ─── Borrow Service Implementation ─────────────────────────────────────────────


class BorrowService(BaseService):
    """Service managing borrow checkouts, idempotent returns, and renewals."""

    def __init__(
        self,
        session: AsyncSession,
        member_repo: MemberRepository,
        book_repo: BookRepository,
        borrow_repo: BorrowRecordRepository,
        fine_calculator: FineCalculator | None = None,
        reservation_policy: ReservationPolicy | None = None,
        max_borrow_limit: int = 5,
        borrow_days: int = 14,
        renewal_days: int = 14,
        reservation_service: Any = None,
    ) -> None:
        """Initialize service with dependencies."""
        super().__init__(session)
        self.member_repo = member_repo
        self.book_repo = book_repo
        self.borrow_repo = borrow_repo
        self.fine_calculator = fine_calculator or FlatDailyFineStrategy()
        self.reservation_policy = reservation_policy or NoReservationPolicy()
        self.max_borrow_limit = max_borrow_limit
        self.borrow_days = borrow_days
        self.renewal_days = renewal_days
        self.reservation_service = reservation_service

    def _log_event(self, event: str, level: str = "info", **kwargs: Any) -> None:
        """Helper to write structured JSON log entries."""
        log_payload = {"event": event, "service": "BorrowService", **kwargs}
        if level == "error":
            logger.error(json.dumps(log_payload))
        else:
            logger.info(json.dumps(log_payload))

    async def _validate_member_for_borrow(self, member: Member) -> None:
        """Validate member status, active overdue holds, and maximum borrow limit rules."""
        member_id = member.id
        if member.membership_status != MembershipStatus.ACTIVE:
            self._log_event(
                "borrow_rejected",
                reason="MEMBER_NOT_ACTIVE",
                member_id=str(member_id),
                status=member.membership_status.value,
            )
            if member.membership_status == MembershipStatus.SUSPENDED:
                raise MemberSuspendedException()
            raise MemberInactiveException()

        # Validate overdue loans block
        overdue_count = await self.borrow_repo.get_overdue_by_member_id_count(member_id)
        if overdue_count > 0:
            self._log_event("borrow_rejected", reason="OVERDUE_BOOKS", member_id=str(member_id))
            raise OverdueMemberException()

        # Validate maximum active borrow limits
        active_count = len(await self.borrow_repo.get_active_by_member_id(member_id))
        if active_count >= self.max_borrow_limit:
            self._log_event(
                "borrow_rejected",
                reason="BORROW_LIMIT_EXCEEDED",
                member_id=str(member_id),
                active_count=active_count,
            )
            raise BorrowLimitExceededException()

    async def borrow_book(self, member_id: uuid.UUID, book_id: uuid.UUID) -> BorrowRecord:
        """Check out a book, validating limits and acquiring pessimistic locks.

        Lock order: Lock Member row first, then lock Book row (prevents deadlocks).

        Args:
            member_id: The member checking out.
            book_id: The book to checkout.

        Returns:
            The created BorrowRecord.
        """
        self._log_event("borrow_created_start", member_id=str(member_id), book_id=str(book_id))

        try:
            # 1. Acquire write lock on Member row
            member = await self.member_repo.get_by_id_for_update(member_id)
            if not member:
                self._log_event(
                    "borrow_rejected", reason="MEMBER_NOT_FOUND", member_id=str(member_id)
                )
                raise ValueError("Member not found")

            # Run extracted member validations
            await self._validate_member_for_borrow(member)

            # 2. Acquire write lock on Book row
            book = await self.book_repo.get_by_id_for_update(book_id)
            if not book or book.is_deleted:
                self._log_event("borrow_rejected", reason="BOOK_NOT_FOUND", book_id=str(book_id))
                raise BookNotFoundException()

            # Acquire write lock on any active HOLD reservation for this book
            from sqlalchemy import select

            from app.domain.enums import ReservationStatus
            from app.models.reservation import Reservation

            res_stmt = (
                select(Reservation)
                .where(
                    Reservation.book_id == str(book_id),
                    Reservation.status == ReservationStatus.HOLD,
                )
                .with_for_update()
            )
            res_result = await self.session.execute(res_stmt)
            active_hold = res_result.scalar_one_or_none()

            reservation_completed = False
            if active_hold:
                if str(active_hold.member_id) == str(member_id):
                    # Permitted: This member holds the reservation
                    active_hold.status = ReservationStatus.COMPLETED
                    active_hold.expires_at = None
                    await self.session.flush()
                    reservation_completed = True
                else:
                    # Blocked: Held for another user
                    self._log_event(
                        "borrow_rejected",
                        reason="RESERVATION_HELD_FOR_OTHER",
                        book_id=str(book_id),
                        member_id=str(member_id),
                    )
                    raise ReservationNotHeldException()

            # Validate book copies availability if not checking out a held reservation
            if not reservation_completed and book.available_copies <= 0:
                self._log_event("borrow_rejected", reason="BOOK_UNAVAILABLE", book_id=str(book_id))
                raise BookUnavailableException()

            # Decrement inventory and save (only if not checking out a held reservation)
            if not reservation_completed:
                book.available_copies -= 1
                await self.book_repo.update(book, update_data={})

            # Create borrow checkout entry
            now = datetime.datetime.now(datetime.UTC)
            due_date = now + datetime.timedelta(days=self.borrow_days)

            record = BorrowRecord(
                id=uuid.uuid4(),
                member_id=member_id,
                book_id=book_id,
                borrow_date=now,
                due_date=due_date,
                status=BorrowStatus.BORROWED,
                renewal_count=0,
            )
            await self.borrow_repo.create(record)
            await self.session.flush()

            self._log_event(
                "borrow_created",
                borrow_id=str(record.id),
                member_id=str(member_id),
                book_id=str(book_id),
            )
            return record

        except OperationalError as e:
            self._log_event("borrow_concurrency_conflict", level="error", error=str(e))
            raise ConcurrentBorrowException() from e

    async def return_book(self, borrow_record_id: uuid.UUID) -> BorrowRecord:
        """Return a borrowed book, calculating fines and restoring copy counts.

        This execution is idempotent: retries return the current state safely.

        Args:
            borrow_record_id: ID of the borrow checkout.

        Returns:
            The updated BorrowRecord.
        """
        self._log_event("borrow_returned_start", borrow_id=str(borrow_record_id))

        try:
            record = await self.borrow_repo.get_by_id(borrow_record_id)
            if not record:
                raise ValueError("Borrow record not found")

            # Idempotency check: if already returned, skip inventory modifications
            if record.status == BorrowStatus.RETURNED:
                self._log_event("borrow_returned_idempotent", borrow_id=str(borrow_record_id))
                return record

            # Calculate overdue fines if returned late
            now = datetime.datetime.now(datetime.UTC)
            fine_incurred = self.fine_calculator.calculate_fine(record.due_date, now)

            # Update borrow record properties
            record.return_date = now
            record.status = BorrowStatus.RETURNED
            record.fine_amount = fine_incurred  # type: ignore[attr-defined]

            await self.borrow_repo.update(record, update_data={})
            await self.session.flush()

            # Delegate promotion flow to ReservationService if wired
            if self.reservation_service:
                await self.reservation_service.promote_next_reservation(record.book_id)
            else:
                # Lock matching Book row to restore inventory copies
                book = await self.book_repo.get_by_id_for_update(record.book_id)
                if book:
                    book.available_copies += 1
                    await self.book_repo.update(book, update_data={})
                    await self.session.flush()

            self._log_event(
                "borrow_returned",
                borrow_id=str(borrow_record_id),
                fine_amount=fine_incurred,
                status=record.status.value,
            )
            return record

        except OperationalError as e:
            self._log_event("borrow_return_concurrency_conflict", level="error", error=str(e))
            raise ConcurrentBorrowException() from e

    async def renew_book(self, borrow_record_id: uuid.UUID) -> BorrowRecord:
        """Renew the borrow checkout, extending due dates if policies permit.

        Args:
            borrow_record_id: ID of the checkout to renew.

        Returns:
            The updated BorrowRecord.

        Raises:
            BookAlreadyReturnedException: If checkout is already returned.
            RenewalLimitExceededException: If maximum renewals (2) are reached.
            OverdueMemberException: If trying to renew an overdue checkout.
        """
        self._log_event("borrow_renewed_start", borrow_id=str(borrow_record_id))

        try:
            record = await self.borrow_repo.get_by_id(borrow_record_id)
            if not record:
                raise ValueError("Borrow record not found")

            if record.status == BorrowStatus.RETURNED:
                self._log_event(
                    "renew_rejected", reason="ALREADY_RETURNED", borrow_id=str(borrow_record_id)
                )
                raise BookAlreadyReturnedException()

            if record.renewal_count >= 2:
                self._log_event(
                    "renew_rejected",
                    reason="RENEWAL_LIMIT_EXCEEDED",
                    borrow_id=str(borrow_record_id),
                )
                raise RenewalLimitExceededException()

            # Verify the book has no active reservations holds blocking renewals
            is_blocked = await self.reservation_policy.has_pending_reservations(
                record.member_id, record.book_id
            )
            if is_blocked:
                self._log_event(
                    "renew_rejected", reason="PENDING_RESERVATIONS", borrow_id=str(borrow_record_id)
                )
                raise BookUnavailableException(
                    "Renewal blocked due to pending reservation hold queue"
                )

            now = datetime.datetime.now(datetime.UTC)
            due_naive = (
                record.due_date.replace(tzinfo=None) if record.due_date.tzinfo else record.due_date
            )
            now_naive = now.replace(tzinfo=None)

            # Block renewals if checkout is already overdue
            if now_naive > due_naive:
                self._log_event(
                    "renew_rejected", reason="BOOK_OVERDUE", borrow_id=str(borrow_record_id)
                )
                raise OverdueMemberException()

            # Extend due date and increment renewal count
            record.due_date = record.due_date + datetime.timedelta(days=self.renewal_days)
            record.renewal_count += 1
            record.status = BorrowStatus.RENEWED

            await self.borrow_repo.update(record, update_data={})
            await self.session.flush()

            self._log_event(
                "borrow_renewed",
                borrow_id=str(borrow_record_id),
                new_due_date=str(record.due_date),
                renewal_count=record.renewal_count,
            )
            return record

        except OperationalError as e:
            self._log_event("borrow_renewal_concurrency_conflict", level="error", error=str(e))
            raise ConcurrentBorrowException() from e

    async def get_borrow_history(
        self, member_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> list[BorrowRecord]:
        """Fetch historical checkouts associated with a member.

        Args:
            member_id: The member's ID.
            page: Offset page.
            page_size: Offset size.

        Returns:
            A list of BorrowRecords.
        """
        skip = (page - 1) * page_size
        return await self.borrow_repo.get_history_by_member_id(
            member_id, skip=skip, limit=page_size
        )
