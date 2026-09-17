import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.domain.estimate import (
    Duration,
    EstimateDraft,
    EstimationError,
    Risk,
    TaskDraft,
    TeamMember,
)
from app.main import app
from app.routers import estimations

TRANSCRIPT = "Client wants an e-commerce store with Stripe."
DRAFT = EstimateDraft(
    meeting_summary="Summary",
    estimate_title="E-Commerce Store",
    assumptions=["Assumption"],
    out_of_scope=["Scope"],
    tasks=[TaskDraft(name="Core", optimistic=10, likely=20, pessimistic=30)],
    team=[TeamMember(role="engineers", quantity=2, details="")],
    duration=Duration(floor=2, ceiling=4, unit="weeks"),
    risks=[Risk(label="R", impact="low", detail="D")],
    confidence="High",
    confidence_rationale="C",
    validity_days=30,
)
RENDERED_ESTIMATE = "## Estimate: E-Commerce Store"


def make_settings(**overrides) -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        openai_api_key="sk-openai",
        anthropic_api_key="sk-anthropic",
        **overrides,
    )


class TestEstimateEndpoint:
    @pytest.fixture
    def test_settings(self):
        return make_settings(llm_provider="openai", llm_model="gpt-4o-mini")

    @pytest.fixture
    def client(self, test_settings):
        app.dependency_overrides[get_settings] = lambda: test_settings
        yield TestClient(app)
        app.dependency_overrides.clear()

    @pytest.fixture
    def mock_generate(self, mocker):
        return mocker.patch.object(
            estimations, "generate_estimate_draft", return_value=DRAFT
        )

    @pytest.fixture
    def mock_render(self, mocker):
        return mocker.patch.object(
            estimations, "render_markdown", return_value=RENDERED_ESTIMATE
        )

    def test_returns_200_with_estimation_body(self, client, mock_generate, mock_render):
        """Return HTTP 200 with generated estimation text in response body."""
        response = client.post("/api/v1/estimate", json={"transcription": TRANSCRIPT})

        assert response.status_code == 200
        assert response.json()["estimation"] == RENDERED_ESTIMATE

    def test_echoes_configured_model_and_provider(
        self, client, mock_generate, mock_render
    ):
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
        self, client, mock_generate, mock_render, test_settings
    ):
        """Pass transcription and settings to the LLM service."""
        client.post("/api/v1/estimate", json={"transcription": TRANSCRIPT})

        mock_generate.assert_awaited_once_with(TRANSCRIPT, test_settings)

    def test_strips_surrounding_whitespace(
        self, client, mock_generate, mock_render, test_settings
    ):
        """Strip surrounding whitespace from transcription before service delegation."""
        client.post("/api/v1/estimate", json={"transcription": f"  {TRANSCRIPT}  \n"})

        mock_generate.assert_awaited_once_with(TRANSCRIPT, test_settings)

    @pytest.mark.parametrize("blank_value", ["", "   ", "\t\n  "])
    def test_rejects_blank_transcription(self, client, mock_generate, blank_value):
        """Reject request with HTTP 422 when transcription is whitespace-only."""
        response = client.post("/api/v1/estimate", json={"transcription": blank_value})

        assert response.status_code == 422
        mock_generate.assert_not_called()

    def test_returns_502_when_estimation_error_is_raised(self, client, mocker):
        """Return HTTP 502 Bad Gateway when estimation generation fails."""
        mocker.patch.object(
            estimations,
            "generate_estimate_draft",
            side_effect=EstimationError("Model failed to parse"),
        )

        response = client.post("/api/v1/estimate", json={"transcription": TRANSCRIPT})

        assert response.status_code == 502
        assert response.json() == {"detail": "Model failed to parse"}

    def test_renders_markdown_when_formatter_is_unmocked(self, client, mock_generate):
        """Produce real formatted markdown when render_markdown is unmocked."""
        response = client.post("/api/v1/estimate", json={"transcription": TRANSCRIPT})

        assert response.status_code == 200
        assert response.json()["estimation"].startswith("## Estimate: E-Commerce Store")
