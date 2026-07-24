import datetime
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AlreadyReservedException,
    BookAlreadyBorrowedException,
    ReservationLimitExceededException,
)
from app.domain.enums import BorrowStatus, MembershipStatus, ReservationStatus, UserRole, UserStatus
from app.models.book import Book
from app.models.borrow_record import BorrowRecord
from app.models.member import Member
from app.models.reservation import Reservation
from app.models.user import User
from app.repositories.book_repository import BookRepository
from app.repositories.borrow_repository import BorrowRecordRepository
from app.repositories.member_repository import MemberRepository
from app.repositories.reservation_repository import ReservationRepository
from app.services.borrow_service import BorrowService
from app.services.reservation_service import ReservationService


@pytest.fixture
def reservation_service(db_session: AsyncSession) -> ReservationService:
    reservation_repo = ReservationRepository(db_session)
    book_repo = BookRepository(db_session)
    member_repo = MemberRepository(db_session)
    borrow_repo = BorrowRecordRepository(db_session)
    return ReservationService(
        session=db_session,
        reservation_repo=reservation_repo,
        book_repo=book_repo,
        member_repo=member_repo,
        borrow_repo=borrow_repo,
    )


@pytest.fixture
def borrow_service(
    db_session: AsyncSession, reservation_service: ReservationService
) -> BorrowService:
    member_repo = MemberRepository(db_session)
    book_repo = BookRepository(db_session)
    borrow_repo = BorrowRecordRepository(db_session)
    return BorrowService(
        session=db_session,
        member_repo=member_repo,
        book_repo=book_repo,
        borrow_repo=borrow_repo,
        reservation_service=reservation_service,
    )


async def _create_member(db_session: AsyncSession, email: str, num: str) -> Member:
    user = User(
        name="Test Member",
        email=email,
        password_hash="Hash123!",
        role=UserRole.MEMBER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.flush()

    member = Member(
        user_id=user.id,
        membership_number=num,
        joined_date=datetime.date.today(),
        membership_status=MembershipStatus.ACTIVE,
    )
    db_session.add(member)
    await db_session.flush()
    return member


@pytest.mark.asyncio
async def test_reserve_in_stock_fails(
    reservation_service: ReservationService, db_session: AsyncSession
) -> None:
    member = await _create_member(db_session, "member1@example.com", "LMP-RES-11")
    # Book with 2 available copies
    book = Book(
        title="Book In Stock",
        author="Author",
        isbn="9780131103300",
        total_copies=2,
        available_copies=2,
    )
    db_session.add(book)
    await db_session.flush()

    with pytest.raises(ValueError, match="currently available in stock"):
        await reservation_service.place_reservation(member.id, book.id)


@pytest.mark.asyncio
async def test_reserve_out_of_stock_succeeds(
    reservation_service: ReservationService, db_session: AsyncSession
) -> None:
    member = await _create_member(db_session, "member2@example.com", "LMP-RES-22")
    # Book with 0 copies
    book = Book(
        title="Book Out of Stock",
        author="Author",
        isbn="9780131103301",
        total_copies=0,
        available_copies=0,
    )
    db_session.add(book)
    await db_session.flush()

    res = await reservation_service.place_reservation(member.id, book.id)
    assert res.id is not None
    assert res.status == ReservationStatus.PENDING

    # Compute dynamic position
    pos = await reservation_service.reservation_repo.compute_queue_position(
        book.id, res.reserved_at
    )
    assert pos == 1


@pytest.mark.asyncio
async def test_active_reservations_limits(
    reservation_service: ReservationService, db_session: AsyncSession
) -> None:
    member = await _create_member(db_session, "member3@example.com", "LMP-RES-33")

    # Reserve 3 different books (max limit)
    for i in range(3):
        book = Book(
            title=f"Reserved Book {i}",
            author="Author",
            isbn=f"978013110331{i}",
            total_copies=0,
            available_copies=0,
        )
        db_session.add(book)
        await db_session.flush()
        await reservation_service.place_reservation(member.id, book.id)

    # 4th reservation should fail
    extra_book = Book(
        title="Extra Book",
        author="Author",
        isbn="9780131103320",
        total_copies=0,
        available_copies=0,
    )
    db_session.add(extra_book)
    await db_session.flush()

    with pytest.raises(ReservationLimitExceededException):
        await reservation_service.place_reservation(member.id, extra_book.id)


@pytest.mark.asyncio
async def test_duplicate_reservation_fails(
    reservation_service: ReservationService, db_session: AsyncSession
) -> None:
    member = await _create_member(db_session, "member4@example.com", "LMP-RES-44")
    book = Book(
        title="Reserved Book X",
        author="Author",
        isbn="9780131103321",
        total_copies=0,
        available_copies=0,
    )
    db_session.add(book)
    await db_session.flush()

    # Place first reservation
    await reservation_service.place_reservation(member.id, book.id)

    # Duplicate should fail
    with pytest.raises(AlreadyReservedException):
        await reservation_service.place_reservation(member.id, book.id)


@pytest.mark.asyncio
async def test_reserve_already_borrowed_fails(
    reservation_service: ReservationService, db_session: AsyncSession
) -> None:
    member = await _create_member(db_session, "member5@example.com", "LMP-RES-55")
    book = Book(
        title="Reserved Book Y",
        author="Author",
        isbn="9780131103322",
        total_copies=1,
        available_copies=0,
    )
    db_session.add(book)
    await db_session.flush()

    # Create active borrow record directly in DB
    borrow_record = BorrowRecord(
        id=uuid.uuid4(),
        member_id=member.id,
        book_id=book.id,
        borrow_date=datetime.datetime.now(datetime.UTC),
        due_date=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=14),
        status=BorrowStatus.BORROWED,
    )
    db_session.add(borrow_record)
    await db_session.flush()

    with pytest.raises(BookAlreadyBorrowedException):
        await reservation_service.place_reservation(member.id, book.id)


