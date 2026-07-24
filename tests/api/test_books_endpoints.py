import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import jwt_manager
from app.domain.enums import UserRole, UserStatus
from app.main import app
from app.models.user import User


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
async def librarian_token(db_session: AsyncSession) -> str:
    user = User(
        name="Librarian Test",
        email="librarian_test@example.com",
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
        name="Member Test",
        email="member_test@example.com",
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
async def test_api_create_book_librarian_succeeds(
    client: AsyncClient, librarian_token: str
) -> None:
    headers = {"Authorization": f"Bearer {librarian_token}"}
    payload = {
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "isbn": "9780132350884",
        "total_copies": 5,
        "genre": "Computer Science",
    }
    response = await client.post("/api/v1/books", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["title"] == "Clean Code"
    assert data["data"]["available_copies"] == 5


@pytest.mark.asyncio
async def test_api_create_book_member_forbidden(client: AsyncClient, member_token: str) -> None:
    headers = {"Authorization": f"Bearer {member_token}"}
    payload = {
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "isbn": "9780132350884",
        "total_copies": 5,
    }
    response = await client.post("/api/v1/books", json=payload, headers=headers)
    assert response.status_code == 403  # Forbidden for normal members


@pytest.mark.asyncio
async def test_api_search_books_paginated(
    client: AsyncClient, librarian_token: str, db_session: AsyncSession
) -> None:
    # Register 1 book
    headers = {"Authorization": f"Bearer {librarian_token}"}
    payload = {
        "title": "Clean Architecture",
        "author": "Robert C. Martin",
        "isbn": "9780134494166",
        "total_copies": 3,
    }
    await client.post("/api/v1/books", json=payload, headers=headers)

    # Search (everyone is allowed)
    response = await client.get("/api/v1/books?query=Architecture&page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]["items"]) == 1
    assert data["data"]["items"][0]["title"] == "Clean Architecture"


@pytest.mark.asyncio
async def test_api_get_book_details(
    client: AsyncClient, librarian_token: str, db_session: AsyncSession
) -> None:
    headers = {"Authorization": f"Bearer {librarian_token}"}
    payload = {
        "title": "Refactoring",
        "author": "Martin Fowler",
        "isbn": "9780201485677",
        "total_copies": 2,
    }
    res = await client.post("/api/v1/books", json=payload, headers=headers)
    book_id = res.json()["data"]["id"]

    # Get book by ID
    response = await client.get(f"/api/v1/books/{book_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["title"] == "Refactoring"


@pytest.mark.asyncio
async def test_api_update_book(client: AsyncClient, librarian_token: str) -> None:
    headers = {"Authorization": f"Bearer {librarian_token}"}
    payload = {
        "title": "Refactoring",
        "author": "Martin Fowler",
        "isbn": "9780201485677",
        "total_copies": 2,
    }
    res = await client.post("/api/v1/books", json=payload, headers=headers)
    book_id = res.json()["data"]["id"]

    # Update copies
    patch_payload = {"total_copies": 10}
    patch_response = await client.patch(
        f"/api/v1/books/{book_id}", json=patch_payload, headers=headers
    )
    assert patch_response.status_code == 200
    data = patch_response.json()
    assert data["data"]["total_copies"] == 10
    assert data["data"]["available_copies"] == 10


@pytest.mark.asyncio
async def test_api_delete_book(client: AsyncClient, librarian_token: str) -> None:
    headers = {"Authorization": f"Bearer {librarian_token}"}
    payload = {
        "title": "Temporary Book",
        "author": "Author Temp",
        "isbn": "9780131103399",
        "total_copies": 1,
    }
    res = await client.post("/api/v1/books", json=payload, headers=headers)
    book_id = res.json()["data"]["id"]

    # Delete book
    del_res = await client.delete(f"/api/v1/books/{book_id}", headers=headers)
    assert del_res.status_code == 200

    # Get details should fail (404)
    get_res = await client.get(f"/api/v1/books/{book_id}")
    assert get_res.status_code == 404
