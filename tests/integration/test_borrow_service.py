import datetime
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BookAlreadyReturnedException,
    BookUnavailableException,
    BorrowLimitExceededException,
    MemberSuspendedException,
    OverdueMemberException,
    RenewalLimitExceededException,
)
from app.domain.enums import BorrowStatus, MembershipStatus, UserRole, UserStatus
from app.models.book import Book
from app.models.borrow_record import BorrowRecord
from app.models.member import Member
from app.models.user import User
from app.repositories.book_repository import BookRepository
from app.repositories.borrow_repository import BorrowRecordRepository
from app.repositories.member_repository import MemberRepository
from app.services.borrow_service import BorrowService


@pytest.fixture
def borrow_service(db_session: AsyncSession) -> BorrowService:
    member_repo = MemberRepository(db_session)
    book_repo = BookRepository(db_session)
    borrow_repo = BorrowRecordRepository(db_session)
    return BorrowService(
        session=db_session,
        member_repo=member_repo,
        book_repo=book_repo,
        borrow_repo=borrow_repo,
    )


@pytest.mark.asyncio
async def test_borrow_book_succeeds(
    borrow_service: BorrowService, db_session: AsyncSession
) -> None:
    # 1. Create active member
    user = User(
        name="Member A",
        email="member_a@example.com",
        password_hash="Hash123!",
        role=UserRole.MEMBER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.flush()

    member = Member(
        user_id=user.id,
        membership_number="LMP-2026-AAAAAA",
        joined_date=datetime.date.today(),
        membership_status=MembershipStatus.ACTIVE,
    )
    db_session.add(member)
    await db_session.flush()

    # 2. Create available book
    book = Book(
        title="Python Design Patterns",
        author="Author X",
        isbn="9780131103328",
        total_copies=2,
        available_copies=2,
    )
    db_session.add(book)
    await db_session.flush()

    # 3. Borrow book
    record = await borrow_service.borrow_book(member.id, book.id)
    assert record.id is not None
    assert record.status == BorrowStatus.BORROWED
    assert record.renewal_count == 0

    # Verify inventory was decremented
    await db_session.refresh(book)
    assert book.available_copies == 1


@pytest.mark.asyncio
async def test_borrow_out_of_stock_fails(
    borrow_service: BorrowService, db_session: AsyncSession
) -> None:
    user = User(
        name="Member B",
        email="member_b@example.com",
        password_hash="Hash123!",
        role=UserRole.MEMBER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.flush()

    member = Member(
        user_id=user.id,
        membership_number="LMP-2026-BBBBBB",
        joined_date=datetime.date.today(),
        membership_status=MembershipStatus.ACTIVE,
    )
    db_session.add(member)
    await db_session.flush()

    # Book with 0 copies
    book = Book(
        title="Out of Stock Book",
        author="Author Y",
        isbn="9780131103329",
        total_copies=0,
        available_copies=0,
    )
    db_session.add(book)
    await db_session.flush()

    with pytest.raises(BookUnavailableException):
        await borrow_service.borrow_book(member.id, book.id)


@pytest.mark.asyncio
async def test_borrow_suspended_member_fails(
    borrow_service: BorrowService, db_session: AsyncSession
) -> None:
    user = User(
        name="Suspended Member",
        email="suspended@example.com",
        password_hash="Hash123!",
        role=UserRole.MEMBER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.flush()

    member = Member(
        user_id=user.id,
        membership_number="LMP-2026-CCCCCC",
        joined_date=datetime.date.today(),
        membership_status=MembershipStatus.SUSPENDED,
    )
    db_session.add(member)
    await db_session.flush()

    book = Book(
        title="Python Guide",
        author="Author Z",
        isbn="9780131103330",
        total_copies=1,
        available_copies=1,
    )
    db_session.add(book)
    await db_session.flush()

    with pytest.raises(MemberSuspendedException):
        await borrow_service.borrow_book(member.id, book.id)


@pytest.mark.asyncio
async def test_borrow_overdue_blocked_fails(
    borrow_service: BorrowService, db_session: AsyncSession
) -> None:
    user = User(
        name="Overdue Member",
        email="overdue@example.com",
        password_hash="Hash123!",
        role=UserRole.MEMBER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.flush()

    member = Member(
        user_id=user.id,
        membership_number="LMP-2026-DDDDDD",
        joined_date=datetime.date.today(),
        membership_status=MembershipStatus.ACTIVE,
    )
    db_session.add(member)
    await db_session.flush()

    book = Book(
        title="Python Intermediate",
        author="Author W",
        isbn="9780131103331",
        total_copies=2,
        available_copies=2,
    )
    db_session.add(book)
    await db_session.flush()

    # Create an active overdue borrow record directly in DB
    overdue_record = BorrowRecord(
        id=uuid.uuid4(),
        member_id=member.id,
        book_id=book.id,
        borrow_date=datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=20),
        due_date=datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=6),  # Overdue
        status=BorrowStatus.BORROWED,
        renewal_count=0,
    )
    db_session.add(overdue_record)
    await db_session.flush()

    # Attempt to borrow another book should fail due to overdue holds
    with pytest.raises(OverdueMemberException):
        await borrow_service.borrow_book(member.id, book.id)


@pytest.mark.asyncio
async def test_borrow_limit_exceeded_fails(
    borrow_service: BorrowService, db_session: AsyncSession
) -> None:
    user = User(
        name="Busy Member",
        email="busy@example.com",
        password_hash="Hash123!",
        role=UserRole.MEMBER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.flush()

    member = Member(
        user_id=user.id,
        membership_number="LMP-2026-EEEEEE",
        joined_date=datetime.date.today(),
        membership_status=MembershipStatus.ACTIVE,
    )
    db_session.add(member)
    await db_session.flush()

    # Insert 5 active borrow records directly
    for i in range(5):
        bk = Book(
            title=f"Book limit {i}",
            author="Author Limit",
            isbn=f"978013110334{i}",
            total_copies=2,
            available_copies=2,
        )
        db_session.add(bk)
        await db_session.flush()

        rec = BorrowRecord(
            id=uuid.uuid4(),
            member_id=member.id,
            book_id=bk.id,
            borrow_date=datetime.datetime.now(datetime.UTC),
            due_date=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=14),
            status=BorrowStatus.BORROWED,
            renewal_count=0,
        )
        db_session.add(rec)
    await db_session.flush()

    # 6th checkout attempt should fail
    extra_book = Book(
        title="Extra Book",
        author="Author Extra",
        isbn="9780131103350",
        total_copies=1,
        available_copies=1,
    )
    db_session.add(extra_book)
    await db_session.flush()

    with pytest.raises(BorrowLimitExceededException):
        await borrow_service.borrow_book(member.id, extra_book.id)


@pytest.mark.asyncio
async def test_return_book_calculates_fine_and_restores_inventory(
    borrow_service: BorrowService, db_session: AsyncSession
) -> None:
    user = User(
        name="Returning Member",
        email="return@example.com",
        password_hash="Hash123!",
        role=UserRole.MEMBER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.flush()

    member = Member(
        user_id=user.id,
        membership_number="LMP-2026-FFFFFF",
        joined_date=datetime.date.today(),
        membership_status=MembershipStatus.ACTIVE,
    )
    db_session.add(member)
    await db_session.flush()

    book = Book(
        title="Clean Architecture",
        author="Robert Martin",
        isbn="9780134494167",
        total_copies=2,
        available_copies=1,  # 1 copy checked out
    )
    db_session.add(book)
    await db_session.flush()

    # Create overdue record
    record = BorrowRecord(
        id=uuid.uuid4(),
        member_id=member.id,
        book_id=book.id,
        borrow_date=datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=20),
        due_date=datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=6),  # 6 days late
        status=BorrowStatus.BORROWED,
        renewal_count=0,
    )
    db_session.add(record)
    await db_session.flush()

    # Return book
    returned = await borrow_service.return_book(record.id)
    assert returned.status == BorrowStatus.RETURNED
    # 6 days * 0.50 rate = 3.00 fine
    assert returned.fine_amount == 3.00

    # Inventory copies must be restored
    await db_session.refresh(book)
    assert book.available_copies == 2


@pytest.mark.asyncio
async def test_return_book_is_idempotent(
    borrow_service: BorrowService, db_session: AsyncSession
) -> None:
    user = User(
        name="Idempotent Member",
        email="idem@example.com",
        password_hash="Hash123!",
        role=UserRole.MEMBER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.flush()

    member = Member(
        user_id=user.id,
        membership_number="LMP-2026-GGGGGG",
        joined_date=datetime.date.today(),
        membership_status=MembershipStatus.ACTIVE,
    )
    db_session.add(member)
    await db_session.flush()

    book = Book(
        title="Extreme Programming",
        author="Kent Beck",
        isbn="9780201616415",
        total_copies=2,
        available_copies=1,
    )
    db_session.add(book)
    await db_session.flush()

    record = BorrowRecord(
        id=uuid.uuid4(),
        member_id=member.id,
        book_id=book.id,
        borrow_date=datetime.datetime.now(datetime.UTC),
        due_date=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=14),
        status=BorrowStatus.BORROWED,
        renewal_count=0,
    )
    db_session.add(record)
    await db_session.flush()

    # First return
    r1 = await borrow_service.return_book(record.id)
    assert r1.status == BorrowStatus.RETURNED
    await db_session.refresh(book)
    assert book.available_copies == 2

    # Second return (replayed)
    r2 = await borrow_service.return_book(record.id)
    assert r2.status == BorrowStatus.RETURNED
    # Available copies should not inflate (remain 2)
    await db_session.refresh(book)
    assert book.available_copies == 2


@pytest.mark.asyncio
async def test_renew_book_succeeds_and_renewal_limits(
    borrow_service: BorrowService, db_session: AsyncSession
) -> None:
    user = User(
        name="Renewal Member",
        email="renew@example.com",
        password_hash="Hash123!",
        role=UserRole.MEMBER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.flush()

    member = Member(
        user_id=user.id,
        membership_number="LMP-2026-HHHHHH",
        joined_date=datetime.date.today(),
        membership_status=MembershipStatus.ACTIVE,
    )
    db_session.add(member)
    await db_session.flush()

    book = Book(
        title="Test Driven Development",
        author="Kent Beck",
        isbn="9780321146533",
        total_copies=1,
        available_copies=0,
    )
    db_session.add(book)
    await db_session.flush()

    record = BorrowRecord(
        id=uuid.uuid4(),
        member_id=member.id,
        book_id=book.id,
        borrow_date=datetime.datetime.now(datetime.UTC),
        due_date=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=14),
        status=BorrowStatus.BORROWED,
        renewal_count=0,
    )
    db_session.add(record)
    await db_session.flush()

    # 1. First renewal
    r1 = await borrow_service.renew_book(record.id)
    assert r1.status == BorrowStatus.RENEWED
    assert r1.renewal_count == 1

    # 2. Second renewal
    r2 = await borrow_service.renew_book(record.id)
    assert r2.renewal_count == 2

    # 3. Third renewal attempt should fail
    with pytest.raises(RenewalLimitExceededException):
        await borrow_service.renew_book(record.id)


@pytest.mark.asyncio
async def test_renew_already_returned_book_fails(
    borrow_service: BorrowService, db_session: AsyncSession
) -> None:
    user = User(
        name="Member I",
        email="member_i@example.com",
        password_hash="Hash123!",
        role=UserRole.MEMBER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.flush()

    member = Member(
        user_id=user.id,
        membership_number="LMP-2026-IIIIII",
        joined_date=datetime.date.today(),
        membership_status=MembershipStatus.ACTIVE,
    )
    db_session.add(member)
    await db_session.flush()

    book = Book(
        title="Refactoring Ruby",
        author="Jay Fields",
        isbn="9780321984135",
        total_copies=1,
        available_copies=1,
    )
    db_session.add(book)
    await db_session.flush()

    record = BorrowRecord(
        id=uuid.uuid4(),
        member_id=member.id,
        book_id=book.id,
        borrow_date=datetime.datetime.now(datetime.UTC),
        due_date=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=14),
        status=BorrowStatus.RETURNED,  # Already returned
        renewal_count=0,
    )
    db_session.add(record)
    await db_session.flush()

    with pytest.raises(BookAlreadyReturnedException):
        await borrow_service.renew_book(record.id)