@pytest.mark.asyncio
async def test_return_promotes_fifo_reservation(
    borrow_service: BorrowService,
    reservation_service: ReservationService,
    db_session: AsyncSession,
) -> None:
    m1 = await _create_member(db_session, "m1@example.com", "LMP-FIFO-1")
    m2 = await _create_member(db_session, "m2@example.com", "LMP-FIFO-2")

    book = Book(
        title="FIFO Testing Book",
        author="Author",
        isbn="9780131103323",
        total_copies=1,
        available_copies=0,  # Currently checked out by m1
    )
    db_session.add(book)
    await db_session.flush()

    # Active checkout record for m1
    rec = BorrowRecord(
        id=uuid.uuid4(),
        member_id=m1.id,
        book_id=book.id,
        borrow_date=datetime.datetime.now(datetime.UTC),
        due_date=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=14),
        status=BorrowStatus.BORROWED,
        renewal_count=0,
    )
    db_session.add(rec)

    # Place reservation for m2
    res_m2 = await reservation_service.place_reservation(m2.id, book.id)
    assert res_m2.status == ReservationStatus.PENDING

    # Return book
    returned = await borrow_service.return_book(rec.id)
    assert returned.status == BorrowStatus.RETURNED

    # Check if reservation promoted to HOLD
    await db_session.refresh(res_m2)
    assert res_m2.status == ReservationStatus.HOLD
    assert res_m2.expires_at is not None

    # Available copies should remain 0 since book is held for m2
    await db_session.refresh(book)
    assert book.available_copies == 0


@pytest.mark.asyncio
async def test_soft_cancel_promotes_next_pending(
    reservation_service: ReservationService, db_session: AsyncSession
) -> None:
    m1 = await _create_member(db_session, "c1@example.com", "LMP-CANC-1")
    m2 = await _create_member(db_session, "c2@example.com", "LMP-CANC-2")

    book = Book(
        title="FIFO Cancel Book",
        author="Author",
        isbn="9780131103324",
        total_copies=1,
        available_copies=0,
    )
    db_session.add(book)
    await db_session.flush()

    # m1 has a HOLD reservation
    res_m1 = Reservation(
        id=uuid.uuid4(),
        member_id=m1.id,
        book_id=book.id,
        status=ReservationStatus.HOLD,
        reserved_at=datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1),
        expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=47),
    )
    db_session.add(res_m1)

    # m2 has a PENDING reservation
    res_m2 = Reservation(
        id=uuid.uuid4(),
        member_id=m2.id,
        book_id=book.id,
        status=ReservationStatus.PENDING,
        reserved_at=datetime.datetime.now(datetime.UTC),
    )
    db_session.add(res_m2)
    await db_session.flush()

    # Cancel m1 hold
    cancelled = await reservation_service.cancel_reservation(res_m1.id, m1.id)
    assert cancelled.status == ReservationStatus.CANCELLED

    # Check if m2 is immediately promoted to HOLD
    await db_session.refresh(res_m2)
    assert res_m2.status == ReservationStatus.HOLD
    assert res_m2.expires_at is not None


@pytest.mark.asyncio
async def test_process_expired_holds(
    reservation_service: ReservationService, db_session: AsyncSession
) -> None:
    m1 = await _create_member(db_session, "e1@example.com", "LMP-EXP-1")
    m2 = await _create_member(db_session, "e2@example.com", "LMP-EXP-2")

    book = Book(
        title="FIFO Expire Book",
        author="Author",
        isbn="9780131103325",
        total_copies=1,
        available_copies=0,
    )
    db_session.add(book)
    await db_session.flush()

    # m1 has expired hold
    res_m1 = Reservation(
        id=uuid.uuid4(),
        member_id=m1.id,
        book_id=book.id,
        status=ReservationStatus.HOLD,
        reserved_at=datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=50),
        expires_at=datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=2),  # Expired
    )
    db_session.add(res_m1)

    # m2 is pending
    res_m2 = Reservation(
        id=uuid.uuid4(),
        member_id=m2.id,
        book_id=book.id,
        status=ReservationStatus.PENDING,
        reserved_at=datetime.datetime.now(datetime.UTC),
    )
    db_session.add(res_m2)
    await db_session.flush()

    # Run expiration sweep
    expired_count = await reservation_service.process_expired_holds()
    assert expired_count == 1

    # Verify m1 transitioned to EXPIRED
    await db_session.refresh(res_m1)
    assert res_m1.status == ReservationStatus.EXPIRED

    # Verify m2 promoted to HOLD
    await db_session.refresh(res_m2)
    assert res_m2.status == ReservationStatus.HOLD
