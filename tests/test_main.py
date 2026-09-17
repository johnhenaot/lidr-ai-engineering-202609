import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.main import app


class TestHealthEndpoint:
    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_returns_200_with_ok_status(self, client):
        """Return HTTP 200 with ok status from health probe."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestStartup:
    @pytest.fixture(autouse=True)
    def isolated_settings(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        for field in Settings.model_fields:
            monkeypatch.delenv(field.upper(), raising=False)
            monkeypatch.delenv(field.lower(), raising=False)
        get_settings.cache_clear()
        yield
        get_settings.cache_clear()

    def test_refuses_to_start_without_active_provider_key(self):
        """Raise ValidationError during startup when provider key is missing."""
        with pytest.raises(ValidationError, match="OPENAI_API_KEY is required"):
            with TestClient(app):
                pass

    def test_starts_when_active_provider_key_is_set(self, monkeypatch):
        """Complete startup when the active provider key is present."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        with TestClient(app):
            pass
