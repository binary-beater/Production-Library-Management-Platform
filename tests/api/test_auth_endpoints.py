from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import UserRole
from app.main import app


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an AsyncClient instance for FastAPI routes testing."""
    # Use ASGITransport to route requests directly to our FastAPI app asynchronously
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.mark.asyncio
async def test_api_register_succeeds(client: AsyncClient, db_session: AsyncSession) -> None:
    payload = {
        "name": "Jane Doe",
        "email": "jane_api@example.com",
        "password": "SecurePassword123!",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Jane Doe"
    assert data["email"] == "jane_api@example.com"
    assert data["role"] == UserRole.MEMBER.value


@pytest.mark.asyncio
async def test_api_register_invalid_password_fails(client: AsyncClient) -> None:
    payload = {
        "name": "Invalid User",
        "email": "invalid_pwd@example.com",
        "password": "short",  # Fails password strength validation
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422  # Unprocessable Entity


@pytest.mark.asyncio
async def test_api_login_returns_tokens(client: AsyncClient, db_session: AsyncSession) -> None:
    # 1. Register User
    payload_reg = {
        "name": "Bob API",
        "email": "bob_api@example.com",
        "password": "SecurePassword123!",
    }
    await client.post("/api/v1/auth/register", json=payload_reg)

    # 2. Login
    payload_login = {
        "email": "bob_api@example.com",
        "password": "SecurePassword123!",
    }
    response = await client.post("/api/v1/auth/login", json=payload_login)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_api_login_invalid_credentials_fails(client: AsyncClient) -> None:
    payload = {
        "email": "nonexistent@example.com",
        "password": "Password123!",
    }
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_api_refresh_token_rotates(client: AsyncClient, db_session: AsyncSession) -> None:
    # 1. Register and Login
    payload_reg = {
        "name": "Charlie API",
        "email": "charlie_api@example.com",
        "password": "SecurePassword123!",
    }
    await client.post("/api/v1/auth/register", json=payload_reg)

    payload_login = {
        "email": "charlie_api@example.com",
        "password": "SecurePassword123!",
    }
    login_resp = await client.post("/api/v1/auth/login", json=payload_login)
    tokens = login_resp.json()

    # 2. Refresh
    payload_refresh = {
        "refresh_token": tokens["refresh_token"],
    }
    response = await client.post("/api/v1/auth/refresh", json=payload_refresh)
    assert response.status_code == 200
    new_tokens = response.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    assert new_tokens["refresh_token"] != tokens["refresh_token"]


@pytest.mark.asyncio
async def test_api_logout_invalidates_token(client: AsyncClient, db_session: AsyncSession) -> None:
    # 1. Register and Login
    payload_reg = {
        "name": "Dave API",
        "email": "dave_api@example.com",
        "password": "SecurePassword123!",
    }
    await client.post("/api/v1/auth/register", json=payload_reg)

    payload_login = {
        "email": "dave_api@example.com",
        "password": "SecurePassword123!",
    }
    login_resp = await client.post("/api/v1/auth/login", json=payload_login)
    tokens = login_resp.json()

    # 2. Logout
    payload_logout = {
        "refresh_token": tokens["refresh_token"],
    }
    logout_resp = await client.post("/api/v1/auth/logout", json=payload_logout)
    assert logout_resp.status_code in (240, 204)

    # 3. Try to refresh again
    refresh_resp = await client.post("/api/v1/auth/refresh", json=payload_logout)
    assert refresh_resp.status_code == 401


@pytest.mark.asyncio
async def test_api_get_me_succeeds(client: AsyncClient, db_session: AsyncSession) -> None:
    # 1. Register and Login
    payload_reg = {
        "name": "Eve API",
        "email": "eve_api@example.com",
        "password": "SecurePassword123!",
    }
    await client.post("/api/v1/auth/register", json=payload_reg)

    payload_login = {
        "email": "eve_api@example.com",
        "password": "SecurePassword123!",
    }
    login_resp = await client.post("/api/v1/auth/login", json=payload_login)
    tokens = login_resp.json()

    # 2. Access /me endpoint
    headers = {
        "Authorization": f"Bearer {tokens['access_token']}",
    }
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "eve_api@example.com"
    assert data["role"] == UserRole.MEMBER.value


@pytest.mark.asyncio
async def test_api_get_me_unauthorized_fails(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
