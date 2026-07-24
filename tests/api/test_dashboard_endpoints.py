import datetime
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import jwt_manager
from app.domain.enums import (
    BorrowStatus,
    MembershipStatus,
    ReservationStatus,
    UserRole,
    UserStatus,
)
from app.main import app
from app.models.book import Book
from app.models.borrow_record import BorrowRecord
from app.models.member import Member
from app.models.reservation import Reservation
from app.models.user import User


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
async def librarian_token(db_session: AsyncSession) -> str:
    user = User(
        name="Lib Dash",
        email="lib_dash@example.com",
        password_hash="Hash123!",
        role=UserRole.LIBRARIAN,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.flush()

    token = jwt_manager.create_access_token(
        subject=str(user.id),
        jti=str(uuid.uuid4()),
        additional_claims={"role": UserRole.LIBRARIAN.value},
    )
    return token


@pytest.fixture
async def member_token(db_session: AsyncSession) -> str:
    user = User(
        name="Mem Dash",
        email="mem_dash@example.com",
        password_hash="Hash123!",
        role=UserRole.MEMBER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.flush()

    token = jwt_manager.create_access_token(
        subject=str(user.id),
        jti=str(uuid.uuid4()),
        additional_claims={"role": UserRole.MEMBER.value},
    )
    return token


@pytest.mark.asyncio
async def test_api_dashboard_rbac(
    client: AsyncClient, librarian_token: str, member_token: str
) -> None:
    # 1. Member access should be forbidden (403)
    res = await client.get(
        "/api/v1/dashboard/summary", headers={"Authorization": f"Bearer {member_token}"}
    )
    assert res.status_code == 403

    # 2. Librarian access should succeed (200)
    res = await client.get(
        "/api/v1/dashboard/summary", headers={"Authorization": f"Bearer {librarian_token}"}
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_api_dashboard_input_validation(client: AsyncClient, librarian_token: str) -> None:
    headers = {"Authorization": f"Bearer {librarian_token}"}

    # Under minimum limit (days = 0)
    res = await client.get("/api/v1/dashboard/summary?days=0", headers=headers)
    assert res.status_code == 422

    # Over maximum limit (days = 366)
    res = await client.get("/api/v1/dashboard/summary?days=366", headers=headers)
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_api_dashboard_empty_database(client: AsyncClient, librarian_token: str) -> None:
    # E2E check when no data exists (all metrics return zero)
    res = await client.get(
        "/api/v1/dashboard/summary", headers={"Authorization": f"Bearer {librarian_token}"}
    )
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["inventory"]["total_titles"] == 0
    assert data["inventory"]["total_copies"] == 0
    assert data["inventory"]["checked_out_copies"] == 0
    assert data["inventory"]["available_copies"] == 0

    assert data["members"]["active_count"] == 0
    assert data["members"]["suspended_count"] == 0

    assert data["reservations"]["pending"] == 0
    assert data["reservations"]["hold"] == 0
    assert data["reservations"]["expired_today"] == 0

    assert data["overdue"]["count"] == 0
    assert data["overdue"]["ratio"] == 0.0
    assert data["overdue"]["average_days_overdue"] == 0.0

    assert len(data["popular_books"]) == 0


@pytest.mark.asyncio
async def test_api_dashboard_complex_data_aggregations(
    client: AsyncClient, librarian_token: str, db_session: AsyncSession
) -> None:
    # 1. Seed two books:
    # Book A: active (1 copy checkout, 1 copy shelf)
    # Book B: soft-deleted (should be completely excluded)
    b1 = Book(
        id=uuid.uuid4(),
        title="Book Active",
        author="Author X",
        isbn="9780131103329",
        total_copies=2,
        available_copies=1,
        is_deleted=False,
    )
    b2 = Book(
        id=uuid.uuid4(),
        title="Book Deleted",
        author="Author Y",
        isbn="9780131103330",
        total_copies=5,
        available_copies=5,
        is_deleted=True,
    )
    db_session.add_all([b1, b2])
    await db_session.flush()

    # 2. Seed active members (1 active, 1 suspended)
    u1 = User(
        name="U1",
        email="u1@ex.com",
        password_hash="H",
        role=UserRole.MEMBER,
        status=UserStatus.ACTIVE,
    )
    u2 = User(
        name="U2",
        email="u2@ex.com",
        password_hash="H",
        role=UserRole.MEMBER,
        status=UserStatus.ACTIVE,
    )
    db_session.add_all([u1, u2])
    await db_session.flush()

    m1 = Member(
        user_id=u1.id,
        membership_number="LMP-D-111",
        joined_date=datetime.date.today(),
        membership_status=MembershipStatus.ACTIVE,
    )
    m2 = Member(
        user_id=u2.id,
        membership_number="LMP-D-222",
        joined_date=datetime.date.today(),
        membership_status=MembershipStatus.SUSPENDED,
    )
    db_session.add_all([m1, m2])
    await db_session.flush()

    # 3. Seed active overdue checkout record (overdue by 3 days)
    now = datetime.datetime.now(datetime.UTC)
    borrow = BorrowRecord(
        id=uuid.uuid4(),
        member_id=m1.id,
        book_id=b1.id,
        borrow_date=now - datetime.timedelta(days=10),
        due_date=now - datetime.timedelta(days=3),  # 3 days overdue
        status=BorrowStatus.BORROWED,
        renewal_count=0,
    )
    db_session.add(borrow)

    # 4. Seed reservations (1 PENDING, 1 HOLD, 1 CANCELLED, 1 COMPLETED)
    # The cancelled and completed ones must be ignored in active queue stats
    r_pending = Reservation(
        id=uuid.uuid4(), member_id=m1.id, book_id=b1.id, status=ReservationStatus.PENDING
    )
    r_hold = Reservation(
        id=uuid.uuid4(), member_id=m2.id, book_id=b1.id, status=ReservationStatus.HOLD
    )
    r_cancel = Reservation(
        id=uuid.uuid4(), member_id=m1.id, book_id=b1.id, status=ReservationStatus.CANCELLED
    )
    r_complete = Reservation(
        id=uuid.uuid4(), member_id=m2.id, book_id=b1.id, status=ReservationStatus.COMPLETED
    )
    db_session.add_all([r_pending, r_hold, r_cancel, r_complete])
    await db_session.flush()

    # 5. Call API
    res = await client.get(
        "/api/v1/dashboard/summary?days=30", headers={"Authorization": f"Bearer {librarian_token}"}
    )
    assert res.status_code == 200
    data = res.json()["data"]

    # Verify inventory details (soft-deleted book B2 is excluded)
    assert data["inventory"]["total_titles"] == 1
    assert data["inventory"]["total_copies"] == 2
    assert data["inventory"]["checked_out_copies"] == 1
    assert data["inventory"]["available_copies"] == 1

    # Verify members
    assert data["members"]["active_count"] == 1
    assert data["members"]["suspended_count"] == 1

    # Verify active reservations (only PENDING and HOLD counted)
    assert data["reservations"]["pending"] == 1
    assert data["reservations"]["hold"] == 1

    # Verify overdue loans (due date < now, status borrowed counts as overdue)
    assert data["overdue"]["count"] == 1
    assert data["overdue"]["ratio"] == 1.0  # 1 overdue loan / 1 active loan
    assert data["overdue"]["average_days_overdue"] == 3.0

    # Verify popular books output
    assert len(data["popular_books"]) == 1
    assert data["popular_books"][0]["title"] == "Book Active"
    assert data["popular_books"][0]["checkout_count"] == 1


@pytest.mark.asyncio
async def test_api_dashboard_popular_books_tie_breaking(
    client: AsyncClient, librarian_token: str, db_session: AsyncSession
) -> None:
    # Seed 3 active books with 1 checkout each. Tie-breaking should be alphabetical by title:
    # "Clean Code", "Design Patterns", "Refactoring"
    books = [
        Book(
            id=uuid.uuid4(),
            title="Refactoring",
            author="Fowler",
            isbn="9780131103331",
            total_copies=1,
            available_copies=0,
        ),
        Book(
            id=uuid.uuid4(),
            title="Clean Code",
            author="Martin",
            isbn="9780131103332",
            total_copies=1,
            available_copies=0,
        ),
        Book(
            id=uuid.uuid4(),
            title="Design Patterns",
            author="Gang of Four",
            isbn="9780131103333",
            total_copies=1,
            available_copies=0,
        ),
    ]
    db_session.add_all(books)
    await db_session.flush()

    # Member user
    u = User(
        name="User",
        email="usr@ex.com",
        password_hash="H",
        role=UserRole.MEMBER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(u)
    await db_session.flush()

    m = Member(
        user_id=u.id,
        membership_number="LMP-TIE-1",
        joined_date=datetime.date.today(),
        membership_status=MembershipStatus.ACTIVE,
    )
    db_session.add(m)
    await db_session.flush()

    # Add borrow records
    now = datetime.datetime.now(datetime.UTC)
    for b in books:
        rec = BorrowRecord(
            id=uuid.uuid4(),
            member_id=m.id,
            book_id=b.id,
            borrow_date=now - datetime.timedelta(hours=1),
            due_date=now + datetime.timedelta(days=14),
            status=BorrowStatus.BORROWED,
        )
        db_session.add(rec)
    await db_session.flush()

    # Call API
    res = await client.get(
        "/api/v1/dashboard/summary?days=30", headers={"Authorization": f"Bearer {librarian_token}"}
    )
    assert res.status_code == 200
    data = res.json()["data"]

    # Popular books list must be sorted alphabetically by title: "Clean Code", "Design Patterns", "Refactoring"
    popular = [b["title"] for b in data["popular_books"]]
    assert popular == ["Clean Code", "Design Patterns", "Refactoring"]
