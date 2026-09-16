import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from app.routers import estimations

TRANSCRIPT = "Client wants an e-commerce store with Stripe."
ESTIMATE = "## Estimate: E-Commerce Store"


def make_settings(**overrides) -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        openai_api_key="sk-openai",
        anthropic_api_key="sk-anthropic",
        **overrides,
    )


@pytest.fixture
def test_settings():
    return make_settings(llm_provider="openai", llm_model="gpt-4o-mini")


@pytest.fixture
def client(test_settings):
    app.dependency_overrides[get_settings] = lambda: test_settings
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def mock_generate(mocker):
    return mocker.patch.object(
        estimations, "generate_estimation", return_value=ESTIMATE
    )


class TestEstimateEndpoint:
    def test_returns_200_with_estimation_body(self, client, mock_generate):
        """Return HTTP 200 with generated estimation text in response body."""
        response = client.post("/api/v1/estimate", json={"transcription": TRANSCRIPT})

        assert response.status_code == 200
        assert response.json()["estimation"] == ESTIMATE
        assert set(response.json().keys()) == {"estimation", "model", "provider"}

    def test_echoes_configured_model_and_provider(self, client, mock_generate):
        """Echo active model and provider configured in settings."""
        anthropic_settings = make_settings(
            llm_provider="anthropic", llm_model="claude-haiku-4-5"
        )
        app.dependency_overrides[get_settings] = lambda: anthropic_settings

        response = client.post("/api/v1/estimate", json={"transcription": TRANSCRIPT})

        data = response.json()
        assert data["provider"] == "anthropic"
        assert data["model"] == "claude-haiku-4-5"

    def test_delegates_to_service_with_transcription_and_settings(
        self, client, mock_generate, test_settings
    ):
        """Pass transcription and settings to the LLM service."""
        client.post("/api/v1/estimate", json={"transcription": TRANSCRIPT})

        mock_generate.assert_awaited_once_with(TRANSCRIPT, test_settings)

    def test_strips_surrounding_whitespace(self, client, mock_generate, test_settings):
        """Strip surrounding whitespace from transcription before service delegation."""
        client.post("/api/v1/estimate", json={"transcription": f"  {TRANSCRIPT}  \n"})

        mock_generate.assert_awaited_once_with(TRANSCRIPT, test_settings)

    def test_rejects_missing_transcription(self, client, mock_generate):
        """Reject request with HTTP 422 when transcription field is omitted."""
        response = client.post("/api/v1/estimate", json={})

        assert response.status_code == 422
        mock_generate.assert_not_called()

    @pytest.mark.parametrize("blank_value", ["", "   ", "\t\n  "])
    def test_rejects_blank_transcription(self, client, mock_generate, blank_value):
        """Reject request with HTTP 422 when transcription is whitespace-only."""
        response = client.post("/api/v1/estimate", json={"transcription": blank_value})

        assert response.status_code == 422
        mock_generate.assert_not_called()
