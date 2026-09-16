import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_returns_200_with_ok_status(self, client):
        """Return HTTP 200 with ok status from health probe."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
