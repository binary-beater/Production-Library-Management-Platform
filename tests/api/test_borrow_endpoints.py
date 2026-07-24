import datetime
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import jwt_manager
from app.domain.enums import MembershipStatus, UserRole, UserStatus
from app.main import app
from app.models.book import Book
from app.models.member import Member
from app.models.user import User


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
async def member_context(db_session: AsyncSession) -> tuple[User, Member, str]:
    user = User(
        name="Member Borrows",
        email="member_borrows@example.com",
        password_hash="Hash123!",
        role=UserRole.MEMBER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.flush()

    member = Member(
        user_id=user.id,
        membership_number="LMP-2026-X11111",
        joined_date=datetime.date.today(),
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


@pytest.mark.asyncio
async def test_api_borrow_and_return_book(
    client: AsyncClient, member_context: tuple[User, Member, str], db_session: AsyncSession
) -> None:
    _, _, token = member_context
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a book
    book = Book(
        title="Software Testing",
        author="Author Test",
        isbn="9780131103366",
        total_copies=2,
        available_copies=2,
    )
    db_session.add(book)
    await db_session.flush()

    # 2. Borrow Book
    borrow_payload = {"book_id": str(book.id)}
    borrow_res = await client.post("/api/v1/borrow", json=borrow_payload, headers=headers)
    assert borrow_res.status_code == 201
    borrow_data = borrow_res.json()
    assert borrow_data["success"] is True
    borrow_id = borrow_data["data"]["borrow_record_id"]

    # 3. Return Book
    return_res = await client.post(f"/api/v1/borrow/{borrow_id}/return", headers=headers)
    assert return_res.status_code == 200
    return_data = return_res.json()
    assert return_data["success"] is True
    assert return_data["data"]["status"] == "RETURNED"


@pytest.mark.asyncio
async def test_api_renew_book(
    client: AsyncClient, member_context: tuple[User, Member, str], db_session: AsyncSession
) -> None:
    _, _, token = member_context
    headers = {"Authorization": f"Bearer {token}"}

    book = Book(
        title="Refactoring Patterns",
        author="Joshua Kerievsky",
        isbn="9780321213358",
        total_copies=1,
        available_copies=1,
    )
    db_session.add(book)
    await db_session.flush()

    # Borrow Book
    borrow_payload = {"book_id": str(book.id)}
    borrow_res = await client.post("/api/v1/borrow", json=borrow_payload, headers=headers)
    borrow_id = borrow_res.json()["data"]["borrow_record_id"]

    # Renew Book
    renew_res = await client.post(f"/api/v1/borrow/{borrow_id}/renew", headers=headers)
    assert renew_res.status_code == 200
    renew_data = renew_res.json()
    assert renew_data["success"] is True
    assert renew_data["data"]["renewal_count"] == 1


@pytest.mark.asyncio
async def test_api_borrow_history(
    client: AsyncClient, member_context: tuple[User, Member, str], db_session: AsyncSession
) -> None:
    _, _, token = member_context
    headers = {"Authorization": f"Bearer {token}"}

    book = Book(
        title="Design Patterns",
        author="Gang of Four",
        isbn="9780201633610",
        total_copies=2,
        available_copies=2,
    )
    db_session.add(book)
    await db_session.flush()

    # Borrow Book
    borrow_payload = {"book_id": str(book.id)}
    await client.post("/api/v1/borrow", json=borrow_payload, headers=headers)

    # Get history
    history_res = await client.get("/api/v1/borrow/history?page=1&page_size=10", headers=headers)
    assert history_res.status_code == 200
    history_data = history_res.json()
    assert history_data["success"] is True
    assert len(history_data["data"]) == 1
    assert history_data["data"][0]["book_title"] == "Design Patterns"
