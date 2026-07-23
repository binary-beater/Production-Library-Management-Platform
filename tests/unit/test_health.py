from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "uptime" in data
    assert data["database"] == "connected"
    assert data["version"] == "1.0.0"
    assert "timestamp" in data
