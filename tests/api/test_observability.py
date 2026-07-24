import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.mark.asyncio
async def test_api_health_liveness(client: AsyncClient) -> None:
    res = await client.get("/health/live")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "alive"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_api_health_readiness(client: AsyncClient, db_session: AsyncSession) -> None:
    res = await client.get("/health/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"


@pytest.mark.asyncio
async def test_api_metrics_endpoint(client: AsyncClient) -> None:
    res = await client.get("/metrics")
    assert res.status_code == 200
    assert "http_requests_total" in res.text


@pytest.mark.asyncio
async def test_request_correlation_id_middleware(client: AsyncClient) -> None:
    # 1. Without x-request-id header (middleware should generate one)
    res = await client.get("/health/live")
    assert res.status_code == 200
    assert "x-request-id" in res.headers
    generated_id = res.headers["x-request-id"]
    assert len(generated_id) > 0

    # 2. With x-request-id header (middleware should propagate it)
    custom_id = "test-correlation-id-1234"
    res2 = await client.get("/health/live", headers={"x-request-id": custom_id})
    assert res2.status_code == 200
    assert res2.headers["x-request-id"] == custom_id


@pytest.mark.asyncio
async def test_exception_envelope_translation(client: AsyncClient) -> None:
    # Trigger a 404 Route NotFound to test StarletteHTTPException handling
    res = await client.get("/invalid-route-that-does-not-exist-123")
    assert res.status_code == 404
    data = res.json()
    assert data["success"] is False
    assert data["error_code"] == "HTTP_ERROR"
    assert "Not Found" in data["message"]
