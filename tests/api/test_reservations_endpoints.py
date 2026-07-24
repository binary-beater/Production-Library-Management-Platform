import datetime
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import jwt_manager
from app.domain.enums import MembershipStatus, ReservationStatus, UserRole, UserStatus
from app.main import app
from app.models.book import Book
from app.models.member import Member
from app.models.reservation import Reservation
from app.models.user import User


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
async def member_context(db_session: AsyncSession) -> tuple[User, Member, str]:
    user = User(
        name="Member Res",
        email="member_res@example.com",
        password_hash="Hash123!",
        role=UserRole.MEMBER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.flush()

    member = Member(
        user_id=user.id,
        membership_number="LMP-2026-R11111",
        joined_date=datetime.date.today()
        if hasattr(datetime, "date")
        else datetime.datetime.now().date(),
        membership_status=MembershipStatus.ACTIVE,
    )
    db_session.add(member)
    await db_session.flush()

    token = jwt_manager.create_access_token(
        subject=str(user.id),
        jti=str(uuid.uuid4()),
        additional_claims={"role": UserRole.MEMBER.value},
    )
    return user, member, token


@pytest.fixture
async def librarian_token(db_session: AsyncSession) -> str:
    user = User(
        name="Librarian Res",
        email="lib_res@example.com",
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


@pytest.mark.asyncio
async def test_api_place_reservation(
    client: AsyncClient, member_context: tuple[User, Member, str], db_session: AsyncSession
) -> None:
    _, _, token = member_context
    headers = {"Authorization": f"Bearer {token}"}

    # Book with 0 copies
    book = Book(
        title="Testing Book X",
        author="Author",
        isbn="9780131103326",
        total_copies=0,
        available_copies=0,
    )
    db_session.add(book)
    await db_session.flush()

    # Place reservation
    payload = {"book_id": str(book.id)}
    res = await client.post("/api/v1/reservations", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["success"] is True
    assert data["data"]["status"] == "PENDING"
    assert data["data"]["queue_position"] == 1


@pytest.mark.asyncio
async def test_api_cancel_reservation(
    client: AsyncClient, member_context: tuple[User, Member, str], db_session: AsyncSession
) -> None:
    _, member, token = member_context
    headers = {"Authorization": f"Bearer {token}"}

    book = Book(
        title="Testing Book Y",
        author="Author",
        isbn="9780131103327",
        total_copies=0,
        available_copies=0,
    )
    db_session.add(book)
    await db_session.flush()

    # Create reservation directly
    reservation = Reservation(
        id=uuid.uuid4(),
        member_id=member.id,
        book_id=book.id,
        status=ReservationStatus.PENDING,
    )
    db_session.add(reservation)
    await db_session.flush()

    # Cancel reservation
    res = await client.post(f"/api/v1/reservations/{reservation.id}/cancel", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_api_list_active_reservations(
    client: AsyncClient, member_context: tuple[User, Member, str], db_session: AsyncSession
) -> None:
    _, member, token = member_context
    headers = {"Authorization": f"Bearer {token}"}

    book = Book(
        title="Testing Book Z",
        author="Author",
        isbn="9780131103328",
        total_copies=0,
        available_copies=0,
    )
    db_session.add(book)
    await db_session.flush()

    reservation = Reservation(
        id=uuid.uuid4(),
        member_id=member.id,
        book_id=book.id,
        status=ReservationStatus.PENDING,
    )
    db_session.add(reservation)
    await db_session.flush()

    # List active
    res = await client.get("/api/v1/reservations/active", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["data"]) == 1
    assert data["data"][0]["queue_position"] == 1


@pytest.mark.asyncio
async def test_api_sweep_requires_librarian(
    client: AsyncClient, librarian_token: str, member_context: tuple[User, Member, str]
) -> None:
    # 1. Member calling sweep should be forbidden (403)
    _, _, m_token = member_context
    m_headers = {"Authorization": f"Bearer {m_token}"}
    res_m = await client.post("/api/v1/reservations/sweep", headers=m_headers)
    assert res_m.status_code == 403

    # 2. Librarian calling sweep should succeed (200)
    lib_headers = {"Authorization": f"Bearer {librarian_token}"}
    res_lib = await client.post("/api/v1/reservations/sweep", headers=lib_headers)
    assert res_lib.status_code == 200
    data = res_lib.json()
    assert data["success"] is True
    assert "expired_count" in data["data"]
